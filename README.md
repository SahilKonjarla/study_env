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
- `POST /agent/heartbeat` records that the macOS agent is alive
- `GET /agent/status` returns agent connectivity state

When focus expires, the backend switches to break automatically. When break expires, the backend returns to idle automatically.

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

Emergency cleanup without polling:

```bash
sudo python3 agent.py --cleanup
```

Focus mode:

- Best-effort macOS `Work` Focus enable
- Kills Discord
- Blocks `youtube.com`, `netflix.com`, and `hulu.com` through a managed `/etc/hosts` block

Idle, pause, reset, and break:

- Best-effort macOS `Work` Focus disable
- Removes all managed `/etc/hosts` entries immediately
- Flushes the macOS DNS cache after hosts changes

macOS Focus automation differs by macOS version. This project uses your Focus named `Work`. Create Shortcuts named exactly `Pomodoro Work Focus On` and `Pomodoro Work Focus Off`.

Open the setup pages:

```bash
scripts/setup_focus_shortcuts.sh
```

Create:

- `Pomodoro Work Focus On`: use Apple's `Set Focus` action to turn on `Work` until turned off
- `Pomodoro Work Focus Off`: use Apple's `Set Focus` action to turn off `Work`

Verify:

```bash
/usr/bin/python3 agent.py --check-shortcuts
```

If you already have different Shortcut names:

```bash
POMODORO_FOCUS_ON_SHORTCUT="Your On Shortcut" POMODORO_FOCUS_OFF_SHORTCUT="Your Off Shortcut" sudo -E python3 agent.py
```

If your Focus is not named `Work`, set `POMODORO_FOCUS_NAME` for clearer logs and point the shortcuts at the Focus you want.

The agent always attempts cleanup on `Ctrl+C`:

- disables the `Work` Focus best-effort
- removes the managed `/etc/hosts` block

It can also clean up stale restrictions on startup.

The agent sends a heartbeat to the backend each poll cycle. The frontend uses this to show whether enforcement is connected.

## Frontend

```bash
cd frontend
npm install
VITE_API_BASE_URL=http://PI_IP_ADDRESS:8000 npm run dev
```

Open the Vite URL printed by `npm run dev`.

Set focus minutes and break minutes in the UI before pressing Start. When focus time reaches zero, the backend switches to break automatically. The agent sees `mode="break"` on its next poll and removes all restrictions.

The UI also shows whether the macOS agent is connected. Use `Remove Restrictions` for an explicit reset/cleanup request.

If `VITE_API_BASE_URL` is not set, the frontend defaults to `http://127.0.0.1:8000`.

## One-Command Local Run

For local testing on your Mac, after dependencies are installed:

```bash
scripts/run_local.sh
```

This starts:

- FastAPI backend on `http://127.0.0.1:8000`
- React frontend on `http://localhost:5173`
- macOS agent with `sudo`

Press `Ctrl+C` in that terminal to:

- call `/reset`
- remove restrictions through the agent shutdown cleanup
- stop the frontend
- stop the backend

## One-Command Mac Run With Pi Backend

Start the backend on the Raspberry Pi first:

```bash
cd /path/to/study_env
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then on your Mac:

```bash
POMODORO_BACKEND_URL=http://PI_IP_ADDRESS:8000 scripts/run_mac_for_pi.sh
```

This starts the frontend and macOS agent from one terminal. Press `Ctrl+C` in that terminal to call `/reset`, stop the frontend, and let the agent remove restrictions.

Starting the Pi backend from the Mac can also be automated, but it needs your Pi SSH username, hostname/IP, project path, and authentication setup.

## Tests

Run:

```bash
python3 -m unittest discover -s tests
```
