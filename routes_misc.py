from __future__ import annotations

from fastapi import APIRouter, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select

import auth
import codes
import quota
from db import Solved, User, SessionLocal


router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    user = auth.current_user(request)
    if user is None:
        return RedirectResponse("/auth/login", status_code=303)
    with SessionLocal() as s:
        user = s.get(User, user.id)
        score = s.scalar(
            select(func.coalesce(func.sum(Solved.points), 0)).where(Solved.user_id == user.id)
        )
        solved_count = s.scalar(
            select(func.count(Solved.id)).where(Solved.user_id == user.id)
        )
        remaining = quota.remaining(s, user)
    return templates.TemplateResponse(
        request, "profile.html",
        {
            "user": user,
            "score": score,
            "solved_count": solved_count,
            "remaining": remaining,
            "message": None,
            "message_kind": None,
        },
    )


@router.post("/profile/redeem", response_class=HTMLResponse)
async def redeem(request: Request, code: str = Form(...)):
    user = auth.current_user(request)
    if user is None:
        return RedirectResponse("/auth/login", status_code=303)
    with SessionLocal() as s:
        user = s.get(User, user.id)
        err = codes.redeem(s, user, code)
        score = s.scalar(
            select(func.coalesce(func.sum(Solved.points), 0)).where(Solved.user_id == user.id)
        )
        solved_count = s.scalar(
            select(func.count(Solved.id)).where(Solved.user_id == user.id)
        )
        remaining = quota.remaining(s, user)
    if err == "empty":
        msg, kind = "Введите код.", "err"
    elif err == "not_found":
        msg, kind = "Код не найден.", "err"
    elif err == "used":
        msg, kind = "Код уже использован.", "err"
    else:
        msg, kind = "Код активирован. Дневной лимит снят.", "ok"
    return templates.TemplateResponse(
        request, "profile.html",
        {
            "user": user,
            "score": score,
            "solved_count": solved_count,
            "remaining": remaining,
            "message": msg,
            "message_kind": kind,
        },
    )


@router.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard(request: Request):
    with SessionLocal() as s:
        rows = s.execute(
            select(
                User.nickname,
                func.coalesce(func.sum(Solved.points), 0).label("score"),
                func.count(Solved.id).label("solved"),
            )
            .join(Solved, Solved.user_id == User.id)
            .group_by(User.id)
            .order_by(func.sum(Solved.points).desc())
            .limit(100)
        ).all()
    user = auth.current_user(request)
    return templates.TemplateResponse(
        request, "leaderboard.html",
        {"user": user, "rows": rows},
    )
