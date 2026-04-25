"""
Account management endpoints — register social accounts + credentials.
"""

import secrets
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.engines import get_engine
from app.models.models import Account

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    platform: str = Field(..., description="telegram|x|facebook|instagram|linkedin|youtube|reddit")
    account_handle: str = Field(..., description="Public handle / username")
    credentials: Dict[str, Any] = Field(default_factory=dict)
    category: Optional[str] = None
    language: Optional[str] = None


class AccountUpdate(BaseModel):
    account_handle: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    category: Optional[str] = None
    language: Optional[str] = None


def _serialize(a: Account) -> Dict[str, Any]:
    return {
        "id": a.id, "platform": a.platform, "account_handle": a.account_handle,
        "category": a.category, "language": a.language,
        "is_active": a.is_active,
        "health_score": a.health_score,
        "last_published_at": a.last_published_at,
        "credentials_set": bool(a.credentials),
    }


@router.get("/")
async def list_accounts(
    platform: Optional[str] = None,
    user_id: int = Depends(lambda: 1),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    return get_engine("account_manager")(action="list", db=db, user_id=user_id,
                                          platform=platform)


@router.post("/")
async def create_account(
    payload: AccountCreate,
    user_id: int = Depends(lambda: 1),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    return get_engine("account_manager")(action="register", db=db, user_id=user_id,
                                          **payload.dict())


@router.get("/rotate")
async def rotate_account(
    platform: str,
    strategy: str = "least_recent",
    user_id: int = Depends(lambda: 1),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    result = get_engine("account_manager")(action="rotate", db=db, user_id=user_id,
                                            platform=platform, strategy=strategy)
    if not result:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                             f"No active accounts on {platform}")
    return result


@router.patch("/{account_id}")
async def update_account(
    account_id: int,
    payload: AccountUpdate,
    user_id: int = Depends(lambda: 1),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    a = db.query(Account).filter(Account.id == account_id,
                                  Account.user_id == user_id).first()
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    for field, value in payload.dict(exclude_none=True).items():
        setattr(a, field, value)
    db.commit(); db.refresh(a)
    return _serialize(a)


@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    user_id: int = Depends(lambda: 1),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    ok = get_engine("account_manager")(action="deactivate", db=db, account_id=account_id)
    return {"deactivated": account_id, "ok": bool(ok)}


class ShadowbanRequest(BaseModel):
    recent_metrics: List[Dict[str, Any]]
    baseline_metrics: List[Dict[str, Any]]
    metric: str = "impressions"


@router.post("/shadowban-check")
async def shadowban_check(payload: ShadowbanRequest) -> Dict[str, Any]:
    return get_engine("shadowban_detection")(**payload.dict())


# OAuth endpoints for connecting accounts
@router.get("/oauth/{platform}")
async def oauth_initiate(
    platform: str,
    user_id: int = Depends(lambda: 1),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Initiate OAuth flow for a platform"""
    if platform not in ["instagram", "facebook", "linkedin", "youtube", "x", "tiktok"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"OAuth not supported for {platform}")

    # Generate state parameter for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in session/cache (simplified - in production use Redis/session)
    # For now, we'll just return the auth URL

    auth_urls = {
        "instagram": f"https://api.instagram.com/oauth/authorize?client_id=YOUR_INSTAGRAM_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&scope=user_profile,user_media&response_type=code&state={state}",
        "facebook": f"https://www.facebook.com/v18.0/dialog/oauth?client_id=YOUR_FACEBOOK_APP_ID&redirect_uri=YOUR_REDIRECT_URI&scope=pages_manage_posts,pages_read_engagement&response_type=code&state={state}",
        "linkedin": f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=YOUR_LINKEDIN_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&scope=w_member_social&state={state}",
        "youtube": f"https://accounts.google.com/o/oauth2/auth?client_id=YOUR_YOUTUBE_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&scope=https://www.googleapis.com/auth/youtube.upload&response_type=code&access_type=offline&state={state}",
        "x": f"https://twitter.com/i/oauth2/authorize?response_type=code&client_id=YOUR_X_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&scope=tweet.write&state={state}&code_challenge=YOUR_CHALLENGE&code_challenge_method=S256",
        "tiktok": f"https://www.tiktok.com/auth/authorize?client_key=YOUR_TIKTOK_CLIENT_KEY&scope=user.info.basic,video.publish&response_type=code&redirect_uri=YOUR_REDIRECT_URI&state={state}",
    }

    if platform not in auth_urls:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"OAuth URL not configured for {platform}")

    return {
        "auth_url": auth_urls[platform],
        "state": state,
        "platform": platform
    }


@router.get("/oauth/{platform}/callback")
async def oauth_callback(
    platform: str,
    code: str,
    state: str,
    error: Optional[str] = None,
    user_id: int = Depends(lambda: 1),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Handle OAuth callback and exchange code for tokens"""
    if error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"OAuth error: {error}")

    # Verify state parameter (simplified)
    # In production, verify against stored state

    # Exchange code for access token
    token_data = await _exchange_code_for_token(platform, code)

    # Get user profile info
    profile_data = await _get_platform_profile(platform, token_data)

    # Register/update account
    account_data = get_engine("account_manager")(
        action="register",
        db=db,
        user_id=user_id,
        platform=platform,
        account_handle=profile_data["username"],
        credentials=token_data,
        category=profile_data.get("category"),
        language=profile_data.get("language")
    )

    return {
        "message": f"Successfully connected {platform} account",
        "account": account_data
    }


async def _exchange_code_for_token(platform: str, code: str) -> Dict[str, Any]:
    """Exchange OAuth code for access token"""
    import httpx

    # Platform-specific token exchange
    if platform == "instagram":
        # Instagram Basic Display API
        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.instagram.com/oauth/access_token", data={
                "client_id": "YOUR_INSTAGRAM_CLIENT_ID",
                "client_secret": "YOUR_INSTAGRAM_CLIENT_SECRET",
                "grant_type": "authorization_code",
                "redirect_uri": "YOUR_REDIRECT_URI",
                "code": code
            })
            response.raise_for_status()
            return response.json()

    elif platform == "facebook":
        # Facebook Graph API
        async with httpx.AsyncClient() as client:
            response = await client.post("https://graph.facebook.com/v18.0/oauth/access_token", data={
                "client_id": "YOUR_FACEBOOK_APP_ID",
                "client_secret": "YOUR_FACEBOOK_APP_SECRET",
                "redirect_uri": "YOUR_REDIRECT_URI",
                "code": code
            })
            response.raise_for_status()
            return response.json()

    elif platform == "linkedin":
        # LinkedIn OAuth 2.0
        async with httpx.AsyncClient() as client:
            response = await client.post("https://www.linkedin.com/oauth/v2/accessToken", data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": "YOUR_LINKEDIN_CLIENT_ID",
                "client_secret": "YOUR_LINKEDIN_CLIENT_SECRET",
                "redirect_uri": "YOUR_REDIRECT_URI"
            })
            response.raise_for_status()
            return response.json()

    elif platform == "youtube":
        # Google OAuth 2.0
        async with httpx.AsyncClient() as client:
            response = await client.post("https://oauth2.googleapis.com/token", data={
                "client_id": "YOUR_YOUTUBE_CLIENT_ID",
                "client_secret": "YOUR_YOUTUBE_CLIENT_SECRET",
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": "YOUR_REDIRECT_URI"
            })
            response.raise_for_status()
            return response.json()

    elif platform == "x":
        # Twitter OAuth 2.0
        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.twitter.com/2/oauth2/token", data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": "YOUR_X_CLIENT_ID",
                "redirect_uri": "YOUR_REDIRECT_URI",
                "code_verifier": "YOUR_CODE_VERIFIER"
            })
            response.raise_for_status()
            return response.json()

    elif platform == "tiktok":
        # TikTok OAuth
        async with httpx.AsyncClient() as client:
            response = await client.post("https://open-api.tiktok.com/oauth/access_token/", data={
                "client_key": "YOUR_TIKTOK_CLIENT_KEY",
                "client_secret": "YOUR_TIKTOK_CLIENT_SECRET",
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": "YOUR_REDIRECT_URI"
            })
            response.raise_for_status()
            return response.json()

    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"OAuth not implemented for {platform}")


async def _get_platform_profile(platform: str, token_data: Dict[str, Any]) -> Dict[str, Any]:
    """Get user profile from platform API"""
    import httpx

    access_token = token_data.get("access_token")

    if platform == "instagram":
        async with httpx.AsyncClient() as client:
            response = await client.get("https://graph.instagram.com/me",
                                      params={"fields": "id,username", "access_token": access_token})
            response.raise_for_status()
            data = response.json()
            return {
                "username": data.get("username", f"instagram_{data.get('id')}"),
                "platform_user_id": data["id"],
                "category": "personal",
                "language": "en"
            }

    elif platform == "facebook":
        async with httpx.AsyncClient() as client:
            # Get pages the user manages
            response = await client.get("https://graph.facebook.com/v18.0/me/accounts",
                                      params={"access_token": access_token})
            response.raise_for_status()
            pages = response.json().get("data", [])
            if pages:
                page = pages[0]  # Use first page
                return {
                    "username": page.get("name", f"facebook_{page.get('id')}"),
                    "platform_user_id": page["id"],
                    "category": "business",
                    "language": "en"
                }

    elif platform == "linkedin":
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.linkedin.com/v2/people/~",
                                      headers={"Authorization": f"Bearer {access_token}"})
            response.raise_for_status()
            data = response.json()
            return {
                "username": data.get("localizedFirstName", "") + " " + data.get("localizedLastName", ""),
                "platform_user_id": data.get("id"),
                "category": "professional",
                "language": "en"
            }

    elif platform == "youtube":
        async with httpx.AsyncClient() as client:
            response = await client.get("https://www.googleapis.com/youtube/v3/channels",
                                      params={"part": "snippet", "mine": "true", "access_token": access_token})
            response.raise_for_status()
            data = response.json()
            if data.get("items"):
                channel = data["items"][0]
                return {
                    "username": channel["snippet"]["title"],
                    "platform_user_id": channel["id"],
                    "category": "content_creator",
                    "language": "en"
                }

    elif platform == "x":
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.twitter.com/2/users/me",
                                      headers={"Authorization": f"Bearer {access_token}"})
            response.raise_for_status()
            data = response.json().get("data", {})
            return {
                "username": data.get("username"),
                "platform_user_id": data.get("id"),
                "category": "personal",
                "language": "en"
            }

    elif platform == "tiktok":
        async with httpx.AsyncClient() as client:
            response = await client.get("https://open-api.tiktok.com/user/info/",
                                      params={"access_token": access_token})
            response.raise_for_status()
            data = response.json().get("data", {})
            return {
                "username": data.get("display_name"),
                "platform_user_id": data.get("open_id"),
                "category": "content_creator",
                "language": "en"
            }

    # Default fallback
    return {
        "username": f"{platform}_user",
        "platform_user_id": "unknown",
        "category": "personal",
        "language": "en"
    }
