# kaogong_ai

`kaogong_ai` 是一个面向公务员面试练习与 AI 测评的同仓工程，当前包含三套可协同使用的子系统：

- `civil-interview-frontend`：Vue 3 + Vite 前端，覆盖登录、题库、练习、成绩页、历史分析、定向备面、专项训练等页面。
- `civil-interview-backend`：平台业务后端，对前端提供统一 API，负责鉴权、题库管理、考试会话、历史记录、订阅/试用/支付 mock 等能力。
- `ai_gongwu_backend`：独立评分引擎，负责题库加载、文本/音视频解析、两阶段评分、规则校验、评分记录落库与回归验证。

## 仓库结构

| 目录 | 角色 | 默认端口 | 说明 |
| --- | --- | --- | --- |
| `civil-interview-frontend/` | 前端应用 | `3001` | Vite 开发服务，默认将 `/api` 代理到 `8050` |
| `civil-interview-backend/` | 业务后端 | `8050` | 当前平台主入口，文件入口是 `main.py` |
| `ai_gongwu_backend/` | 评分引擎 | `9000` | 独立 FastAPI 服务，适合调试评分链路与回归 |
| `sample_sets/` | 样本答案 | - | 高分/中低分文本样本，供评分标定和人工对照 |
| `reports/` | 报表输出 | - | 回归报告、题库盘点等脚本输出目录 |
| `docs/` | 工程文档 | - | 联调说明、改造记录等补充资料 |
| `scripts/` | 仓库级脚本 | - | 一键启动、烟雾测试、题库盘点等工具 |

## 当前架构

推荐把项目理解成两条使用路径：

1. 产品演示链路  
   `civil-interview-frontend` -> `civil-interview-backend`  
   这是当前最完整的交互式体验路径，前端页面和业务接口都走这条链路。

2. 评分引擎链路  
   `ai_gongwu_backend`  
   这是更适合开发和回归的独立评分服务，暴露题库、纯文本/音视频评分、评分记录查询接口。

有一个实现细节需要特别注意：

- `civil-interview-backend/main.py` 是当前有效入口。
- `civil-interview-backend/main_old.py` 保留为历史参考，不是当前运行入口。
- `civil-interview-backend` 启动时会把 `ai_gongwu_backend/assets/questions/` 下的题目同步到自己的数据库，用于前端题库与练习流程。

## 核心能力

- 多模态评分：支持文本、音频、视频输入。
- 两阶段评分：先抽取证据，再基于证据评分，降低模型直接打分时的漂移。
- 规则兜底：当模型不可用或输出异常时，评分引擎会进行确定性校验和保守回退。
- 题库管理：支持内置真题、导入题、AI 生成题、自定义题。
- 前端业务能力：包含登录、考试会话、成绩页、历史趋势、定向备面、专项训练、试用与订阅状态。
- 回归验证：内置文本样本、批量回归脚本和题库盘点脚本。

## 快速开始

### 环境要求

- Python `3.10+`
- Node.js `18+`
- npm `9+`
- `ffmpeg`：音视频转写与格式归一化需要
- `tmux`：可选；仅用于一键启动脚本

### 1. 安装依赖

建议在仓库根目录准备一个共用虚拟环境：

```bash
cd /home/quyu/kaogong_ai
python3 -m venv .venv
source .venv/bin/activate
pip install -r civil-interview-backend/requirements.txt
pip install -r ai_gongwu_backend/requirements.txt

cd civil-interview-frontend
npm install
cd ..
```

### 2. 配置环境变量

业务后端可以直接从模板开始：

```bash
cp civil-interview-backend/.env_example civil-interview-backend/.env
```

评分引擎没有现成模板，至少建议创建一个最小配置：

```env
# ai_gongwu_backend/.env
LLM_API_KEY=YOUR_API_KEY
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen3-coder-plus
DATABASE_URL=sqlite:///storage/ai_gongwu.db
WHISPER_MODEL_SIZE=base
```

说明：

- `civil-interview-backend/.env` 主要控制数据库、JWT、支付 mock 等业务配置。
- `ai_gongwu_backend/.env` 主要控制评分引擎模型、ASR 和引擎数据库。
- 前端默认使用 `civil-interview-frontend/.env.development`，`VITE_API_BASE=/api`，开发态会代理到 `http://localhost:8050`。

### 3. 启动完整演示链路

最省事的方式是直接用仓库脚本启动前端和业务后端：

```bash
bash scripts/restart_civil_demo.sh
```

启动成功后可访问：

- 前端：`http://127.0.0.1:3001`
- 业务后端 Swagger：`http://127.0.0.1:8050/docs`
- 健康检查：`http://127.0.0.1:8050/health`

默认种子账号：

- 用户名：`admin`
- 密码：`admin123`

停止服务：

```bash
bash scripts/stop_civil_demo.sh
```

### 4. 手动启动

如果你想分别调试每个服务：

```bash
source .venv/bin/activate

cd civil-interview-backend
python -m uvicorn main:app --host 127.0.0.1 --port 8050 --reload
```

```bash
cd civil-interview-frontend
npm run dev -- --host 127.0.0.1 --port 3001
```

独立评分引擎：

```bash
cd ai_gongwu_backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload
```

评分引擎启动后可访问：

- Swagger：`http://127.0.0.1:9000/docs`
- 健康检查：`http://127.0.0.1:9000/health`

## 评分引擎链路

`ai_gongwu_backend` 的主流程在 `app/services/flow.py`，可概括为：

1. 根据 `question_id` 从 `assets/questions/` 加载题目定义。
2. 对文本、音频或视频进行转写/提取。
3. 第一阶段让模型抽取可核验证据。
4. 第二阶段只基于证据进行评分。
5. 通过 `app/services/scoring/calculator.py` 做分数收敛、证据校验、异常修正。
6. 将结果写入 `storage/ai_gongwu.db`，并提供记录查询接口。

主要接口：

| 服务 | 路径 | 说明 |
| --- | --- | --- |
| `ai_gongwu_backend` | `GET /api/v1/interview/questions` | 查看题目摘要 |
| `ai_gongwu_backend` | `GET /api/v1/interview/questions/{question_id}` | 查看题目详情 |
| `ai_gongwu_backend` | `POST /api/v1/interview/evaluate` | 音视频评分 |
| `ai_gongwu_backend` | `POST /api/v1/interview/evaluate/text` | 纯文本评分 |
| `ai_gongwu_backend` | `GET /api/v1/interview/records` | 最近评分记录 |
| `ai_gongwu_backend` | `GET /api/v1/interview/records/{record_id}` | 单条评分详情 |

## 业务后端链路

`civil-interview-backend` 面向前端页面，当前 API 大致分为：

- 鉴权：`/token`、`/register`
- 用户：`/user/*`
- 题库：`/questions/*`
- 考试会话：`/exam/*`
- 评分：`/scoring/*`
- 历史分析：`/history/*`
- 定向备面与专项训练：`/targeted/*`、相关训练生成接口
- 订阅/试用/支付：`/subscription/*`、`/trial/*`、`/payment/*`

前端开发时，`civil-interview-frontend/vite.config.js` 会将：

- `/api` 代理到 `http://localhost:8050`
- `/uploads` 代理到 `http://localhost:8050`

## 常用开发命令

| 命令 | 说明 |
| --- | --- |
| `bash scripts/restart_civil_demo.sh` | 一键启动前端和业务后端 |
| `bash scripts/stop_civil_demo.sh` | 停止一键启动的服务 |
| `bash scripts/smoke_civil_demo.sh` | 运行前端构建 + 后端健康检查 + 端到端烟雾测试 |
| `python -m unittest discover ai_gongwu_backend/tests` | 运行评分引擎单测 |
| `python -m unittest discover civil-interview-backend/tests` | 运行业务后端单测 |
| `python ai_gongwu_backend/scripts/run_regression.py` | 运行确定性文本回归 |
| `python ai_gongwu_backend/scripts/run_llm_regression.py --quiet` | 运行真实模型回归 |
| `python scripts/export_question_answer_inventory.py` | 导出题库/答案资产盘点报告 |
| `npx gitnexus analyze` | 刷新 GitNexus 索引 |

## 数据与资产

- 评分引擎题库：`ai_gongwu_backend/assets/questions/`
- 评分引擎数据库：`ai_gongwu_backend/storage/ai_gongwu.db`
- 业务后端数据库：`civil-interview-backend/civil_interview.db`
- 上传文件：`civil-interview-backend/uploads/`
- 回归报告：`reports/regression/`
- 示例答题样本：`sample_sets/`

`sample_sets/` 当前已经按三类整理：

- `通用高分`
- `河南省直高分`
- `非高分参考`

这批样本既可以用于人工对照，也可以作为回归脚本的语料来源。

## 推荐阅读顺序

如果你第一次接手这个仓库，建议按下面顺序阅读：

1. [docs/kaogong_ai工程联调与改造说明.md](/home/quyu/kaogong_ai/docs/kaogong_ai工程联调与改造说明.md)
2. [civil-interview-backend/main.py](/home/quyu/kaogong_ai/civil-interview-backend/main.py)
3. [civil-interview-backend/app/api/v1](/home/quyu/kaogong_ai/civil-interview-backend/app/api/v1)
4. [ai_gongwu_backend/app/main.py](/home/quyu/kaogong_ai/ai_gongwu_backend/app/main.py)
5. [ai_gongwu_backend/app/services/flow.py](/home/quyu/kaogong_ai/ai_gongwu_backend/app/services/flow.py)
6. [ai_gongwu_backend/app/services/scoring/calculator.py](/home/quyu/kaogong_ai/ai_gongwu_backend/app/services/scoring/calculator.py)

## 注意事项

- 如果没有配置真实大模型，评分相关能力可能会进入保守回退或占位输出，不适合直接拿来做模型效果评估。
- 音视频链路依赖 `ffmpeg`；缺少它时，ASR 和媒体归一化会失败。
- `civil-interview-backend` 与 `ai_gongwu_backend` 各自读取自己目录下的 `.env`，不要只改根目录环境变量。
- `reports/`、数据库文件、`uploads/`、运行日志属于运行产物，不建议手工混入源码变更。

