"""
Account management endpoints — register social accounts + credentials.
"""

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
