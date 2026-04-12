# kaogong_ai 工程联调与改造说明

更新时间：2026-04-11

## 1. 背景与目标

本次处理的直接目标有四个：

1. 将 `ai_interview` 当前工作区代码同步到 `kaogong_ai`。
2. 将仓库内“评分引擎、业务后端、前端”三段混合代码串成一条可运行链路。
3. 形成一份面向工程落地的改造与联调文档，便于后续维护。
4. 基于当前代码产出一份对外可交付的功能清单 `.docx`。

同步完成后，`kaogong_ai` 的实际工程角色如下：

1. `ai_gongwu_backend`
   角色：评分引擎与落库核心。
   职责：题库加载、文本/音视频解析、两阶段评分、确定性校验、测评记录落库。

2. `civil-interview-backend`
   角色：前端兼容业务后端。
   职责：对外保留前端原有接口协议，对内直接调用 `ai_gongwu_backend`。

3. `civil-interview-frontend`
   角色：Vue 业务前端。
   职责：登录、题库浏览、练习流程、历史记录、结果展示、定向备面、专项训练。

## 2. 目录与分层设计

推荐按下面的方式理解当前仓库：

```text
kaogong_ai/
├── ai_gongwu_backend/                 # 新评分引擎
│   ├── app/
│   ├── assets/questions/
│   ├── storage/ai_gongwu.db
│   └── tests/
├── civil-interview-backend/           # 前端兼容层
│   ├── main.py
│   └── storage/                       # 运行态数据（已加入忽略）
├── civil-interview-frontend/          # Vue 前端
│   ├── src/
│   └── package.json
└── docs/
    └── kaogong_ai工程联调与改造说明.md
```

### 2.1 分层边界

本次不再让前端直接适配 `ai_gongwu_backend` 的新接口，而是引入清晰边界：

1. 前端只依赖 `civil-interview-backend` 暴露的旧接口协议。
2. `civil-interview-backend` 负责接口兼容、会话编排、用户轻量状态和前端数据结构转换。
3. `ai_gongwu_backend` 继续作为评分引擎与数据事实来源，不承担前端兼容历史包袱。

这样做的理由是：

1. 前端历史接口面较大，直接改前端成本高、回归面大。
2. 新引擎接口更聚焦，更适合作为内核而不是直接承接所有页面协议。
3. 兼容层让“前端协议稳定”和“引擎持续升级”可以解耦。

## 3. 本次主要改造项

### 3.1 代码同步策略

已将 `ai_interview` 当前工作区内容同步到 `kaogong_ai`，保留 `kaogong_ai/.git` 仓库历史。

同步时排除了以下非代码目录：

1. `.git`
2. `.gitnexus`
3. `.claude`
4. `.venv`
5. `venv`
6. `__pycache__`
7. 常见 Python 缓存目录

这样做的原因是避免把源仓库的大体积虚拟环境和索引缓存直接复制到目标仓库。

### 3.2 重写前端兼容后端

`civil-interview-backend/main.py` 已重写为新的兼容层，核心能力如下：

1. 登录与轻量用户资料接口
2. 题库查询、随机抽题、自定义题目新增、批量 JSON 导入
3. 考试会话创建、录音上传、完结标记
4. 录音转写、文本评分、历史统计、趋势数据
5. 定向备面与专项训练接口

### 3.3 兼容层如何复用评分引擎

兼容层通过本地 Python 导入直接复用 `ai_gongwu_backend`：

1. `QuestionBank`
   用于加载标准题库与自定义镜像题库。

2. `InterviewFlowService`
   用于执行文本评分主流程。

3. `EvaluationStore`
   用于写入与读取测评记录。

4. `process_audio` / `process_video`
   用于转写音频、视频输入。

### 3.4 前端联调关键修复

已完成以下前端改动：

1. `src/api/scoring.js`
   浏览器上传录音时显式附带文件名和扩展名，避免后端拿到默认 `blob` 文件名后无法推断格式。

2. `src/stores/exam.js`
   评分请求透传 `examId`，使历史记录、结果回查和考试会话真正可关联。

3. `src/views/QuestionBank/BankList.vue`
   内置题库标记为“只读”，避免在界面层误导用户直接修改标准题。

4. `src/views/QuestionBank/BankEditor.vue`
   若进入内置题目编辑页，保存按钮自动受限，防止提交后端报错。

5. `src/views/QuestionBank/BankImport.vue`
   将导入预览结果转成 JSON 文件再提交后端，补齐原页面“预览后无法真正导入”的断链问题。

### 3.5 评分引擎媒体格式补充

`ai_gongwu_backend/app/core/config.py` 已将 `.webm` 加入支持的视频扩展名。

这一步是为了兼容浏览器 MediaRecorder 默认输出格式，避免后续直接调用引擎媒体接口时被后缀校验拦截。

## 4. 数据落点设计

### 4.1 核心评分数据

路径：`ai_gongwu_backend/storage/ai_gongwu.db`

用途：

1. 保存单次评分记录
2. 保存最终评分结果
3. 保存模型原始返回与后处理结果

### 4.2 兼容层运行态数据

路径：`civil-interview-backend/storage/`

当前使用以下 JSON 文件：

1. `users.json`
   保存轻量用户账号、资料与练习偏好。

2. `exam_sessions.json`
   保存考试会话、题目列表、关联记录 ID、上传记录和完成时间。

3. `custom_questions.json`
   保存前端创建或导入的自定义题目。

### 4.3 自定义题目镜像

路径：`ai_gongwu_backend/assets/questions/custom_frontend/`

用途：

1. 将前端自定义题目同步成评分引擎可识别的题库 JSON。
2. 让自定义题目不仅能展示，还能被 `InterviewFlowService` 真正评分。

## 5. 接口适配关系

### 5.1 前端题库接口

前端调用：

1. `GET /questions`
2. `GET /questions/random`
3. `GET /questions/{id}`
4. `POST /questions`
5. `PUT /questions/{id}`
6. `DELETE /questions/{id}`
7. `POST /questions/import`

兼容层处理：

1. 标准题库从 `ai_gongwu_backend/assets/questions` 读取。
2. 自定义题库从 `civil-interview-backend/storage/custom_questions.json` 读取。
3. 两者合并后转换成前端历史结构：
   - `stem`
   - `dimension`
   - `province`
   - `scoringPoints`
   - `keywords`
   - `readonly`

### 5.2 前端评分接口

前端链路：

1. `POST /exam/start`
2. `POST /exam/{examId}/upload`
3. `POST /scoring/transcribe`
4. `POST /scoring/evaluate`
5. `POST /exam/{examId}/complete`
6. `GET /scoring/result/{examId}/{questionId}`

兼容层实现方式：

1. `upload`
   只负责保存上传元信息和文件副本，不直接评分。

2. `transcribe`
   通过 `process_audio` / `process_video` 走转写链。

3. `evaluate`
   通过 `InterviewFlowService.evaluate_text_only()` 调用评分引擎。

4. `result`
   从 `EvaluationStore` 中回查评分结果，并转换为前端旧结构。

### 5.3 历史统计接口

前端调用：

1. `GET /history`
2. `GET /history/stats`
3. `GET /history/trend`

兼容层统计逻辑：

1. 以 `exam_sessions.json` 为考试会话索引。
2. 以 `ai_gongwu.db` 中的测评记录为分题明细来源。
3. 将单题分数统一换算为百分制，用于首页、个人分析和趋势图。

## 6. 联调启动建议

### 6.1 纯本地规则模式联调

如果只做本地烟雾测试，建议关闭真实大模型调用：

```bash
cd /home/quyu/kaogong_ai/ai_gongwu_backend
LLM_API_KEY='' /home/quyu/ai_interview/ai_gongwu_backend/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 9000
```

```bash
cd /home/quyu/kaogong_ai/civil-interview-backend
LLM_API_KEY='' COMPAT_FORCE_RULE_BASED=true /home/quyu/ai_interview/ai_gongwu_backend/venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8050
```

```bash
cd /home/quyu/kaogong_ai/civil-interview-frontend
npm install
npm run dev -- --host 127.0.0.1 --port 3001
```

### 6.2 真实模型联调

如果需要调用真实大模型：

1. 在 `kaogong_ai/.env` 或 `ai_gongwu_backend/.env` 中配置有效 `LLM_API_KEY`
2. 取消上面命令中的 `LLM_API_KEY=''`
3. 保持 `ffmpeg`、Whisper 模型和网络访问可用

## 7. 本次验证结果

验证日期：2026-04-11

### 7.1 静态校验

执行：

```bash
LLM_API_KEY='' /home/quyu/ai_interview/ai_gongwu_backend/venv/bin/python -m compileall \
  /home/quyu/kaogong_ai/ai_gongwu_backend/app \
  /home/quyu/kaogong_ai/civil-interview-backend \
  /home/quyu/kaogong_ai/ai_gongwu_backend/tests
```

结果：

1. 通过

### 7.2 评分引擎单测

执行：

```bash
cd /home/quyu/kaogong_ai/ai_gongwu_backend
LLM_API_KEY='' PYTHONPATH=/home/quyu/kaogong_ai/ai_gongwu_backend \
  /home/quyu/ai_interview/ai_gongwu_backend/venv/bin/python -m unittest discover -s tests -v
```

结果：

1. 共 12 项测试
2. 全部通过

### 7.3 前端构建

执行：

```bash
cd /home/quyu/kaogong_ai/civil-interview-frontend
npm run build
```

结果：

1. 构建通过
2. 仍存在较大 chunk 警告，但不影响当前运行

### 7.4 评分引擎接口烟雾测试

验证项：

1. `GET /health`
2. `GET /api/v1/interview/questions`
3. `POST /api/v1/interview/evaluate/text`

结果：

1. 健康检查通过
2. 题库列表正常返回 30 题
3. 使用 `28分.txt` 调用文本测评接口成功，返回 `200`，得分 `24.0`

### 7.5 兼容后端主链路烟雾测试

验证项：

1. 登录获取 token
2. 获取用户信息
3. 题库列表
4. 创建考试
5. 文本评分
6. 完成考试
7. 历史统计
8. 趋势查询

结果：

1. 全部通过
2. 兼容后端已能对接评分引擎完成一整条练习链路

### 7.6 媒体入口烟雾测试

验证方式：

1. 使用 `ffmpeg` 生成 1 秒静音 wav
2. 调用 `POST /scoring/transcribe`

结果：

1. 请求成功
2. 返回占位 transcript：`（未能识别到任何有效的人声作答）`
3. 说明媒体解析入口已连通

### 7.7 前端代理链路测试

验证项：

1. 启动 Vite dev server
2. 通过 `http://127.0.0.1:3001/api/questions?pageSize=2` 访问代理接口

结果：

1. 前端代理成功转发到兼容后端
2. 数据正常返回

### 7.8 题库管理补充验证

验证项：

1. `POST /questions` 创建自定义题目
2. `POST /questions/import` 导入 JSON 题目
3. 使用导入题目再次执行评分

结果：

1. 自定义题目新增成功
2. 批量导入成功
3. 导入题目可被评分引擎识别并完成评分

## 8. 当前限制与风险

1. 内置标准题库当前设计为只读。
   原因是这些题目直接对应评分引擎标准题库，若允许前端直接改写，会引入题目版本漂移和重复 ID 风险。

2. 兼容层的用户体系是轻量本地实现。
   它适合当前开发联调，不适合作为正式生产认证方案。

3. 媒体转写链路虽然已打通，但终端烟雾测试只验证了“接口可调用”和“文件可解析”。
   真正的麦克风质量、浏览器权限、视频流表现仍需在浏览器里做一次人工联调。

4. 前端构建仍存在大包警告。
   当前不影响交付，但如果后续要部署到弱网环境，建议继续做按页拆包和组件懒加载。

## 9. 后续建议

1. 如果要进入稳定迭代阶段，建议把 `civil-interview-backend` 再拆成：
   - `routers`
   - `services`
   - `state_store`
   - `mappers`

2. 如果要支持多用户和正式部署，建议把兼容层的用户、考试会话从 JSON 文件迁移到数据库。

3. 如果要支持标准题库在线编辑，建议给题库引入版本号与审核机制，而不是直接覆盖引擎题库 JSON。

4. 如果要提升结果页刷新恢复能力，建议在前端结果页中增加“按 examId 拉取整场多题结果”的接口，而不是仅回查单题。
