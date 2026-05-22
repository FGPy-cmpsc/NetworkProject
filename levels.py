from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yaml

import config


@dataclass(frozen=True)
class Verification:
    type: str
    flag: Optional[str] = None
    judge_prompt: Optional[str] = None
    judge_model: Optional[str] = None


@dataclass(frozen=True)
class Level:
    id: str
    track: str
    order: int
    title: str
    description: str
    points: int
    model: str
    multi_turn: bool
    system_prompt: str
    verification: Verification
    afterword: str
    input_filters: tuple[str, ...]
    output_filters: tuple[str, ...]
    judge_on_response: bool
    submit_mode: str


@dataclass(frozen=True)
class Track:
    id: str
    title: str
    description: str
    order: int
    unlock_mode: str
    levels: tuple[Level, ...]


_tracks: dict[str, Track] = {}
_levels: dict[str, Level] = {}


def _load_level(path: str, track_id: str) -> Level:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    vraw = data.get("verification") or {}
    verification = Verification(
        type=vraw.get("type", "contains"),
        flag=vraw.get("flag"),
        judge_prompt=vraw.get("judge_prompt"),
        judge_model=vraw.get("judge_model"),
    )
    return Level(
        id=data["id"],
        track=track_id,
        order=int(data.get("order", 0)),
        title=data["title"],
        description=data.get("description", ""),
        points=int(data["points"]),
        model=data["model"],
        multi_turn=bool(data.get("multi_turn", False)),
        system_prompt=data["system_prompt"],
        verification=verification,
        afterword=data.get("afterword", ""),
        input_filters=tuple(data.get("input_filters", []) or []),
        output_filters=tuple(data.get("output_filters", []) or []),
        judge_on_response=bool(data.get("judge_on_response", False)),
        submit_mode=data.get("submit_mode", "auto"),
    )


def _load_track(track_dir: str) -> Track:
    meta_path = os.path.join(track_dir, "_track.yaml")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    track_id = meta["id"]
    level_files = sorted(
        f for f in os.listdir(track_dir)
        if f.endswith(".yaml") and not f.startswith("_")
    )
    levels = tuple(sorted(
        (_load_level(os.path.join(track_dir, f), track_id) for f in level_files),
        key=lambda l: l.order,
    ))
    return Track(
        id=track_id,
        title=meta["title"],
        description=meta.get("description", ""),
        order=int(meta.get("order", 0)),
        unlock_mode=meta.get("unlock_mode", "linear"),
        levels=levels,
    )


def load_all() -> None:
    _tracks.clear()
    _levels.clear()
    if not os.path.isdir(config.LEVELS_DIR):
        return
    for name in sorted(os.listdir(config.LEVELS_DIR)):
        track_dir = os.path.join(config.LEVELS_DIR, name)
        if not os.path.isdir(track_dir):
            continue
        if not os.path.isfile(os.path.join(track_dir, "_track.yaml")):
            continue
        track = _load_track(track_dir)
        _tracks[track.id] = track
        for level in track.levels:
            _levels[level.id] = level


def all_tracks() -> list[Track]:
    return sorted(_tracks.values(), key=lambda t: t.order)


def get_track(track_id: str) -> Optional[Track]:
    return _tracks.get(track_id)


def get_level(level_id: str) -> Optional[Level]:
    return _levels.get(level_id)


def levels_unlocked_for(track: Track, solved_ids: set[str]) -> list[tuple[Level, bool]]:
    if track.unlock_mode == "free":
        return [(lvl, True) for lvl in track.levels]
    result = []
    unlocked_next = True
    for lvl in track.levels:
        result.append((lvl, unlocked_next))
        unlocked_next = unlocked_next and (lvl.id in solved_ids)
    return result
