# AI 公考面试测评项目说明

## 1. 项目简介

这是一个面向“公考面试作答评估”场景的后端项目，核心目标是：

1. 接收考生提交的文本、音频或视频作答。
2. 将媒体内容转换为可分析的文字 transcript。
3. 结合题库、评分标准和关键词信息，调用大模型进行结构化评分。
4. 对大模型输出做二次校验，尽量降低格式错误、总分不一致、引用原文不真实等问题。

当前代码主体位于 [ai_gongwu_backend](/home/quyu/ai_interview/ai_gongwu_backend) 目录中。

项目中根目录下的若干 `.txt` 文件，可以理解为不同质量的答题样例文本，适合你后续用来做对比测试。

## 2. 这个项目现在能做什么

当前后端具备以下能力：

1. 提供 FastAPI 接口，支持 Swagger 在线调试。
2. 支持文本、音频、视频三种输入路径。
3. 音频/视频可通过 Whisper 做语音转写。
4. 视频可做一个轻量的人脸稳定性观察。
5. 评分前会根据题目构造 Prompt。
6. 评分后会对模型结果进行后处理，修正明显异常。
7. 返回统一结构的评分结果，便于前端展示和后续扩展。

## 3. 为什么这次要做重构和补注释

你原来的项目已经有基本雏形，但存在几个常见问题：

1. `question_id` 传入了接口，但没有真正参与选题。
2. 视频视觉描述和考生原文混在一起，容易污染大模型判断。
3. 大模型输出缺少强校验，容易出现：
   - 维度名写错
   - 总分与分项分不一致
   - 模型“脑补”考生原话
4. 依赖注入、配置管理、路径解析还不够稳定。
5. 对弱基础读者不够友好，阅读门槛偏高。

所以这次优化主要做了三件事：

1. 把项目结构理顺。
2. 把关键逻辑补强。
3. 把代码和文档讲明白。

## 4. 项目目录说明

建议你先从这个结构开始理解：

```text
ai_interview/
├── README.md
├── docs/
│   └── 项目修改记录.md
├── ai_gongwu_backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── endpoints/
│   │   │       └── interview.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── dependencies.py
│   │   ├── models/
│   │   │   └── schemas.py
│   │   ├── services/
│   │   │   ├── flow.py
│   │   │   ├── question_bank.py
│   │   │   ├── llm/
│   │   │   │   └── client.py
│   │   │   ├── media/
│   │   │   │   ├── audio_transcriber.py
│   │   │   │   └── video_processor.py
│   │   │   └── scoring/
│   │   │       ├── prompts.py
│   │   │       ├── calculator.py
│   │   │       └── keyword_matcher.py
│   │   ├── utils/
│   │   │   └── data_loader.py
│   │   └── main.py
│   ├── assets/
│   │   ├── questions/
│   │   │   ├── README.md
│   │   │   └── HN-LX-20200606-01.json
│   │   └── mock/
│   │       └── last_result.json
│   ├── scripts/
│   │   └── run_regression.py
│   ├── tests/
│   │   ├── test_question_bank.py
│   │   └── test_scoring_calculator.py
│   ├── requirements.txt
│   └── run.sh
├── reports/
│   └── regression/
│       └── README.md
└── 若干答题样例 .txt
```

## 5. 核心模块怎么理解

### 5.1 `app/main.py`

这是 FastAPI 的入口文件，负责：

1. 创建应用对象。
2. 注册路由。
3. 提供根路径跳转和健康检查。

你可以把它理解成“后端服务启动总开关”。

### 5.2 `app/api/endpoints/interview.py`

这是接口层，专门做和 HTTP 有关的工作：

1. 接收上传文件。
2. 读取表单参数。
3. 处理异常并返回 HTTP 状态码。
4. 调用业务服务。

如果以后前端调用失败，你第一步通常先看这里。

### 5.3 `app/services/flow.py`

这是最核心的业务编排层，负责把多个子模块串起来：

1. 读取题目。
2. 解析媒体。
3. 生成 Prompt。
4. 调大模型。
5. 做后处理。

如果你只想看“完整评分流程”，优先读这个文件。

### 5.4 `app/services/question_bank.py`

负责题库加载和查询。

作用是：

1. 启动时把题库 JSON 读入内存。
2. 通过 `question_id` 找到对应题目。
3. 保证题目结构合法、ID 不重复。

### 5.5 `app/services/llm/client.py`

负责调用大模型。

里面做了这些保护：

1. 统一 API 入口。
2. 尽量要求模型返回 JSON。
3. JSON 解析失败时自动重试。
4. 尝试从不规范输出中抽取 JSON。

这个模块很重要，因为很多“幻觉问题”并不只来自模型内容本身，也来自输出不稳定。

### 5.6 `app/services/scoring/prompts.py`

负责拼接评分 Prompt。

设计重点是：

1. 题目信息清楚。
2. 评分标准清楚。
3. 视觉观察和 transcript 分开。
4. 明确要求模型提供证据引用。

### 5.7 `app/services/scoring/calculator.py`

这是本项目现在最关键的“防失真”模块。

它会对模型输出做二次校验，主要处理：

1. 维度名错误。
2. 分数越界。
3. 总分不一致。
4. 模型引用了 transcript 中不存在的原话。
5. 作答太短时的强制降分。

如果你想继续降低幻觉，这个文件一定要重点读。

### 5.8 `app/services/media/*`

这部分负责媒体解析：

1. `audio_transcriber.py`：Whisper 转文字。
2. `video_processor.py`：视频抽音频 + 视觉观察。

### 5.9 `app/models/schemas.py`

这里定义了系统的数据结构。

你可以把它理解成“接口合同”和“数据模板”。
只要把这里看懂，很多函数传参和返回值就会清晰很多。

## 6. 当前评分流程

完整流程如下：

1. 前端调用 `/api/v1/interview/evaluate` 或 `/api/v1/interview/evaluate/text`。
2. 路由层接收输入并做基础校验。
3. `InterviewFlowService` 根据输入类型选择文本/音频/视频处理路径。
4. 系统根据 `question_id` 从题库中取出题目信息。
5. 第一阶段先让模型只抽取可核验的原文证据。
6. 系统对证据做校验，并补充规则型缺失证据。
7. 第二阶段再让模型只基于证据包打分。
8. `calculator.py` 对结果做证据绑定校验、分数校验和最终收敛。
9. 返回统一 API 响应，并把过程数据落库。

## 7. 这次重点做了哪些优化

### 7.1 后端结构优化

1. 新增题库服务 `QuestionBank`，真正支持 `question_id` 查询。
2. 增加统一数据模型，避免返回结构随意变化。
3. 把服务依赖做成缓存复用，减少重复初始化。
4. 补充路径解析能力，减少启动目录变化引起的路径报错。

### 7.2 幻觉抑制优化

1. 把 transcript 和视觉观察拆开，避免模型把视觉描述当作考生原话。
2. 第一阶段只抽证据，第二阶段只基于证据评分。
3. 抽象加扣分理由必须绑定证据 ID。
4. 后处理阶段会校验引用是否真实出现在 transcript 中。
5. 如果模型胡乱写维度、总分不一致、理由不绑定证据，会自动修正并记录到 `validation_notes`。

### 7.3 可维护性优化

1. 核心代码补充了大量中文注释。
2. 补了测试文件，方便后续回归验证。
3. 完善了 `requirements.txt`。
4. 增加了更清晰的模块边界。

## 8. 环境准备

推荐使用 Python 3.10 及以上版本。

如果你要本地运行，建议步骤如下：

```bash
cd /home/quyu/ai_interview
python3 -m venv .venv
source .venv/bin/activate
pip install -r ai_gongwu_backend/requirements.txt
```

如果你的机器不方便安装完整依赖，可以分层理解：

1. 最基础运行：`fastapi`、`uvicorn`、`pydantic`、`pydantic-settings`、`python-multipart`
2. 模型调用：`openai`
3. 语音转写：`openai-whisper`、`torch`
4. 视频视觉分析：`opencv-python-headless`
5. 视频抽音频：系统还需要安装 `ffmpeg`

## 9. 环境变量配置

建议在 [ai_gongwu_backend](/home/quyu/ai_interview/ai_gongwu_backend) 目录下创建 `.env` 文件，例如：

```env
LLM_PROVIDER=QWEN
LLM_API_KEY=你的密钥
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen3-coder-plus

QUESTION_DB_PATH=assets/questions
WHISPER_MODEL_SIZE=base
WHISPER_CPU_THREADS=4
WHISPER_LANGUAGE=zh
ENABLE_VISUAL_ANALYSIS=true

MIN_VALID_WORDS=15
MIN_WORDS_PENALTY_RATIO=0.2
SCORE_TOLERANCE=2.0
MAX_RATIONALE_CHARS=400
```

## 10. 如何启动项目

### 方式一：直接用 uvicorn

```bash
cd /home/quyu/ai_interview/ai_gongwu_backend
uvicorn app.main:app --reload --port 9000
```

### 方式二：运行脚本

```bash
cd /home/quyu/ai_interview/ai_gongwu_backend
bash run.sh
```

启动后打开：

```text
http://127.0.0.1:9000/docs
```

## 11. 接口说明

### 11.1 健康检查

```http
GET /health
```

示例返回：

```json
{
  "status": "ok",
  "service": "公考面试AI测评系统",
  "version": "1.1.0",
  "question_count": 1
}
```

### 11.2 文本测评接口

```http
POST /api/v1/interview/evaluate/text
```

表单字段：

1. `question_id`
2. `text_file`

### 11.3 音频/视频测评接口

```http
POST /api/v1/interview/evaluate
```

表单字段：

1. `question_id`
2. `media_file`

### 11.4 题目列表接口

```http
GET /api/v1/interview/questions
```

用途：

1. 查看当前加载了哪些题目。
2. 查看每道题是否已经配置了分档和回归样本。

### 11.5 题目详情接口

```http
GET /api/v1/interview/questions/{question_id}
```

用途：

1. 查看单题完整配置。
2. 联调前端题目选择器。
3. 核查当前题目的 `scoreBands` 和 `regressionCases`。

## 12. 返回结果字段说明

最终返回数据主要包含：

1. `dimension_scores`
   表示各维度得分。
2. `deduction_details`
   表示扣分原因。
3. `bonus_details`
   表示加分原因。
4. `evidence_quotes`
   表示模型声称使用的原文证据。
5. `rationale`
   表示总体评价。
6. `total_score`
   表示最终总分。
7. `matched_keywords`
   表示系统自己匹配到的关键词。
8. `validation_notes`
   表示系统自动修正了哪些模型问题。

## 13. 如何理解“幻觉”

在这个项目里，常见幻觉不是指“模型胡说八道”这么简单，而是指：

1. 模型引用了考生没说过的话。
2. 模型把视觉观察误当成考生表达内容。
3. 模型写了题目中根本不存在的评分维度。
4. 模型给出的总分和分项分对不上。
5. 模型在证据不足时仍然下了很重的结论。

当前项目已经加了几层防线，但还不能说完全解决。

## 14. 如何测试项目

### 14.1 代码级测试

```bash
cd /home/quyu/ai_interview/ai_gongwu_backend
python -m unittest discover -s tests
```

### 14.2 语法检查

```bash
cd /home/quyu/ai_interview
python3 -m compileall ai_gongwu_backend/app ai_gongwu_backend/tests
```

### 14.3 人工对比测试

建议你直接用根目录已有样例文本反复测，重点观察：

1. 低分文本是否真能拉开差距。
2. 高分文本是否能命中强关键词和 bonus。
3. 模型有没有引用不存在的原话。
4. `validation_notes` 是否频繁出现异常修正。

### 14.4 批量回归测试

项目已经补了专门的批量回归脚本：

```bash
cd /home/quyu/ai_interview/ai_gongwu_backend
./venv/bin/python scripts/run_regression.py
```

可选参数：

1. `--question-id HN-LX-20200606-01`
   只跑指定题目。
2. `--output-dir /path/to/output`
   自定义输出目录。
3. `--persist`
   把回归结果也写入数据库。默认不落库。

脚本会根据题目 JSON 里的 `regressionCases` 自动读取样本，并在 [reports/regression](/home/quyu/ai_interview/reports/regression) 下生成：

1. `JSON` 明细报表
2. `Markdown` 汇总报表

## 15. 后续最值得做的优化方向

如果你想继续把项目做好，我建议按下面优先级推进：

### 优先级 A：先提高结果可信度

1. 把评分改成“两阶段”：
   第一阶段只抽证据；
   第二阶段只基于证据打分。
2. 保存每次请求的：
   - transcript
   - prompt
   - raw_llm_output
   - final_result
3. 对 evidence 缺失或 validation_notes 过多的结果打上人工复核标记。

### 优先级 B：提高工程可用性

1. 加数据库，保存测评记录。
2. 增加日志追踪和请求 ID。
3. 增加统一异常处理中间件。
4. 增加 Docker 部署文件。

### 优先级 C：提高模型效果

1. 引入更稳定的评分模板。
2. 扩充题库，不要只依赖单题数据。
3. 做少量人工标注数据，用于对比模型评分偏差。
4. 按题型拆分 Prompt，不要所有题共用一套评分策略。
5. 每道题单独维护 `scoreBands` 和 `regressionCases`，不要跨题复用同一套阈值。

## 16. 初学者建议怎么读这个项目

推荐阅读顺序：

1. 先读 [README.md](/home/quyu/ai_interview/README.md)
2. 再读 [schemas.py](/home/quyu/ai_interview/ai_gongwu_backend/app/models/schemas.py)
3. 再读 [main.py](/home/quyu/ai_interview/ai_gongwu_backend/app/main.py)
4. 再读 [interview.py](/home/quyu/ai_interview/ai_gongwu_backend/app/api/endpoints/interview.py)
5. 再读 [flow.py](/home/quyu/ai_interview/ai_gongwu_backend/app/services/flow.py)
6. 最后重点读：
   - [prompts.py](/home/quyu/ai_interview/ai_gongwu_backend/app/services/scoring/prompts.py)
   - [client.py](/home/quyu/ai_interview/ai_gongwu_backend/app/services/llm/client.py)
   - [calculator.py](/home/quyu/ai_interview/ai_gongwu_backend/app/services/scoring/calculator.py)

## 17. 相关文档

本次修改记录见：

[项目修改记录](/home/quyu/ai_interview/docs/项目修改记录.md)

如果你后面继续改项目，建议每做一轮重构都追加记录，这样你自己回头看会非常轻松。

## 18. 样本分类入口

为了区分“通用高分”和“河南省直高分”，已经新增分类目录：

1. [sample_sets/通用高分](/home/quyu/ai_interview/sample_sets/通用高分)
2. [sample_sets/河南省直高分](/home/quyu/ai_interview/sample_sets/河南省直高分)
3. [sample_sets/非高分参考](/home/quyu/ai_interview/sample_sets/非高分参考)
4. 分类说明见 [sample_sets/README.md](/home/quyu/ai_interview/sample_sets/README.md)

## 19. 多题扩展建议

现在题库已经支持“目录式多题配置”：

1. 每道题单独一个 JSON，放在 [assets/questions](/home/quyu/ai_interview/ai_gongwu_backend/assets/questions)。
2. 题目文件名建议直接用 `question_id.json`。
3. 每道题都建议同时维护：
   - `scoreBands`
   - `regressionCases`
4. 新增题目后，直接跑一次 `scripts/run_regression.py` 做回归，不要只靠人工点接口。
