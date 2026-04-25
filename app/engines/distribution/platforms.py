"""
Per-platform publishers.

Each publisher accepts a credentials dict (typically from Account.credentials)
and a payload of caption/media URLs. They return a uniform result:

    {"published": bool, "platform": str, "platform_post_id": Optional[str],
     "url": Optional[str], "error": Optional[str]}

When credentials are missing or the API fails, we never crash the calling
flow — we return published=False with an explanatory error so the post can
be retried.

External libs used (already installed): tweepy (X), praw (Reddit, optional),
httpx (HTTP). Facebook/Instagram use Meta Graph API directly via httpx.
LinkedIn uses its REST API. YouTube uses the Data v3 upload API. Telegram
uses the Bot API.
"""

from __future__ import annotations

import json
import logging
import mimetypes
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _result(published: bool, platform: str, **kwargs: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "published": published,
        "platform": platform,
        "platform_post_id": None,
        "url": None,
        "error": None,
    }
    base.update(kwargs)
    return base


def _missing(platform: str, fields: List[str]) -> Dict[str, Any]:
    return _result(False, platform,
                   error=f"Missing credentials for {platform}: {', '.join(fields)}")


def _http_post_json(url: str, *, json_body: Dict[str, Any],
                     headers: Optional[Dict[str, str]] = None,
                     timeout: float = 30.0) -> httpx.Response:
    return httpx.post(url, json=json_body, headers=headers or {}, timeout=timeout)


# ---------------------------------------------------------------------------
# Telegram (Bot API) — easiest, uses bot token + chat_id
# ---------------------------------------------------------------------------
def publish_telegram(*, credentials: Dict[str, Any],
                      caption: str,
                      image_url: Optional[str] = None,
                      video_url: Optional[str] = None,
                      **_: Any) -> Dict[str, Any]:
    token = credentials.get("bot_token")
    chat_id = credentials.get("chat_id")
    if not token or not chat_id:
        return _missing("telegram", ["bot_token", "chat_id"])
    api = f"https://api.telegram.org/bot{token}"
    try:
        if video_url:
            r = _http_post_json(f"{api}/sendVideo",
                                 json_body={"chat_id": chat_id, "video": video_url,
                                            "caption": caption[:1024]})
        elif image_url:
            r = _http_post_json(f"{api}/sendPhoto",
                                 json_body={"chat_id": chat_id, "photo": image_url,
                                            "caption": caption[:1024]})
        else:
            r = _http_post_json(f"{api}/sendMessage",
                                 json_body={"chat_id": chat_id, "text": caption[:4096]})
        r.raise_for_status()
        body = r.json()
        msg = body.get("result") or {}
        msg_id = msg.get("message_id")
        username = (msg.get("chat") or {}).get("username")
        url = f"https://t.me/{username}/{msg_id}" if username and msg_id else None
        return _result(True, "telegram", platform_post_id=str(msg_id) if msg_id else None,
                       url=url)
    except Exception as exc:
        logger.warning("Telegram publish failed: %s", exc)
        return _result(False, "telegram", error=str(exc))


# ---------------------------------------------------------------------------
# X / Twitter — uses tweepy (OAuth 1.0a)
# ---------------------------------------------------------------------------
def publish_x(*, credentials: Dict[str, Any], caption: str,
              image_paths: Optional[List[str]] = None, **_: Any) -> Dict[str, Any]:
    required = ["api_key", "api_secret", "access_token", "access_token_secret"]
    missing = [f for f in required if not credentials.get(f)]
    if missing:
        return _missing("x", missing)
    try:
        import tweepy  # type: ignore
        client = tweepy.Client(
            consumer_key=credentials["api_key"],
            consumer_secret=credentials["api_secret"],
            access_token=credentials["access_token"],
            access_token_secret=credentials["access_token_secret"],
        )
        media_ids: List[str] = []
        if image_paths:
            auth = tweepy.OAuth1UserHandler(
                credentials["api_key"], credentials["api_secret"],
                credentials["access_token"], credentials["access_token_secret"],
            )
            api_v1 = tweepy.API(auth)
            for path in image_paths[:4]:
                if os.path.exists(path):
                    media = api_v1.media_upload(filename=path)
                    media_ids.append(str(media.media_id))
        kwargs: Dict[str, Any] = {"text": caption[:280]}
        if media_ids:
            kwargs["media_ids"] = media_ids
        resp = client.create_tweet(**kwargs)
        tid = (resp.data or {}).get("id")
        return _result(True, "x", platform_post_id=str(tid) if tid else None,
                       url=f"https://x.com/i/status/{tid}" if tid else None)
    except Exception as exc:
        logger.warning("X publish failed: %s", exc)
        return _result(False, "x", error=str(exc))


# ---------------------------------------------------------------------------
# Facebook (Page Graph API)
# ---------------------------------------------------------------------------
def publish_facebook(*, credentials: Dict[str, Any], caption: str,
                      image_url: Optional[str] = None,
                      video_url: Optional[str] = None,
                      link_url: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    page_id = credentials.get("page_id")
    token = credentials.get("page_access_token")
    if not page_id or not token:
        return _missing("facebook", ["page_id", "page_access_token"])
    base = f"https://graph.facebook.com/v19.0/{page_id}"
    try:
        if image_url:
            url = f"{base}/photos"
            params = {"url": image_url, "caption": caption, "access_token": token}
        elif video_url:
            url = f"{base}/videos"
            params = {"file_url": video_url, "description": caption, "access_token": token}
        else:
            url = f"{base}/feed"
            params = {"message": caption, "access_token": token}
            if link_url:
                params["link"] = link_url
        r = httpx.post(url, params=params, timeout=60.0)
        r.raise_for_status()
        data = r.json()
        post_id = data.get("post_id") or data.get("id")
        return _result(True, "facebook", platform_post_id=post_id,
                       url=f"https://facebook.com/{post_id}" if post_id else None)
    except Exception as exc:
        logger.warning("Facebook publish failed: %s", exc)
        return _result(False, "facebook", error=str(exc))


# ---------------------------------------------------------------------------
# Instagram (Graph API for Business accounts: 2-step container + publish)
# ---------------------------------------------------------------------------
def publish_instagram(*, credentials: Dict[str, Any], caption: str,
                       image_url: Optional[str] = None,
                       video_url: Optional[str] = None,
                       is_reel: bool = False, **_: Any) -> Dict[str, Any]:
    ig_user_id = credentials.get("ig_user_id")
    token = credentials.get("page_access_token")
    if not ig_user_id or not token:
        return _missing("instagram", ["ig_user_id", "page_access_token"])
    if not image_url and not video_url:
        return _result(False, "instagram", error="image_url or video_url required")

    base = f"https://graph.facebook.com/v19.0/{ig_user_id}"
    try:
        media_params: Dict[str, Any] = {"caption": caption[:2200], "access_token": token}
        if video_url:
            media_params["video_url"] = video_url
            media_params["media_type"] = "REELS" if is_reel else "VIDEO"
        else:
            media_params["image_url"] = image_url
        r = httpx.post(f"{base}/media", params=media_params, timeout=60.0)
        r.raise_for_status()
        creation_id = r.json().get("id")
        if not creation_id:
            return _result(False, "instagram", error="No creation id from container call")

        pub = httpx.post(f"{base}/media_publish",
                          params={"creation_id": creation_id, "access_token": token},
                          timeout=60.0)
        pub.raise_for_status()
        post_id = pub.json().get("id")
        return _result(True, "instagram", platform_post_id=post_id,
                       url=f"https://www.instagram.com/p/{post_id}/" if post_id else None)
    except Exception as exc:
        logger.warning("Instagram publish failed: %s", exc)
        return _result(False, "instagram", error=str(exc))


# ---------------------------------------------------------------------------
# LinkedIn (UGC posts — text + media)
# ---------------------------------------------------------------------------
def publish_linkedin(*, credentials: Dict[str, Any], caption: str,
                      image_path: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    token = credentials.get("access_token")
    actor = credentials.get("urn")  # e.g. "urn:li:person:abc123"
    if not token or not actor:
        return _missing("linkedin", ["access_token", "urn"])
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    media_assets: List[Dict[str, Any]] = []
    try:
        if image_path and os.path.exists(image_path):
            # 1) register upload
            reg_body = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": actor,
                    "serviceRelationships": [
                        {"relationshipType": "OWNER",
                         "identifier": "urn:li:userGeneratedContent"}
                    ],
                }
            }
            reg = httpx.post("https://api.linkedin.com/v2/assets?action=registerUpload",
                              headers=headers, json=reg_body, timeout=30.0)
            reg.raise_for_status()
            reg_data = reg.json()["value"]
            asset = reg_data["asset"]
            upload_url = reg_data["uploadMechanism"][
                "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
            with open(image_path, "rb") as f:
                up = httpx.post(upload_url,
                                 headers={"Authorization": f"Bearer {token}"},
                                 content=f.read(), timeout=60.0)
                up.raise_for_status()
            media_assets.append({"status": "READY", "media": asset})

        post_body: Dict[str, Any] = {
            "author": actor,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": caption[:3000]},
                    "shareMediaCategory": "IMAGE" if media_assets else "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        if media_assets:
            post_body["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = media_assets

        r = httpx.post("https://api.linkedin.com/v2/ugcPosts",
                        headers=headers, json=post_body, timeout=30.0)
        r.raise_for_status()
        urn = r.headers.get("x-restli-id") or r.json().get("id")
        return _result(True, "linkedin", platform_post_id=urn,
                       url=f"https://www.linkedin.com/feed/update/{urn}" if urn else None)
    except Exception as exc:
        logger.warning("LinkedIn publish failed: %s", exc)
        return _result(False, "linkedin", error=str(exc))


# ---------------------------------------------------------------------------
# YouTube (Data API v3 — resumable upload)
# ---------------------------------------------------------------------------
def publish_youtube(*, credentials: Dict[str, Any], caption: str,
                     video_path: Optional[str] = None,
                     title: Optional[str] = None,
                     tags: Optional[List[str]] = None,
                     privacy: str = "public", **_: Any) -> Dict[str, Any]:
    token = credentials.get("access_token")
    if not token:
        return _missing("youtube", ["access_token (OAuth2)"])
    if not video_path or not os.path.exists(video_path):
        return _result(False, "youtube", error="video_path is required and must exist")

    metadata = {
        "snippet": {
            "title": (title or caption[:90])[:100],
            "description": caption[:5000],
            "tags": (tags or [])[:25],
            "categoryId": "22",  # People & Blogs
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    try:
        # Initiate resumable upload.
        init = httpx.post(
            "https://www.googleapis.com/upload/youtube/v3/videos"
            "?uploadType=resumable&part=snippet,status",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": "video/*",
            },
            content=json.dumps(metadata).encode("utf-8"),
            timeout=30.0,
        )
        init.raise_for_status()
        upload_url = init.headers.get("Location")
        if not upload_url:
            return _result(False, "youtube", error="No resumable upload URL returned")

        with open(video_path, "rb") as f:
            data = f.read()
        up = httpx.put(upload_url,
                        headers={"Content-Type": mimetypes.guess_type(video_path)[0]
                                 or "video/mp4"},
                        content=data, timeout=600.0)
        up.raise_for_status()
        vid = up.json().get("id")
        return _result(True, "youtube", platform_post_id=vid,
                       url=f"https://www.youtube.com/watch?v={vid}" if vid else None)
    except Exception as exc:
        logger.warning("YouTube publish failed: %s", exc)
        return _result(False, "youtube", error=str(exc))


# ---------------------------------------------------------------------------
# Reddit (PRAW)
# ---------------------------------------------------------------------------
def publish_reddit(*, credentials: Dict[str, Any], caption: str,
                    title: Optional[str] = None,
                    subreddit: Optional[str] = None,
                    image_path: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    required = ["client_id", "client_secret", "username", "password", "user_agent"]
    missing = [f for f in required if not credentials.get(f)]
    sub = subreddit or credentials.get("subreddit")
    if missing or not sub:
        return _missing("reddit", missing + (["subreddit"] if not sub else []))
    try:
        import praw  # type: ignore
        reddit = praw.Reddit(
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
            username=credentials["username"],
            password=credentials["password"],
            user_agent=credentials.get("user_agent", "ContentBot/1.0"),
        )
        sr = reddit.subreddit(sub)
        if image_path and os.path.exists(image_path):
            submission = sr.submit_image(title=title or caption[:300], image_path=image_path)
        else:
            submission = sr.submit(title=title or caption[:300], selftext=caption)
        return _result(True, "reddit", platform_post_id=submission.id,
                       url=f"https://reddit.com{submission.permalink}")
    except Exception as exc:
        logger.warning("Reddit publish failed: %s", exc)
        return _result(False, "reddit", error=str(exc))


# Registry — used by PublisherEngine.
PUBLISHERS = {
    "telegram": publish_telegram,
    "x": publish_x,
    "twitter": publish_x,
    "facebook": publish_facebook,
    "instagram": publish_instagram,
    "linkedin": publish_linkedin,
    "youtube": publish_youtube,
    "youtube_shorts": publish_youtube,
    "reddit": publish_reddit,
}
