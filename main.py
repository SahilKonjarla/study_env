import logging
import time
from typing import Any
from typing import Dict
from typing import Literal

from fastapi import FastAPI, Query, Request
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
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

state: Dict[str, Any] = {
    "mode": "idle",
    "start_time": None,
    "duration": 0,
    "focus_duration": 1500,
    "break_duration": 300,
    "repeat_enabled": False,
    "cycle_count": 0,
    "agent_last_seen": None,
    "agent_name": None,
    "agent_closed_apps": [],
    "agent_reopened_apps": [],
}


def minutes_to_seconds(minutes: int) -> int:
    return minutes * 60


def set_timer(mode: Mode, duration: int = 0) -> Dict[str, Any]:
    previous_mode = state["mode"]
    state["mode"] = mode
    state["duration"] = duration
    state["start_time"] = time.time() if mode != "idle" else None
    logger.info("timer state change previous=%s current=%s duration=%s", previous_mode, mode, duration)
    return status()


def start_break_timer() -> None:
    state["mode"] = "break"
    state["duration"] = int(state["break_duration"] or 300)
    state["start_time"] = time.time()
    logger.info("focus complete; auto-starting break duration=%s", state["duration"])


def restart_focus_timer() -> None:
    state["mode"] = "focus"
    state["duration"] = int(state["focus_duration"] or 1500)
    state["start_time"] = time.time()
    state["cycle_count"] = int(state["cycle_count"] or 0) + 1
    logger.info(
        "break complete; repeat enabled; auto-starting focus duration=%s cycle_count=%s",
        state["duration"],
        state["cycle_count"],
    )


def finish_break_timer() -> None:
    state["mode"] = "idle"
    state["duration"] = 0
    state["start_time"] = None
    state["repeat_enabled"] = False
    logger.info("break complete; returning to idle")


def status() -> Dict[str, Any]:
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
        elif mode == "break" and remaining_time == 0:
            if state["repeat_enabled"]:
                restart_focus_timer()
            else:
                finish_break_timer()
            mode = state["mode"]
            duration = int(state["duration"] or 0)
            remaining_time = duration if mode != "idle" else 0

    return {
        "mode": mode,
        "remaining_time": remaining_time,
        "focus_duration": int(state["focus_duration"] or 1500),
        "break_duration": int(state["break_duration"] or 300),
        "repeat_enabled": bool(state["repeat_enabled"]),
        "cycle_count": int(state["cycle_count"] or 0),
    }


@app.get("/start")
def start(
    focus_minutes: int = Query(25, ge=1, le=240),
    break_minutes: int = Query(5, ge=1, le=120),
    repeat: bool = Query(False),
) -> Dict[str, Any]:
    state["focus_duration"] = minutes_to_seconds(focus_minutes)
    state["break_duration"] = minutes_to_seconds(break_minutes)
    state["repeat_enabled"] = repeat
    state["cycle_count"] = 1
    return set_timer("focus", int(state["focus_duration"] or 1500))


@app.get("/pause")
def pause() -> Dict[str, Any]:
    state["repeat_enabled"] = False
    return set_timer("idle")


@app.get("/break")
def start_break(
    break_minutes: int = Query(5, ge=1, le=120),
) -> Dict[str, Any]:
    state["repeat_enabled"] = False
    state["break_duration"] = minutes_to_seconds(break_minutes)
    return set_timer("break", int(state["break_duration"] or 300))


@app.get("/reset")
def reset() -> Dict[str, Any]:
    state["repeat_enabled"] = False
    state["cycle_count"] = 0
    return set_timer("idle")


@app.get("/status")
def get_status() -> Dict[str, Any]:
    return status()


@app.post("/agent/heartbeat")
async def agent_heartbeat(request: Request) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    state["agent_last_seen"] = time.time()
    state["agent_name"] = payload.get("name") or "mac-agent"
    state["agent_closed_apps"] = payload.get("closed_apps") or []
    state["agent_reopened_apps"] = payload.get("reopened_apps") or []
    logger.info(
        "agent heartbeat name=%s closed_apps=%s reopened_apps=%s",
        state["agent_name"],
        state["agent_closed_apps"],
        state["agent_reopened_apps"],
    )
    return {"ok": "true", "last_seen": state["agent_last_seen"]}


@app.get("/agent/status")
def get_agent_status() -> Dict[str, Any]:
    last_seen = state["agent_last_seen"]
    seconds_since_seen = None
    online = False

    if last_seen is not None:
        seconds_since_seen = int(time.time() - float(last_seen))
        online = seconds_since_seen <= 15

    return {
        "online": online,
        "last_seen": last_seen,
        "seconds_since_seen": seconds_since_seen,
        "agent_name": state["agent_name"],
        "closed_apps": state["agent_closed_apps"],
        "reopened_apps": state["agent_reopened_apps"],
    }
