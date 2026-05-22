from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session

import config
from db import Quota, User


def _today_key() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def _row(s: Session, user_id: int) -> Quota:
    key = _today_key()
    row = s.query(Quota).filter_by(user_id=user_id, date=key).one_or_none()
    if row is None:
        row = Quota(user_id=user_id, date=key, used=0)
        s.add(row)
        s.flush()
    return row


def remaining(s: Session, user: User) -> int:
    if user.unlimited:
        return -1
    row = _row(s, user.id)
    return max(0, config.DAILY_QUOTA - row.used)


def try_consume(s: Session, user: User) -> bool:
    if user.unlimited:
        return True
    row = _row(s, user.id)
    if row.used >= config.DAILY_QUOTA:
        return False
    row.used += 1
    s.commit()
    return True
