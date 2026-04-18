#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"

"$PYTHON_BIN" "$ROOT/agent.py" --open-shortcuts

cat <<'EOF'

Create these two macOS Shortcuts:

1. Pomodoro Work Focus On
   - Add action: Set Focus
   - Choose: Work
   - Set it to turn on until turned off

2. Pomodoro Work Focus Off
   - Add action: Set Focus
   - Choose: Work
   - Set it to turn off

Then verify:

  /usr/bin/python3 agent.py --check-shortcuts

If you use different shortcut names, run the agent with:

  POMODORO_FOCUS_ON_SHORTCUT="Your On Name" POMODORO_FOCUS_OFF_SHORTCUT="Your Off Name" ...

EOF
