from __future__ import annotations

import logging

from fastapi import APIRouter, Form, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

import auth
import config
import levels
import quota
import rate_limit
import verifier
import gemini_client
from db import Conversation, Message, Solved, SessionLocal


router = APIRouter()
templates = Jinja2Templates(directory="templates")
log = logging.getLogger("mipt_prompts.game")


def _solved_ids(s, user_id: int) -> set[str]:
    rows = s.execute(select(Solved.level_id).where(Solved.user_id == user_id)).all()
    return {r[0] for r in rows}


def _require_user(request: Request):
    user = auth.current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    return user


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = auth.current_user(request)
    if user is None:
        return templates.TemplateResponse(request, "landing.html")
    with SessionLocal() as s:
        solved_ids = _solved_ids(s, user.id)
        total_points = s.execute(
            select(Solved.points).where(Solved.user_id == user.id)
        ).all()
        score = sum(r[0] for r in total_points)
        remaining = quota.remaining(s, user)
    tracks_view = []
    for tr in levels.all_tracks():
        solved_count = sum(1 for lvl in tr.levels if lvl.id in solved_ids)
        tracks_view.append({
            "track": tr,
            "solved": solved_count,
            "total": len(tr.levels),
        })
    return templates.TemplateResponse(
        request, "tracks.html",
        {"user": user, "tracks": tracks_view, "score": score, "remaining": remaining},
    )


@router.get("/track/{track_id}", response_class=HTMLResponse)
async def track_view(track_id: str, request: Request):
    user = _require_user(request)
    track = levels.get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404)
    with SessionLocal() as s:
        solved_ids = _solved_ids(s, user.id)
    rows = levels.levels_unlocked_for(track, solved_ids)
    view = [
        {"level": lvl, "unlocked": unlocked, "solved": lvl.id in solved_ids}
        for lvl, unlocked in rows
    ]
    return templates.TemplateResponse(
        request, "track.html",
        {"user": user, "track": track, "rows": view},
    )


def _level_unlocked(track, level_id: str, solved_ids: set[str]) -> bool:
    rows = levels.levels_unlocked_for(track, solved_ids)
    for lvl, unlocked in rows:
        if lvl.id == level_id:
            return unlocked
    return False


@router.get("/level/{level_id}", response_class=HTMLResponse)
async def level_view(level_id: str, request: Request):
    user = _require_user(request)
    level = levels.get_level(level_id)
    if level is None:
        raise HTTPException(status_code=404)
    track = levels.get_track(level.track)
    with SessionLocal() as s:
        solved_ids = _solved_ids(s, user.id)
        if not _level_unlocked(track, level.id, solved_ids):
            raise HTTPException(status_code=403, detail="locked")
        already_solved = level.id in solved_ids
        history = []
        if level.multi_turn:
            conv = s.scalar(
                select(Conversation).where(
                    Conversation.user_id == user.id,
                    Conversation.level_id == level.id,
                    Conversation.finished == False,
                ).order_by(Conversation.id.desc())
            )
            if conv is not None:
                for m in conv.messages:
                    history.append({"role": m.role, "content": m.content})
        remaining = quota.remaining(s, user)
    template = "level_chat.html" if level.multi_turn else "level_single.html"
    return templates.TemplateResponse(
        request, template,
        {
            "user": user,
            "level": level,
            "track": track,
            "already_solved": already_solved,
            "history": history,
            "remaining": remaining,
            "max_turns": config.MAX_CONVERSATION_TURNS,
        },
    )


@router.post("/level/{level_id}/reset")
async def level_reset(level_id: str, request: Request):
    user = _require_user(request)
    level = levels.get_level(level_id)
    if level is None or not level.multi_turn:
        raise HTTPException(status_code=404)
    with SessionLocal() as s:
        convs = s.scalars(
            select(Conversation).where(
                Conversation.user_id == user.id,
                Conversation.level_id == level.id,
                Conversation.finished == False,
            )
        ).all()
        for c in convs:
            c.finished = True
        s.commit()
    return RedirectResponse(f"/level/{level_id}", status_code=303)


@router.post("/level/{level_id}/submit")
async def level_submit(level_id: str, request: Request):
    user = _require_user(request)
    level = levels.get_level(level_id)
    if level is None:
        raise HTTPException(status_code=404)

    data = await request.json()
    message = (data.get("message") or "").strip()
    if not message:
        return JSONResponse({"error": "Пустое сообщение."}, status_code=400)
    if len(message) > 4000:
        return JSONResponse({"error": "Слишком длинное сообщение (макс 4000 символов)."}, status_code=400)

    track = levels.get_track(level.track)
    with SessionLocal() as s:
        solved_ids = _solved_ids(s, user.id)
        if not _level_unlocked(track, level.id, solved_ids):
            raise HTTPException(status_code=403, detail="locked")
        if level.id in solved_ids:
            return JSONResponse({"error": "Уровень уже пройден."}, status_code=400)

        if verifier.apply_input_filters(message, level.input_filters):
            return JSONResponse(
                {"error": "Сообщение заблокировано фильтром на входе.", "filtered_in": True}
            )

        if not quota.try_consume(s, user):
            return JSONResponse(
                {"error": "Дневной лимит запросов исчерпан. Введите код доступа в профиле."},
                status_code=429,
            )

        conv_history: list[dict] = []
        conv = None
        if level.multi_turn:
            conv = s.scalar(
                select(Conversation).where(
                    Conversation.user_id == user.id,
                    Conversation.level_id == level.id,
                    Conversation.finished == False,
                ).order_by(Conversation.id.desc())
            )
            if conv is None:
                conv = Conversation(user_id=user.id, level_id=level.id)
                s.add(conv)
                s.flush()
            else:
                for m in conv.messages:
                    conv_history.append({"role": m.role, "content": m.content})
            user_msgs_count = sum(1 for m in conv_history if m["role"] == "user")
            if user_msgs_count >= config.MAX_CONVERSATION_TURNS:
                return JSONResponse(
                    {"error": f"Достигнут лимит {config.MAX_CONVERSATION_TURNS} сообщений за попытку."},
                    status_code=400,
                )

    allowed, wait = await rate_limit.acquire(config.GLOBAL_RATE_LIMIT_SECONDS)
    if not allowed:
        return JSONResponse(
            {"error": f"Подождите {wait} сек, сервер перегружен."},
            status_code=429,
        )

    try:
        raw_reply = gemini_client.generate(
            model=level.model,
            user_text=message,
            system_prompt=level.system_prompt,
            history=conv_history,
        )
    except Exception:
        log.exception("gemini failed for level %s", level.id)
        return JSONResponse({"error": "Ошибка вызова модели."}, status_code=500)

    reply_for_user = verifier.apply_output_filters(raw_reply, level.output_filters)

    solved = False
    if level.submit_mode == "auto":
        try:
            solved = verifier.check(level, conv_history, raw_reply)
        except Exception:
            log.exception("verifier failed for level %s", level.id)

    with SessionLocal() as s:
        if level.multi_turn:
            conv = s.scalar(
                select(Conversation).where(
                    Conversation.user_id == user.id,
                    Conversation.level_id == level.id,
                    Conversation.finished == False,
                ).order_by(Conversation.id.desc())
            )
            if conv is None:
                conv = Conversation(user_id=user.id, level_id=level.id)
                s.add(conv)
                s.flush()
            s.add(Message(conversation_id=conv.id, role="user", content=message))
            s.add(Message(conversation_id=conv.id, role="model", content=raw_reply))
            if solved:
                conv.finished = True
        if solved:
            existing = s.scalar(
                select(Solved).where(Solved.user_id == user.id, Solved.level_id == level.id)
            )
            if existing is None:
                s.add(Solved(user_id=user.id, level_id=level.id, points=level.points))
        s.commit()

    return {
        "reply": reply_for_user,
        "solved": solved,
        "afterword": level.afterword if solved else "",
        "points": level.points if solved else 0,
    }


@router.post("/level/{level_id}/submit_flag")
async def level_submit_flag(level_id: str, request: Request):
    user = _require_user(request)
    level = levels.get_level(level_id)
    if level is None:
        raise HTTPException(status_code=404)
    if level.submit_mode != "manual":
        return JSONResponse({"error": "У этого уровня нет формы для сдачи флага."}, status_code=400)

    data = await request.json()
    submitted = (data.get("flag") or "").strip()
    if not submitted:
        return JSONResponse({"error": "Введите флаг."}, status_code=400)
    if len(submitted) > 500:
        return JSONResponse({"error": "Слишком длинно."}, status_code=400)

    track = levels.get_track(level.track)
    with SessionLocal() as s:
        solved_ids = _solved_ids(s, user.id)
        if not _level_unlocked(track, level.id, solved_ids):
            raise HTTPException(status_code=403, detail="locked")
        if level.id in solved_ids:
            return {"solved": True, "already": True, "afterword": level.afterword, "points": 0}

        ok = verifier.check_submitted_flag(level, submitted)
        if ok:
            s.add(Solved(user_id=user.id, level_id=level.id, points=level.points))
            s.commit()
            return {
                "solved": True,
                "afterword": level.afterword,
                "points": level.points,
            }
    return {"solved": False, "error": "Неверный флаг."}
