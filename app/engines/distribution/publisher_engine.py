"""
PublisherEngine — single entry point that takes a Post + target platforms,
looks up the right Account, applies human-mimicry, runs the platform
publisher, and writes a `Log` row for audit.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.engines.base import BaseEngine
from app.engines.distribution.account_manager import AccountManager
from app.engines.distribution.human_mimicry import HumanMimicryEngine
from app.engines.distribution.platforms import PUBLISHERS
from app.models.models import Account, Log, Post


class PublisherEngine(BaseEngine):
    name = "publisher"
    description = "Multi-platform publisher with logging and rotation"

    def __init__(self) -> None:
        super().__init__()
        self.accounts = AccountManager()
        self.human = HumanMimicryEngine()

    def run(
        self,
        *,
        db: Session,
        user_id: int,
        post_id: int,
        platforms: List[str],
        media: Optional[Dict[str, Any]] = None,
        rotate_account: bool = True,
        per_platform_credentials: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        post = db.query(Post).filter(Post.id == post_id, Post.user_id == user_id).first()
        if not post:
            raise ValueError(f"Post {post_id} not found for user {user_id}")
        media = media or {}

        # Track per-platform IDs on the post.
        platforms_meta: Dict[str, Any] = dict(post.platforms or {})
        platform_post_ids: Dict[str, str] = dict(post.platform_post_ids or {})

        results: List[Dict[str, Any]] = []
        for platform in platforms:
            if platform not in PUBLISHERS:
                results.append({"platform": platform, "published": False,
                                "error": f"Unknown platform '{platform}'"})
                continue

            account_row: Optional[Account] = None
            credentials: Dict[str, Any]
            if per_platform_credentials and platform in per_platform_credentials:
                credentials = per_platform_credentials[platform]
            elif rotate_account:
                rotated = self.accounts(action="rotate", db=db, user_id=user_id, platform=platform)
                if rotated:
                    account_row = db.query(Account).filter(Account.id == rotated["id"]).first()
                    credentials = self.accounts(action="credentials", db=db,
                                                 account_id=rotated["id"]) if account_row else {}
                else:
                    credentials = {}
            else:
                credentials = {}

            # Compose a caption: prefer per-platform stored in post.platforms, else post.caption.
            per_platform = (post.platforms or {}).get(platform, {}) if isinstance(post.platforms, dict) else {}
            caption = per_platform.get("caption") or post.caption or post.script or post.title or ""
            hashtags = (post.extra_metadata or {}).get("hashtags") or []
            shuffled_tags = self.human(action="shuffle_hashtags", hashtags=hashtags)
            if shuffled_tags and "#" not in caption:
                caption = f"{caption}\n\n{' '.join(shuffled_tags[:15])}"

            payload: Dict[str, Any] = {
                "credentials": credentials,
                "caption": caption,
                "title": post.title,
                "image_url": media.get("image_url"),
                "video_url": media.get("video_url"),
                "image_paths": media.get("image_paths") or [],
                "image_path": media.get("image_path"),
                "video_path": media.get("video_path"),
                "link_url": media.get("link_url"),
                "is_reel": media.get("is_reel", False),
                "tags": [t.lstrip("#") for t in hashtags],
                "subreddit": media.get("subreddit"),
                "privacy": media.get("privacy", "public"),
            }

            try:
                outcome = PUBLISHERS[platform](**payload)
            except Exception as exc:  # final safety net
                outcome = {"published": False, "platform": platform,
                           "error": f"Publisher exception: {exc}",
                           "platform_post_id": None, "url": None}

            # Audit log.
            log = Log(
                user_id=user_id,
                entity_type="post",
                entity_id=post_id,
                action="publish",
                action_category="publishing",
                description=f"Publish to {platform}: "
                            f"{'success' if outcome.get('published') else 'failed'}",
                status="success" if outcome.get("published") else "failed",
                error_message=outcome.get("error"),
                new_values={
                    "platform": platform,
                    "platform_post_id": outcome.get("platform_post_id"),
                    "url": outcome.get("url"),
                },
                extra_metadata={"account_id": account_row.id if account_row else None},
            )
            db.add(log)

            # Track on the post itself.
            if outcome.get("published"):
                platform_post_ids[platform] = outcome.get("platform_post_id") or ""
                platforms_meta.setdefault(platform, {})
                platforms_meta[platform].update({
                    "published_at": dt.datetime.utcnow().isoformat(),
                    "url": outcome.get("url"),
                    "post_id": outcome.get("platform_post_id"),
                })
                if account_row:
                    account_row.last_sync_at = dt.datetime.utcnow()

            results.append(outcome)

        post.platform_post_ids = platform_post_ids
        post.platforms = platforms_meta
        post.status = "published" if any(r.get("published") for r in results) else "failed"
        if post.status == "published" and not post.published_at:
            post.published_at = dt.datetime.utcnow()
        db.commit()

        return {
            "post_id": post_id,
            "results": results,
            "summary": {
                "total": len(results),
                "successes": sum(1 for r in results if r.get("published")),
                "failures": sum(1 for r in results if not r.get("published")),
            },
        }
