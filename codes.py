from __future__ import annotations

import secrets
from typing import Optional

from sqlalchemy.orm import Session

from db import UnlockCode, User, utcnow


def generate(s: Session) -> str:
    code = secrets.token_urlsafe(12)
    s.add(UnlockCode(code=code))
    s.commit()
    return code


def redeem(s: Session, user: User, raw: str) -> Optional[str]:
    raw = raw.strip()
    if not raw:
        return "empty"
    row = s.get(UnlockCode, raw)
    if row is None:
        return "not_found"
    if row.used_by is not None:
        return "used"
    row.used_by = user.id
    row.used_at = utcnow()
    user.unlimited = True
    s.commit()
    return None
