#!/usr/bin/env bash
# 这个脚本串起后端编译、前端构建和接口探活；它适合部署前快速确认核心路径没断。
# @param: 无；依赖本地演示服务已按约定端口启动。
# @return: 全部检查通过时返回 0，任一环节失败时返回非零状态。
# @raises: Python 编译、前端构建、curl 探活或 Node 冒烟失败都会中断脚本。
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
