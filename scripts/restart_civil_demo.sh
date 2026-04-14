#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run/civil-demo"
BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"
mkdir -p "$RUN_DIR"
BACKEND_SESSION="civil-demo-backend"
FRONTEND_SESSION="civil-demo-frontend"

resolve_python_bin() {
  local candidate
  for candidate in \
    "$ROOT_DIR/.venv/bin/python" \
    "$ROOT_DIR/civil-interview-backend/.venv/bin/python" \
    "python" \
    "python3"
  do
    if [[ "$candidate" == */* ]]; then
      [[ -x "$candidate" ]] || continue
      if "$candidate" -c "import uvicorn" >/dev/null 2>&1; then
        printf '%s\n' "$candidate"
        return 0
      fi
      continue
    fi

    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import uvicorn" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

wait_for_url() {
  local name="$1"
  local url="$2"
  local log_file="$3"
  local attempts="${4:-30}"
  local i
  for i in $(seq 1 "$attempts"); do
    if curl --noproxy '*' -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "$name failed to start: $url"
  if [[ -f "$log_file" ]]; then
    echo "recent $name log:"
    tail -n 40 "$log_file"
  fi
  return 1
}

PYTHON_BIN="$(resolve_python_bin || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "backend python with uvicorn not found" >"$BACKEND_LOG"
  echo "backend: failed to start  log=$BACKEND_LOG"
  exit 1
fi

"$ROOT_DIR/scripts/stop_civil_demo.sh" >/dev/null 2>&1 || true

if command -v tmux >/dev/null 2>&1; then
  tmux new-session -d -s "$BACKEND_SESSION" \
    "cd \"$ROOT_DIR/civil-interview-backend\" && exec \"$PYTHON_BIN\" -m uvicorn main:app --host 127.0.0.1 --port 8050 >\"$BACKEND_LOG\" 2>&1"
  tmux new-session -d -s "$FRONTEND_SESSION" \
    "cd \"$ROOT_DIR/civil-interview-frontend\" && exec npm run dev -- --host 127.0.0.1 --port 3001 >\"$FRONTEND_LOG\" 2>&1"
  printf '%s\n' "$BACKEND_SESSION" >"$RUN_DIR/backend.session"
  printf '%s\n' "$FRONTEND_SESSION" >"$RUN_DIR/frontend.session"
  rm -f "$RUN_DIR/backend.pid" "$RUN_DIR/frontend.pid"
else
  nohup bash -lc "cd \"$ROOT_DIR/civil-interview-backend\" && exec \"$PYTHON_BIN\" -m uvicorn main:app --host 127.0.0.1 --port 8050" \
    >"$BACKEND_LOG" 2>&1 </dev/null &
  echo $! >"$RUN_DIR/backend.pid"

  nohup bash -lc "cd \"$ROOT_DIR/civil-interview-frontend\" && exec npm run dev -- --host 127.0.0.1 --port 3001" \
    >"$FRONTEND_LOG" 2>&1 </dev/null &
  echo $! >"$RUN_DIR/frontend.pid"
  rm -f "$RUN_DIR/backend.session" "$RUN_DIR/frontend.session"
fi

if ! wait_for_url "backend" "http://127.0.0.1:8050/health" "$BACKEND_LOG" 30; then
  "$ROOT_DIR/scripts/stop_civil_demo.sh" >/dev/null 2>&1 || true
  exit 1
fi

if ! wait_for_url "frontend" "http://127.0.0.1:3001" "$FRONTEND_LOG" 30; then
  "$ROOT_DIR/scripts/stop_civil_demo.sh" >/dev/null 2>&1 || true
  exit 1
fi

echo "backend:  http://127.0.0.1:8050  log=$BACKEND_LOG"
echo "frontend: http://127.0.0.1:3001  log=$FRONTEND_LOG"
