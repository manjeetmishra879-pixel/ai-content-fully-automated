"""
SchedulerEngine — schedules posts in the DB with optional human-mimicry
delay and best-time learning.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.engines.base import BaseEngine
from app.engines.distribution.account_manager import AccountManager
from app.engines.distribution.human_mimicry import HumanMimicryEngine
from app.engines.learning.timing_engines import BestTimeEngine
from app.models.models import Schedule, Account


class SchedulerEngine(BaseEngine):
    name = "scheduler"
    description = "Schedule posts with smart best-time + jitter"

    def __init__(self) -> None:
        super().__init__()
        self.best_time = BestTimeEngine()
        self.human = HumanMimicryEngine()
        self.account_mgr = AccountManager()

    def run(self, action: str = "schedule", **kwargs: Any) -> Any:
        if action == "schedule":
            return self.schedule(**kwargs)
        if action == "list":
            return self.list_pending(**kwargs)
        if action == "cancel":
            return self.cancel(**kwargs)
        raise ValueError("action must be schedule|list|cancel")

    # ------------------------------------------------------------------
    def schedule(
        self,
        *,
        db: Session,
        user_id: int,
        post_id: int,
        platform: str,
        account_id: Optional[int] = None,
        scheduled_at: Optional[dt.datetime] = None,
        use_best_time: bool = True,
        jitter_seconds: int = 180,
    ) -> Dict[str, Any]:
        # account_id is required by the model — auto-rotate if missing.
        if not account_id:
            rotated = self.account_mgr(action="rotate", db=db, user_id=user_id, platform=platform)
            if not rotated:
                raise ValueError(f"No active account found for {platform}; "
                                 f"register one first.")
            account_id = rotated["id"]

        if scheduled_at is None and use_best_time:
            slots = self.best_time(platform=platform)["times"]
            target = self._next_slot(slots[0]) if slots else dt.datetime.utcnow() + dt.timedelta(hours=1)
        elif scheduled_at is None:
            target = dt.datetime.utcnow() + dt.timedelta(hours=1)
        else:
            target = scheduled_at

        if jitter_seconds:
            jitter = self.human(action="delay", base_seconds=jitter_seconds)["delay_seconds"]
            target = target + dt.timedelta(seconds=jitter)

        sched = Schedule(
            user_id=user_id,
            post_id=post_id,
            account_id=account_id,
            platform=platform,
            scheduled_time=target,
            status="pending",
        )
        db.add(sched); db.commit(); db.refresh(sched)
        return self._serialize(sched)

    def list_pending(self, *, db: Session, user_id: int) -> List[Dict[str, Any]]:
        rows = (db.query(Schedule)
                .filter(Schedule.user_id == user_id, Schedule.status == "pending")
                .order_by(Schedule.scheduled_time.asc()).all())
        return [self._serialize(r) for r in rows]

    def cancel(self, *, db: Session, schedule_id: int) -> bool:
        s = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not s:
            return False
        s.status = "cancelled"
        db.commit()
        return True

    @staticmethod
    def _next_slot(hhmm: str) -> dt.datetime:
        hour, minute = (int(x) for x in hhmm.split(":"))
        now = dt.datetime.utcnow()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += dt.timedelta(days=1)
        return target

    @staticmethod
    def _serialize(s: Schedule) -> Dict[str, Any]:
        return {
            "id": s.id, "user_id": s.user_id, "post_id": s.post_id,
            "account_id": s.account_id, "platform": s.platform,
            "scheduled_time": s.scheduled_time.isoformat() if s.scheduled_time else None,
            "status": s.status,
        }
