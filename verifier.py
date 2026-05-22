from __future__ import annotations

import logging
import re
from typing import Iterable

import config
import gemini_client
from levels import Level, Verification


log = logging.getLogger("mipt_prompts.judge")


def _contains(text: str, flag: str) -> bool:
    return flag.lower() in text.lower()


def _signal(text: str, flag: str) -> bool:
    pattern = re.compile(re.escape(flag), re.IGNORECASE)
    return bool(pattern.search(text))


def _judge(level: Level, conversation: list[dict], last_response: str) -> bool:
    v = level.verification
    if not v.judge_prompt:
        return False
    model = v.judge_model or config.JUDGE_MODEL

    transcript_parts = []
    for m in conversation:
        who = "Пользователь" if m["role"] == "user" else "Модель"
        transcript_parts.append(f"{who}: {m['content']}")
    transcript_parts.append(f"Модель: {last_response}")
    transcript = "\n\n".join(transcript_parts)

    prompt = v.judge_prompt.replace("{{conversation}}", transcript).replace("{{response}}", last_response)
    prompt += "\n\nСначала одно-два предложения краткого рассуждения. Последней строкой - вердикт строго одним словом: YES или NO."
    raw = gemini_client.generate_simple(model, prompt).strip()
    last_line = raw.splitlines()[-1].strip().upper() if raw else ""
    verdict = last_line.startswith("YES")
    log.info(
        "level=%s verdict=%s reasoning=%s",
        level.id, "YES" if verdict else "NO",
        " | ".join(line.strip() for line in raw.splitlines() if line.strip())[:600],
    )
    return verdict


def check(level: Level, conversation: list[dict], last_response: str) -> bool:
    v = level.verification
    if v.type == "contains":
        return v.flag is not None and _contains(last_response, v.flag)
    if v.type == "signal":
        return v.flag is not None and _signal(last_response, v.flag)
    if v.type == "judge":
        return _judge(level, conversation, last_response)
    return False


def check_submitted_flag(level: Level, submitted: str) -> bool:
    v = level.verification
    if v.flag is None:
        return False
    return v.flag.strip().lower() == submitted.strip().lower()


def apply_input_filters(text: str, patterns: Iterable[str]) -> bool:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def apply_output_filters(text: str, patterns: Iterable[str]) -> str:
    out = text
    for p in patterns:
        out = re.sub(p, "[ЗАБЛОКИРОВАНО]", out, flags=re.IGNORECASE)
    return out
