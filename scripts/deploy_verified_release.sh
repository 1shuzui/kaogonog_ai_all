#!/usr/bin/env bash
# Prepare once, then activate backend and web separately using the same release ID.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER="${SERVER:-ubuntu@150.158.87.179}"
SSH_KEY="${SSH_KEY:-/home/quyu/.ssh/civil.pem}"
REMOTE_ROOT=/home/ubuntu/civil
PHASE="${PHASE:-prepare}"
REVISION="$(git -C "$ROOT_DIR" rev-parse HEAD)"
RELEASE_ID="${RELEASE_ID:-${REVISION:0:12}-$(date -u +%Y%m%dT%H%M%SZ)}"
[[ "$RELEASE_ID" =~ ^[a-f0-9]{12}-[0-9]{8}T[0-9]{6}Z$ ]] || { echo 'Invalid release ID' >&2; exit 1; }
SSH=(ssh -o BatchMode=yes -i "$SSH_KEY" "$SERVER")
RSYNC_RSH="ssh -o BatchMode=yes -i $SSH_KEY"

if [[ "$PHASE" == prepare ]]; then
  git -C "$ROOT_DIR" diff --exit-code HEAD -- civil-interview-backend civil-interview-frontend/src civil-interview-miniprogram/src
  STAGE="$(mktemp -d /tmp/kaogong-release.XXXXXX)"
  echo "Local build: $STAGE"
  mkdir -p "$STAGE/source" "$STAGE/backend"
  git -C "$ROOT_DIR" archive HEAD civil-interview-backend ai_gongwu_backend/assets/questions scripts/repair_empty_evidence_scores.py | tar -x -C "$STAGE/source"
  SOURCE="$STAGE/source/civil-interview-backend"
  # Pyarmor trial has a large-module limit. Move only the temporary source copy.
  mv "$SOURCE/app/services/question_service.py" "$STAGE/question_service.py"
  INPUTS=("$SOURCE/main.py" "$SOURCE/app")
  for script in database_setup.py data_loader.py keyword_matcher.py llm_scorer.py post_process.py prompt_builder.py seed.py two_stage_scoring.py; do
    [[ ! -f "$SOURCE/$script" ]] || INPUTS+=("$SOURCE/$script")
  done
  "${PYARMOR:-pyarmor}" gen -O "$STAGE/backend" -r "${INPUTS[@]}"
  cp "$STAGE/question_service.py" "$STAGE/backend/app/services/question_service.py"
  cp "$SOURCE/requirements.txt" "$STAGE/backend/"
  for file in db.json question.json seed_questions.json; do
    [[ ! -f "$SOURCE/$file" ]] || cp "$SOURCE/$file" "$STAGE/backend/"
  done
  (cd "$ROOT_DIR/civil-interview-frontend" && npm run build)
  (cd "$ROOT_DIR/civil-interview-miniprogram" && npm run build:mp-weixin:prod)
  printf '%s\n' "$REVISION" > "$STAGE/REVISION"
  "${SSH[@]}" "test '\$(readlink -f $REMOTE_ROOT/latest/backend)' = '$REMOTE_ROOT/latest/backend' && mkdir -p '$REMOTE_ROOT/releases/$RELEASE_ID' && chmod 700 '$REMOTE_ROOT/releases/$RELEASE_ID'"
  rsync -az -e "$RSYNC_RSH" "$STAGE/backend" "$STAGE/REVISION" "$SERVER:$REMOTE_ROOT/releases/$RELEASE_ID/"
  rsync -az -e "$RSYNC_RSH" "$STAGE/source/ai_gongwu_backend" "$SERVER:$REMOTE_ROOT/releases/$RELEASE_ID/"
  rsync -az -e "$RSYNC_RSH" "$ROOT_DIR/civil-interview-frontend/dist/" "$SERVER:$REMOTE_ROOT/releases/$RELEASE_ID/frontend/"
  rsync -az -e "$RSYNC_RSH" "$ROOT_DIR/civil-interview-miniprogram/dist/build/mp-weixin-prod/" "$SERVER:$REMOTE_ROOT/releases/$RELEASE_ID/miniprogram/"
  rsync -az -e "$RSYNC_RSH" "$STAGE/source/scripts/repair_empty_evidence_scores.py" "$SERVER:$REMOTE_ROOT/releases/$RELEASE_ID/"
  "${SSH[@]}" bash -s -- "$RELEASE_ID" <<'REMOTE'
set -euo pipefail
release="/home/ubuntu/civil/releases/$1"
live=/home/ubuntu/civil/latest/backend
for path in .env .venv uploads storage certs; do
  [[ ! -e "$live/$path" ]] || ln -s "$live/$path" "$release/backend/$path"
done
cd "$release/backend"
.venv/bin/python -c 'import main; from app.core.config import settings; from app.services.exam_access_service import get_owned_exam_or_404; assert settings.local_reference_scoring is False; print("Backend import and external scoring configuration verified")'
REMOTE
  echo "Prepared release: $RELEASE_ID"
elif [[ "$PHASE" == backend || "$PHASE" == web ]]; then
  "${SSH[@]}" bash -s -- "$RELEASE_ID" "$PHASE" <<'REMOTE'
set -euo pipefail
release="/home/ubuntu/civil/releases/$1"
backup="/home/ubuntu/civil/backups/$1"
live=/home/ubuntu/civil/latest
[[ "$(readlink -f "$live/backend")" == /home/ubuntu/civil/latest/backend ]]
[[ "$(readlink -f "$release")" == "/home/ubuntu/civil/releases/$1" ]]
test -s "$release/REVISION"
mkdir -p "$backup"
chmod 700 "$backup"
if [[ "$2" == backend ]]; then
  test ! -e "$backup/backend"
  excludes=(--exclude=.env --exclude=.venv --exclude=uploads --exclude=storage --exclude=certs --exclude=__pycache__ --exclude='*.db*' --exclude='*.sqlite*')
  rsync -a "${excludes[@]}" "$live/backend/" "$backup/backend/"
  cp -p "$live/backend/.env" "$backup/backend.env"
  rollback() {
    echo 'Backend activation failed; restoring previous code' >&2
    rsync -a "${excludes[@]}" "$backup/backend/" "$live/backend/"
    sudo systemctl restart civil-backend
  }
  trap rollback ERR
  sudo systemctl stop civil-backend
  rsync -a "${excludes[@]}" "$release/backend/" "$live/backend/"
  rsync -a "$release/ai_gongwu_backend/" "$live/ai_gongwu_backend/"
  cp "$release/REVISION" "$live/backend/REVISION"
  sudo systemctl start civil-backend
  ready=false
  for attempt in {1..45}; do
    if curl -fsS http://127.0.0.1:8050/health >/dev/null; then ready=true; break; fi
    sleep 1
  done
  "$ready"
  trap - ERR
  echo 'Backend activated and healthy'
else
  test ! -e "$backup/frontend"
  rsync -a "$live/frontend/" "$backup/frontend/"
  rsync -a "$live/miniprogram/mp-weixin-prod/" "$backup/miniprogram/"
  # Keep old hashed chunks for clients with an already-open page; publish index last.
  rsync -a --exclude=index.html "$release/frontend/" "$live/frontend/"
  cp "$release/frontend/index.html" "$live/frontend/index.html"
  rsync -a "$release/miniprogram/" "$live/miniprogram/mp-weixin-prod/"
  cp "$release/REVISION" "$live/frontend/REVISION"
  cp "$release/REVISION" "$live/miniprogram/mp-weixin-prod/REVISION"
  sudo nginx -t
  echo 'Web and miniprogram artifacts activated'
fi
REMOTE
else
  echo 'PHASE must be prepare, backend or web' >&2
  exit 1
fi
