#!/usr/bin/env bash
# 这个脚本停止本地演示环境；它同时处理 tmux 会话和 pid 文件，避免端口被残留进程占住。
# @param: 无；脚本使用固定会话名和运行目录。
# @return: 清理本地演示进程、会话标记和残留 pid 文件。
# @raises: 该脚本尽量容错；严重 shell 错误仍会因 set -euo pipefail 终止。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run/civil-demo"
BACKEND_SESSION="civil-demo-backend"
FRONTEND_SESSION="civil-demo-frontend"

stop_process() {
  local name="$1"
  local pid_file="$2"
  if [[ ! -f "$pid_file" ]]; then
    return
  fi

  local pid
  pid="$(cat "$pid_file")"
  if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    sleep 1
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
    echo "stopped $name ($pid)"
  fi
  rm -f "$pid_file"
}

stop_tmux_session() {
  local name="$1"
  local session_name="$2"
  if ! command -v tmux >/dev/null 2>&1; then
    return
  fi

  if tmux has-session -t "$session_name" >/dev/null 2>&1; then
    tmux kill-session -t "$session_name" >/dev/null 2>&1 || true
    echo "stopped $name (tmux:$session_name)"
  fi
}

mkdir -p "$RUN_DIR"
stop_tmux_session "backend" "$BACKEND_SESSION"
stop_tmux_session "frontend" "$FRONTEND_SESSION"
stop_process "backend" "$RUN_DIR/backend.pid"
stop_process "frontend" "$RUN_DIR/frontend.pid"
rm -f "$RUN_DIR/backend.session" "$RUN_DIR/frontend.session"

pkill -f "uvicorn main:app --host 127.0.0.1 --port 8050" >/dev/null 2>&1 || true
pkill -f "vite --host 127.0.0.1 --port 3001" >/dev/null 2>&1 || true
