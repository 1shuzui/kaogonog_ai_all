# 公考面试 AI 测评平台

生产地址：https://xzqianmianyuzhoukeji.com  
微信小程序：公考面试AI测评

这是一个面向公考、事业单位、银行、医疗卫生、法检书记员等面试训练场景的双端产品。当前仓库包含后端、PC 前端、小程序、题库资产、回归报告和维护文档。

## 快速入口

| 入口 | 用途 |
| --- | --- |
| `civil-interview-backend/` | FastAPI 后端，负责用户、题库、考试、评分、ASR、支付、权益、反馈。 |
| `civil-interview-frontend/` | PC 管理端和网页端，Vue 3 + Ant Design Vue。 |
| `civil-interview-miniprogram/` | 微信小程序端，uni-app + Vue 3。 |
| `ai_gongwu_backend/` | 题库导入、评分回归和历史评分引擎资产。 |
| `docs/` | 当前项目文档入口，后续 AI 优先从这里读。 |
| `data/question-bank/` | 题库模板、外置源文档索引和校验信息。 |
| `reports/` | 保留的最新测试、抽样和库存报告。 |
| `/home/quyu/doc_kaogong/` | 外置归档目录，不属于 Git 仓库。 |

## 当前技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.10, FastAPI, SQLAlchemy, MySQL, Redis |
| ASR | FunASR Paraformer ONNX + FSMN-VAD + 标点模型 |
| LLM 评分 | DeepSeek/Qwen 兼容 OpenAI SDK 的两阶段评分流程 |
| PC 前端 | Vue 3, Vite, Pinia, Ant Design Vue |
| 小程序 | uni-app, Vue 3, Pinia, 微信小程序虚拟支付 |
| 部署 | Nginx, systemd, rsync, pyarmor 相关脚本 |

## 本地开发

真实 `.env` 和支付证书已迁出仓库。首次启动前按 [密钥与本地配置恢复](docs/ops/secrets-and-local-config.md) 恢复本机配置。

当前评分默认使用外部模型的两阶段点评流程，后端配置应保持 `LOCAL_REFERENCE_SCORING=false`。题库中的
`referenceAnswer`、采分点和关键词会作为模型上下文使用；只有离线调试、明确接受规则评分差异时，才临时设置为
`LOCAL_REFERENCE_SCORING=true`。转写接口在收到 `examId` 时会先保存文字稿，再继续点评，因此点评较慢或暂时失败时，结果页仍可从历史详情回看已保存答案。

```bash
# 后端
cd civil-interview-backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8050

# PC 前端
cd civil-interview-frontend
npm install
npm run dev

# 小程序
cd civil-interview-miniprogram
npm install
npm run dev:mp-weixin
```

## 常用命令

```bash
# PC 构建
cd civil-interview-frontend && npm run build

# 小程序生产构建
cd civil-interview-miniprogram && npm run build:mp-weixin:prod

# 后端测试
cd civil-interview-backend && pytest

# 同步部署
bash scripts/deploy_clean_to_server.sh
DEPLOY_BACKEND=1 bash scripts/deploy_clean_to_server.sh
```

## 文档导航

- [AI 项目知识库入口](docs/ai/README.md)
- [文档总索引](docs/README.md)
- [项目地图](docs/overview/project-map.md)
- [API 契约总览](docs/api/README.md)
- [医疗卫生题库知识库](docs/data/medical-question-bank.md)
- [题库、套题与评分接口](docs/api/question-bank-and-suites.md)
- [题库导入、重建与验收](docs/ops/question-bank-maintenance.md)
- [本地开发与运行](docs/ops/local-development.md)
- [部署与同步手册](docs/ops/deployment-runbook.md)
- [数据库内容与字段说明](docs/data/数据库内容与字段说明.md)
- [题库资产索引](data/question-bank/README.md)
- [测试与报告说明](docs/testing/testing-and-reports.md)
- [外部归档索引](docs/ops/archive-index.md)

## 文件整理约定

- 题库原始 Word/doc、抽取文本和 normalized 文本不再放在 Git 中，统一归档到 `/home/quyu/doc_kaogong/question-bank/`。
- 真实 `.env`、支付证书、私钥、公钥、数据库备份统一归档到 `/home/quyu/doc_kaogong/doc_secret/`。
- 旧报告只保留必要最新结果，其余归档到 `/home/quyu/doc_kaogong/reports/archive/`。
- `.venv`、`node_modules`、`dist`、FunASR 模型缓存等可重建或运行缓存暂不移动，只在清理候选文档中记录。
