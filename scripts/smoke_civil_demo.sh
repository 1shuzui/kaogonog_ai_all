#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python -m py_compile \
  "$ROOT_DIR/civil-interview-backend/app/services/question_service.py" \
  "$ROOT_DIR/civil-interview-backend/app/services/scoring_service.py" \
  "$ROOT_DIR/civil-interview-backend/app/api/v1/routes/targeted_routes.py" \
  "$ROOT_DIR/civil-interview-backend/main.py"

(cd "$ROOT_DIR/civil-interview-frontend" && npm run build >/dev/null)

curl --noproxy '*' -fsS "http://127.0.0.1:8050/health" >/dev/null
curl --noproxy '*' -fsS "http://127.0.0.1:3001" >/dev/null

node "$ROOT_DIR/scripts/smoke_civil_demo.js"
