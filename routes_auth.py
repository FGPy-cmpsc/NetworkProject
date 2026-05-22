from __future__ import annotations

import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

import auth
import config
import email_sender
from db import User, SessionLocal


router = APIRouter()
templates = Jinja2Templates(directory="templates")
log = logging.getLogger("mipt_prompts.auth")


def _render(request: Request, name: str, **ctx) -> HTMLResponse:
    return templates.TemplateResponse(request, name, ctx)


@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    if auth.current_user_id(request):
        return RedirectResponse("/", status_code=303)
    return _render(request, "auth/register.html", error=None, values={})


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    nickname: str = Form(...),
    password: str = Form(...),
):
    values = {"email": email, "nickname": nickname}

    em = auth.validate_email(email)
    if em is None:
        return _render(request, "auth/register.html", error="Некорректный email.", values=values)
    nk = auth.validate_nickname(nickname)
    if nk is None:
        return _render(
            request,
            "auth/register.html",
            error="Никнейм: 2-32 символа, буквы/цифры/_/-",
            values=values,
        )
    if not auth.validate_password(password):
        return _render(request, "auth/register.html", error="Пароль: 8-128 символов.", values=values)

    with SessionLocal() as s:
        existing_email = s.scalar(select(User).where(User.email == em))
        if existing_email is not None:
            return _render(
                request, "auth/register.html",
                error="Email уже зарегистрирован.", values=values,
            )
        existing_nick = s.scalar(select(User).where(User.nickname == nk))
        if existing_nick is not None:
            return _render(
                request, "auth/register.html",
                error="Никнейм занят.", values=values,
            )
        user = User(
            email=em,
            nickname=nk,
            password_hash=auth.hash_password(password),
            email_verified=False,
        )
        s.add(user)
        s.flush()
        token = auth.make_email_token(user.id, "verify")
        s.add(token)
        s.commit()
        token_value = token.token

    link = f"{config.SITE_URL}/auth/verify?token={token_value}"
    try:
        email_sender.send_verification(em, link)
    except Exception:
        log.exception("smtp send failed for %s", em)
        return _render(
            request, "auth/register.html",
            error="Не удалось отправить письмо. Попробуйте позже.",
            values=values,
        )

    return _render(request, "auth/verify_sent.html", email=em)


@router.get("/verify", response_class=HTMLResponse)
async def verify(request: Request, token: str = ""):
    if not token:
        return _render(request, "auth/verify_done.html", ok=False, message="Нет токена.")
    uid = auth.consume_email_token(token, "verify")
    if uid is None:
        return _render(request, "auth/verify_done.html", ok=False, message="Ссылка недействительна или истекла.")
    with SessionLocal() as s:
        user = s.get(User, uid)
        if user is None:
            return _render(request, "auth/verify_done.html", ok=False, message="Пользователь не найден.")
        user.email_verified = True
        s.commit()
    return _render(request, "auth/verify_done.html", ok=True, message="Почта подтверждена, теперь можно войти.")


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    if auth.current_user_id(request):
        return RedirectResponse("/", status_code=303)
    return _render(request, "auth/login.html", error=None, values={})


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    em = auth.validate_email(email)
    if em is None:
        return _render(request, "auth/login.html", error="Некорректный email.", values={"email": email})
    with SessionLocal() as s:
        user = s.scalar(select(User).where(User.email == em))
        if user is None or not auth.verify_password(password, user.password_hash):
            return _render(request, "auth/login.html", error="Неверный email или пароль.", values={"email": em})
        if not user.email_verified:
            return _render(
                request, "auth/login.html",
                error="Подтвердите email через ссылку в письме.",
                values={"email": em},
            )
        uid = user.id

    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(
        config.SESSION_COOKIE,
        auth.sign_session(uid),
        max_age=config.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=config.SITE_URL.startswith("https"),
    )
    return resp


@router.post("/logout")
async def logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(config.SESSION_COOKIE)
    return resp
