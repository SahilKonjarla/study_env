# Pomodoro Control System

Minimal three-part Pomodoro control system:

- FastAPI backend for the Raspberry Pi
- macOS polling agent for local system controls
- React frontend for local browser control

## Backend on Raspberry Pi

Install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Endpoints:

- `GET /start` starts a focus session and then automatically starts break when focus expires
- `GET /start?focus_minutes=50&break_minutes=10` starts a 50 minute focus session followed by a 10 minute break
- `GET /pause` returns to idle and triggers cleanup through the agent
- `GET /break` starts a 5 minute break and triggers cleanup through the agent
- `GET /break?break_minutes=10` starts a 10 minute break
- `GET /reset` returns to idle and triggers cleanup through the agent
- `GET /status` returns `{ "mode": "...", "remaining_time": 0, "focus_duration": 1500, "break_duration": 300 }`

State is in memory only. Restarting the backend resets it.

## macOS Agent

Run this on the Mac. It needs `sudo` because it safely edits only its managed block in `/etc/hosts`.

```bash
sudo POMODORO_BACKEND_URL=http://PI_IP_ADDRESS:8000 python3 agent.py
```

Optional poll interval:

```bash
sudo POMODORO_BACKEND_URL=http://PI_IP_ADDRESS:8000 POMODORO_POLL_SECONDS=3 python3 agent.py
```

Focus mode:

- Best-effort Do Not Disturb enable
- Kills Discord
- Blocks `youtube.com`, `netflix.com`, and `hulu.com` through a managed `/etc/hosts` block

Idle, pause, reset, and break:

- Best-effort Do Not Disturb disable
- Removes all managed `/etc/hosts` entries immediately

Do Not Disturb automation differs by macOS version. For best results, create Shortcuts named exactly `Turn On Do Not Disturb` and `Turn Off Do Not Disturb`; the agent also tries the older `defaults` fallback.

## Frontend

```bash
cd frontend
npm install
VITE_API_BASE_URL=http://PI_IP_ADDRESS:8000 npm run dev
```

Open the Vite URL printed by `npm run dev`.

Set focus minutes and break minutes in the UI before pressing Start. When focus time reaches zero, the backend switches to break automatically. The agent sees `mode="break"` on its next poll and removes all restrictions.

If `VITE_API_BASE_URL` is not set, the frontend defaults to `http://127.0.0.1:8000`.
