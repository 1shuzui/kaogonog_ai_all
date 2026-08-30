# 本地开发与运行

## 前置步骤

真实 `.env` 和支付证书已经移出仓库。需要本地运行时，先按 [密钥与本地配置恢复](secrets-and-local-config.md) 复制回原路径。

## 后端

```bash
cd /home/quyu/kaogong_ai/civil-interview-backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8050
```

常用检查：

```bash
cd /home/quyu/kaogong_ai/civil-interview-backend
pytest
python database_setup.py --check
```

后端启动后，进程内接口文档位于 <http://127.0.0.1:8050/docs>，健康检查位于 <http://127.0.0.1:8050/health>。本地 FastAPI 路由直接从根路径开始，例如 <http://127.0.0.1:8050/questions>；生产环境的 `/api` 前缀由网关或客户端 API 基址提供。

题库、套题、评分和定向备面字段的人工可读契约见 [API 契约总览](../api/README.md)。修改文档后可从仓库根目录运行 `.venv/bin/python scripts/validate_project_docs.py`。

## 评分与答案保存

默认把 `LOCAL_REFERENCE_SCORING` 设为 `false`，题库参考答案只注入外部模型提示词，不绕过统一的两阶段点评流程。
这样线上评分口径一致；Redis 命中时仍会复用已有点评缓存，减少重复外部请求。只有离线调试规则评分时，才显式改为
`LOCAL_REFERENCE_SCORING=true`，不要把这个值作为生产默认配置。

前端提交录音转写时应同时传 `questionId` 和 `examId`。后端会在转写成功后立即更新 `ExamAnswer.transcript`，再进入点评阶段；
历史详情接口因此可以在最终分数尚未生成时先展示文字稿，结果页打开带 `examId` 的历史记录时也不会复用其他考试的本地 store 状态。

前期不要为了节省少量调用而把线上点评切回本地规则、减少用户应得的点评内容，或增加额外等待步骤。保持
`LOCAL_REFERENCE_SCORING=false` 和当前外部模型点评体验；成本优化优先使用已有 Redis 评分缓存、避免同一考试重复提交、
复用已保存结果，并先观察真实调用量和延迟。以后只有在不减少反馈质量、不让用户感知额外排队的前提下，再评估提示词压缩、
模型分层或异步预处理。题库参考答案继续作为模型上下文使用，而不是直接替代外部模型点评。

## PC 前端

```bash
cd /home/quyu/kaogong_ai/civil-interview-frontend
npm install
npm run dev
```

构建：

```bash
cd /home/quyu/kaogong_ai/civil-interview-frontend
npm run build
```

## 小程序

```bash
cd /home/quyu/kaogong_ai/civil-interview-miniprogram
npm install
npm run dev:mp-weixin
```

生产构建：

```bash
cd /home/quyu/kaogong_ai/civil-interview-miniprogram
npm run build:mp-weixin:prod
```

## 常见本地问题

- 后端启动报缺少数据库或 Redis 配置：先恢复 `civil-interview-backend/.env`。
- 微信虚拟支付无法调起：确认小程序端 `.env`、后端 `.env`、支付证书和微信现网配置均已恢复。
- FunASR 首次转写慢：模型可能需要下载或读取 `civil-interview-backend/storage/modelscope_cache/`。
- 小程序构建后体积变化：`dist/` 是构建产物，按需重建，不作为源码修改依据。
