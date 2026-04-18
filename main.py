import logging
import time
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("pomodoro-backend")

Mode = Literal["idle", "focus", "break"]

app = FastAPI(title="Pomodoro Control System")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

state: dict[str, Mode | float | int | None] = {
    "mode": "idle",
    "start_time": None,
    "duration": 0,
    "focus_duration": 1500,
    "break_duration": 300,
}


def minutes_to_seconds(minutes: int) -> int:
    return minutes * 60


def set_timer(mode: Mode, duration: int = 0) -> dict[str, Mode | int]:
    state["mode"] = mode
    state["duration"] = duration
    state["start_time"] = time.time() if mode != "idle" else None
    logger.info("mode=%s duration=%s", mode, duration)
    return status()


def start_break_timer() -> None:
    state["mode"] = "break"
    state["duration"] = int(state["break_duration"] or 300)
    state["start_time"] = time.time()
    logger.info("focus complete; auto-starting break duration=%s", state["duration"])


def status() -> dict[str, Mode | int]:
    mode = state["mode"]
    start_time = state["start_time"]
    duration = int(state["duration"] or 0)

    remaining_time = 0
    if mode != "idle" and start_time is not None:
        elapsed = int(time.time() - float(start_time))
        remaining_time = max(0, duration - elapsed)
        if mode == "focus" and remaining_time == 0:
            start_break_timer()
            mode = state["mode"]
            duration = int(state["duration"] or 0)
            remaining_time = duration

    return {
        "mode": mode,
        "remaining_time": remaining_time,
        "focus_duration": int(state["focus_duration"] or 1500),
        "break_duration": int(state["break_duration"] or 300),
    }


@app.get("/start")
def start(
    focus_minutes: int = Query(25, ge=1, le=240),
    break_minutes: int = Query(5, ge=1, le=120),
) -> dict[str, Mode | int]:
    state["focus_duration"] = minutes_to_seconds(focus_minutes)
    state["break_duration"] = minutes_to_seconds(break_minutes)
    return set_timer("focus", int(state["focus_duration"] or 1500))


@app.get("/pause")
def pause() -> dict[str, Mode | int]:
    return set_timer("idle")


@app.get("/break")
def start_break(
    break_minutes: int = Query(5, ge=1, le=120),
) -> dict[str, Mode | int]:
    state["break_duration"] = minutes_to_seconds(break_minutes)
    return set_timer("break", int(state["break_duration"] or 300))


@app.get("/reset")
def reset() -> dict[str, Mode | int]:
    return set_timer("idle")


@app.get("/status")
def get_status() -> dict[str, Mode | int]:
    return status()
