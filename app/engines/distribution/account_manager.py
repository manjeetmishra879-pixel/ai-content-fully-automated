"""
AccountManager — register, list and rotate publishing accounts per platform.

Persists to the existing `accounts` table in Postgres. The Account model
stores `username`, `platform_user_id`, and `access_token`; full per-platform
credential dicts (e.g. multiple OAuth fields) live in `extra_metadata`.
"""

from __future__ import annotations

import datetime as dt
import random
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.engines.base import BaseEngine
from app.models.models import Account


class AccountManager(BaseEngine):
    name = "account_manager"
    description = "Manage publishing accounts and rotation"

    def run(self, action: str = "list", **kwargs: Any) -> Any:
        if action == "register":
            return self.register(**kwargs)
        if action == "rotate":
            return self.rotate(**kwargs)
        if action == "list":
            return self.list_accounts(**kwargs)
        if action == "deactivate":
            return self.deactivate(**kwargs)
        if action == "credentials":
            return self.get_credentials(**kwargs)
        raise ValueError("action must be register|list|rotate|deactivate|credentials")

    # ------------------------------------------------------------------
    def register(
        self,
        *,
        db: Session,
        user_id: int,
        platform: str,
        account_handle: str,
        credentials: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Use the platform handle as both username and platform_user_id when
        # the caller doesn't supply one explicitly.
        platform_user_id = (credentials or {}).get("platform_user_id") or account_handle

        existing = db.query(Account).filter(
            Account.user_id == user_id,
            Account.platform == platform,
            Account.username == account_handle,
        ).first()

        if existing:
            if credentials is not None:
                self._merge_credentials(existing, credentials)
            existing.is_active = True
            db.commit(); db.refresh(existing)
            return self._serialize(existing)

        acct = Account(
            user_id=user_id,
            platform=platform,
            platform_user_id=platform_user_id,
            username=account_handle,
            display_name=account_handle,
            is_active=True,
        )
        if credentials:
            self._merge_credentials(acct, credentials)
        if category or language:
            meta = dict(acct.extra_metadata or {})
            if category:
                meta["category"] = category
            if language:
                meta["language"] = language
            acct.extra_metadata = meta
        db.add(acct); db.commit(); db.refresh(acct)
        return self._serialize(acct)

    def list_accounts(self, *, db: Session, user_id: int,
                       platform: Optional[str] = None,
                       active_only: bool = True) -> List[Dict[str, Any]]:
        q = db.query(Account).filter(Account.user_id == user_id)
        if platform:
            q = q.filter(Account.platform == platform)
        if active_only:
            q = q.filter(Account.is_active.is_(True))
        return [self._serialize(a) for a in q.all()]

    def rotate(self, *, db: Session, user_id: int,
                platform: str, strategy: str = "least_recent") -> Optional[Dict[str, Any]]:
        accounts = (
            db.query(Account)
            .filter(Account.user_id == user_id, Account.platform == platform,
                    Account.is_active.is_(True))
            .all()
        )
        if not accounts:
            return None
        if strategy == "random":
            chosen = random.choice(accounts)
        elif strategy == "healthiest":
            chosen = max(accounts, key=lambda a: float(a.engagement_rate or 0))
        else:  # least_recent
            chosen = min(accounts, key=lambda a: (a.last_sync_at or dt.datetime(1970, 1, 1)))
        return self._serialize(chosen)

    def deactivate(self, *, db: Session, account_id: int) -> bool:
        a = db.query(Account).filter(Account.id == account_id).first()
        if not a:
            return False
        a.is_active = False
        db.commit()
        return True

    def get_credentials(self, *, db: Session, account_id: int) -> Dict[str, Any]:
        a = db.query(Account).filter(Account.id == account_id).first()
        if not a:
            return {}
        return self._extract_credentials(a)

    # ------------------------------------------------------------------
    @staticmethod
    def _merge_credentials(a: Account, creds: Dict[str, Any]) -> None:
        meta = dict(a.extra_metadata or {})
        existing = dict(meta.get("credentials") or {})
        existing.update({k: v for k, v in creds.items() if v is not None})
        meta["credentials"] = existing
        a.extra_metadata = meta
        # Keep access_token in its first-class column when present.
        if creds.get("access_token"):
            a.access_token = creds["access_token"]
        if creds.get("refresh_token"):
            a.refresh_token = creds["refresh_token"]

    @staticmethod
    def _extract_credentials(a: Account) -> Dict[str, Any]:
        meta = dict(a.extra_metadata or {})
        creds = dict(meta.get("credentials") or {})
        if a.access_token and "access_token" not in creds:
            creds["access_token"] = a.access_token
        if a.refresh_token and "refresh_token" not in creds:
            creds["refresh_token"] = a.refresh_token
        return creds

    @staticmethod
    def _serialize(a: Account) -> Dict[str, Any]:
        meta = dict(a.extra_metadata or {})
        creds = dict(meta.get("credentials") or {})
        return {
            "id": a.id, "user_id": a.user_id, "platform": a.platform,
            "account_handle": a.username,
            "display_name": a.display_name,
            "category": meta.get("category"),
            "language": meta.get("language"),
            "is_active": a.is_active,
            "is_shadowbanned": a.is_shadowbanned,
            "followers": a.followers,
            "engagement_rate": a.engagement_rate,
            "last_sync_at": a.last_sync_at.isoformat() if a.last_sync_at else None,
            "has_credentials": bool(creds) or bool(a.access_token),
        }
