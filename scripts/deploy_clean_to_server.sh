#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/civil.pem}"
SERVER="${SERVER:-ubuntu@150.158.87.179}"
REMOTE_ROOT="${REMOTE_ROOT:-/home/ubuntu/civil}"
REMOTE_LATEST="$REMOTE_ROOT/latest"

SSH_OPTS=(-i "$SSH_KEY")
RSYNC_RSH="ssh -i $SSH_KEY"

copy_if_exists() {
  local src="$1"
  local dst="$2"
  if [[ -f "$src" ]]; then
    cp "$src" "$dst"
  fi
}

build_backend_artifact() {
  local artifact_dir="$1"
  local backend_dir="$ROOT_DIR/civil-interview-backend"
  local obf_dir

  if ! command -v pyarmor >/dev/null 2>&1; then
    echo "Missing pyarmor. Install it before deploying the encrypted backend artifact." >&2
    exit 1
  fi

  obf_dir="$(mktemp -d)"
  rm -rf "$artifact_dir"
  mkdir -p "$artifact_dir"

  local pyarmor_inputs=(
    "$backend_dir/main.py"
    "$backend_dir/app"
  )
  local optional_script
  for optional_script in \
    database_setup.py \
    data_loader.py \
    keyword_matcher.py \
    llm_scorer.py \
    post_process.py \
    prompt_builder.py \
    seed.py \
    two_stage_scoring.py
  do
    if [[ -f "$backend_dir/$optional_script" ]]; then
      pyarmor_inputs+=("$backend_dir/$optional_script")
    fi
  done

  pyarmor gen -O "$obf_dir" -r "${pyarmor_inputs[@]}"

  rsync -a "$obf_dir/" "$artifact_dir/"
  rm -rf "$obf_dir"

  cp "$backend_dir/requirements.txt" "$artifact_dir/requirements.txt"
  copy_if_exists "$backend_dir/db.json" "$artifact_dir/db.json"
  copy_if_exists "$backend_dir/question.json" "$artifact_dir/question.json"
  copy_if_exists "$backend_dir/seed_questions.json" "$artifact_dir/seed_questions.json"
  copy_if_exists "$backend_dir/.env_example" "$artifact_dir/.env_example"

  mkdir -p "$artifact_dir/certs"
  copy_if_exists "$backend_dir/certs/apiclient_cert.p12" "$artifact_dir/certs/apiclient_cert.p12"
  copy_if_exists "$backend_dir/certs/apiclient_cert.pem" "$artifact_dir/certs/apiclient_cert.pem"
  copy_if_exists "$backend_dir/certs/apiclient_key.pem" "$artifact_dir/certs/apiclient_key.pem"
  copy_if_exists "$backend_dir/certs/wechatpay_public_key.pem" "$artifact_dir/certs/wechatpay_public_key.pem"

  find "$artifact_dir" -type d -name '__pycache__' -prune -exec rm -rf {} +
  find "$artifact_dir" -type f \( -name '*.db' -o -name '*.db-shm' -o -name '*.db-wal' -o -name '*.sqlite' -o -name '*.sqlite3' \) -delete
}

cd "$ROOT_DIR/civil-interview-frontend"
npm run build

cd "$ROOT_DIR/civil-interview-miniprogram"
npm run build:mp-weixin:prod

ssh "${SSH_OPTS[@]}" "$SERVER" "mkdir -p '$REMOTE_LATEST/frontend' '$REMOTE_LATEST/miniprogram/mp-weixin-prod'"

rsync -az --delete -e "$RSYNC_RSH" \
  "$ROOT_DIR/civil-interview-frontend/dist/" \
  "$SERVER:$REMOTE_LATEST/frontend/"

rsync -az --delete -e "$RSYNC_RSH" \
  "$ROOT_DIR/civil-interview-miniprogram/dist/build/mp-weixin/" \
  "$SERVER:$REMOTE_LATEST/miniprogram/mp-weixin-prod/"

if [[ "${DEPLOY_BACKEND:-0}" == "1" ]]; then
  LOCAL_BACKEND_ARTIFACT="${LOCAL_BACKEND_ARTIFACT:-}"
  if [[ -z "$LOCAL_BACKEND_ARTIFACT" ]]; then
    LOCAL_BACKEND_ARTIFACT="${BACKEND_ARTIFACT_DIR:-/home/quyu/civil/backend}"
    build_backend_artifact "$LOCAL_BACKEND_ARTIFACT"
  fi

  if [[ ! -d "$LOCAL_BACKEND_ARTIFACT" ]]; then
    echo "Missing backend artifact directory: $LOCAL_BACKEND_ARTIFACT" >&2
    exit 1
  fi

  ssh "${SSH_OPTS[@]}" "$SERVER" "mkdir -p '$REMOTE_LATEST/backend'"
  rsync -az --delete -e "$RSYNC_RSH" \
    --exclude='.env' \
    --exclude='.venv/' \
    --exclude='uploads/' \
    --exclude='storage/' \
    "$LOCAL_BACKEND_ARTIFACT/" \
    "$SERVER:$REMOTE_LATEST/backend/"

  ssh "${SSH_OPTS[@]}" "$SERVER" "cd '$REMOTE_LATEST/backend' && if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi && .venv/bin/python -m pip install -r requirements.txt"

  ssh "${SSH_OPTS[@]}" "$SERVER" "mkdir -p '$REMOTE_LATEST/ai_gongwu_backend/assets/questions'"
  rsync -az --delete -e "$RSYNC_RSH" \
    "$ROOT_DIR/ai_gongwu_backend/assets/questions/" \
    "$SERVER:$REMOTE_LATEST/ai_gongwu_backend/assets/questions/"

  ssh "${SSH_OPTS[@]}" "$SERVER" "python3 - <<'PY'
from pathlib import Path
import secrets

env_path = Path('$REMOTE_LATEST/backend/.env')
updates = {
    'ALLOWED_ORIGINS': 'https://xzqianmianyuzhoukeji.com',
    'PASSWORD_RESET_CODE_DEBUG_RESPONSE': 'false',
    'PRODUCTION_REQUIRE_SECURE_CONFIG': 'true',
    'REDIS_URL': 'redis://:4Wv79nd4v3%21@127.0.0.1:6379/0',
    'WECHAT_PAY_ENABLED': 'true',
}
lines = env_path.read_text().splitlines() if env_path.exists() else []
values = {}
for line in lines:
    if '=' in line and not line.lstrip().startswith('#'):
        key, value = line.split('=', 1)
        values[key] = value
if values.get('SECRET_KEY', '').strip() in {'', 'civil-demo-secret'}:
    updates['SECRET_KEY'] = secrets.token_urlsafe(48)
seen = set()
next_lines = []
for line in lines:
    key = line.split('=', 1)[0] if '=' in line and not line.lstrip().startswith('#') else ''
    if key in updates:
        next_lines.append(f'{key}={updates[key]}')
        seen.add(key)
    else:
        next_lines.append(line)
for key, value in updates.items():
    if key not in seen:
        next_lines.append(f'{key}={value}')
env_path.write_text('\\n'.join(next_lines) + '\\n')
PY"

  ssh "${SSH_OPTS[@]}" "$SERVER" "sudo mkdir -p /etc/systemd/system/civil-backend.service.d && printf '%s\n' '[Service]' 'ExecStart=' 'ExecStart=/home/ubuntu/civil/latest/backend/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8050' | sudo tee /etc/systemd/system/civil-backend.service.d/override.conf >/dev/null && sudo systemctl daemon-reload"
  ssh "${SSH_OPTS[@]}" "$SERVER" "sudo ufw allow 22/tcp >/dev/null && sudo ufw allow 80/tcp >/dev/null && sudo ufw allow 443/tcp >/dev/null && (sudo ufw delete allow 8050/tcp >/dev/null 2>&1 || true) && sudo ufw deny 8050/tcp >/dev/null && sudo ufw --force enable >/dev/null"
  ssh "${SSH_OPTS[@]}" "$SERVER" "sudo systemctl restart civil-backend"
fi

ssh "${SSH_OPTS[@]}" "$SERVER" "rm -rf \
  '$REMOTE_ROOT'/.git \
  '$REMOTE_ROOT'/.latest_release_path \
  '$REMOTE_ROOT'/CONFIG_DECRYPTION_KEY_* \
  '$REMOTE_ROOT'/civil_release_* \
  '$REMOTE_ROOT'/frontend \
  '$REMOTE_ROOT'/miniprogram \
  '$REMOTE_LATEST'/OPS_MANUAL.md \
  '$REMOTE_LATEST'/README_DEPLOY.md \
  '$REMOTE_LATEST'/操作手册_部署运维_MySQL_ONLY.md \
  '$REMOTE_LATEST'/config \
  '$REMOTE_LATEST'/data \
  '$REMOTE_LATEST'/frontend_h5 \
  '$REMOTE_LATEST'/logs \
  '$REMOTE_LATEST'/scripts \
  '$REMOTE_LATEST'/miniprogram/README_MINI.md \
  '$REMOTE_LATEST'/miniprogram/mp-weixin \
  '$REMOTE_LATEST'/miniprogram/mp-weixin-dev \
  '$REMOTE_LATEST'/backend/.env.bak.* \
  '$REMOTE_LATEST'/backend/.env.enc \
  '$REMOTE_LATEST'/backend/.env_example \
  '$REMOTE_LATEST'/backend/__pycache__ \
  '$REMOTE_LATEST'/backend/app/__pycache__"

ssh "${SSH_OPTS[@]}" "$SERVER" "if grep -Eq '^DATABASE_URL=(mysql|mysql\\+)' '$REMOTE_LATEST/backend/.env'; then rm -f '$REMOTE_LATEST/backend/'*.db; fi"

ssh "${SSH_OPTS[@]}" "$SERVER" "sudo nginx -t && for i in {1..90}; do curl -fsS http://127.0.0.1:8050/health >/dev/null 2>&1 && exit 0; sleep 1; done; curl -fsS http://127.0.0.1:8050/health >/dev/null"
ssh "${SSH_OPTS[@]}" "$SERVER" "ss -ltn | grep -q '127.0.0.1:8050' && ! ss -ltn | grep -Eq '0\\.0\\.0\\.0:8050|\\[::\\]:8050'"
if timeout 3 bash -c '</dev/tcp/150.158.87.179/8050' 2>/dev/null; then
  echo "Public 8050 is reachable; expected it to be blocked." >&2
  exit 1
fi
for i in {1..20}; do
  curl -fsS https://xzqianmianyuzhoukeji.com/api/health >/dev/null 2>&1 && break
  sleep 1
  if [[ "$i" == "20" ]]; then
    curl -fsS https://xzqianmianyuzhoukeji.com/api/health >/dev/null
  fi
done

echo "Clean deploy finished."
