from __future__ import annotations

import re
import secrets
from datetime import timedelta
from typing import Optional

import bcrypt
from fastapi import Request
from itsdangerous import URLSafeSerializer, BadSignature
from sqlalchemy import select

import config
from db import User, EmailToken, SessionLocal, utcnow


NICKNAME_RE = re.compile(r"^[A-Za-z0-9_\-А-Яа-яЁё]{2,32}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_serializer = URLSafeSerializer(config.SESSION_SECRET, salt="ctf-session")


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def sign_session(user_id: int) -> str:
    return _serializer.dumps({"uid": user_id})


def read_session(raw: str) -> Optional[int]:
    try:
        data = _serializer.loads(raw)
    except BadSignature:
        return None
    if not isinstance(data, dict):
        return None
    uid = data.get("uid")
    return uid if isinstance(uid, int) else None


def current_user_id(request: Request) -> Optional[int]:
    raw = request.cookies.get(config.SESSION_COOKIE)
    if not raw:
        return None
    return read_session(raw)


def current_user(request: Request) -> Optional[User]:
    uid = current_user_id(request)
    if uid is None:
        return None
    with SessionLocal() as s:
        return s.get(User, uid)


def validate_email(email: str) -> Optional[str]:
    email = email.strip().lower()
    if not email or len(email) > 255 or not EMAIL_RE.match(email):
        return None
    return email


def validate_nickname(nickname: str) -> Optional[str]:
    nickname = nickname.strip()
    if not NICKNAME_RE.match(nickname):
        return None
    return nickname


def validate_password(password: str) -> bool:
    return 8 <= len(password) <= 128


def make_email_token(user_id: int, kind: str) -> EmailToken:
    return EmailToken(
        token=secrets.token_urlsafe(32),
        user_id=user_id,
        kind=kind,
        expires_at=utcnow() + timedelta(hours=config.EMAIL_TOKEN_TTL_HOURS),
    )


def consume_email_token(token: str, kind: str) -> Optional[int]:
    with SessionLocal() as s:
        row = s.get(EmailToken, token)
        if row is None or row.kind != kind:
            return None
        if row.expires_at < utcnow():
            s.delete(row)
            s.commit()
            return None
        uid = row.user_id
        s.delete(row)
        s.commit()
        return uid
