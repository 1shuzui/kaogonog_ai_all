# 公考面试 AI 测评平台

> 生产地址：https://xzqianmianyuzhoukeji.com  
> 微信小程序：公考面试AI测评

## 1. 项目概述

一个面向公考面试的 AI 智能测评平台，提供 PC 网页端与微信小程序双端服务，支持结构化面试的全流程模拟、评分与复盘。

**核心能力：**

- 🎯 **全真模拟** — 按真题套卷连续作答，录音/录像，自动转写与评分
- 📋 **专项练习** — 按题型维度自由组合题目，即时练习即时反馈
- 🎯 **定向备面** — 按考试大类 → 地区 → 方向 → 年份精准筛选真题
- 🏦 **题库系统** — 550+ 道结构化面试真题，支持多级筛选与检索
- 🤖 **AI 评分** — 两阶段证据抽取+约束评分，六维能力雷达图
- 💳 **会员体系** — 按时/包月套餐，微信小程序虚拟支付
- 📱 **小程序** — 微信小程序端录音作答，体验与 PC 对齐

---

## 2. 项目架构

```
kaogong_ai/
├── civil-interview-backend/     # FastAPI 业务后端（主）
│   ├── app/
│   │   ├── api/v1/routes/       # 接口路由（题库/考试/评分/支付/用户）
│   │   ├── core/                # 配置/安全/AI 客户端/访问控制
│   │   ├── models/              # SQLAlchemy ORM
│   │   ├── schemas/             # Pydantic 数据模型
│   │   └── services/            # 业务逻辑层
│   ├── main.py                  # 入口
│   └── database_setup.py        # 数据库初始化与种子数据
│
├── civil-interview-frontend/    # PC 网页前端 (Vue 3 + Ant Design Vue)
│   └── src/
│       ├── views/               # 页面组件
│       ├── components/          # 公共组件
│       ├── stores/              # Pinia 状态管理
│       ├── composables/         # 组合式函数
│       └── utils/               # 工具函数
│
├── civil-interview-miniprogram/ # 微信小程序 (uni-app + Vue 3)
│   └── src/
│       ├── pages/               # 页面
│       ├── components/          # 组件
│       ├── stores/              # Pinia 状态管理
│       └── utils/               # 工具函数
│
├── ai_gongwu_backend/           # 原始评分引擎（已被 civil-interview-backend 整合调用）
│   ├── assets/questions/        # 题库 JSON 文件
│   └── scripts/                 # 导入/回归测试脚本
│
└── scripts/
    └── deploy_clean_to_server.sh # 一键部署脚本
```

**代码规模：** 后端 66 个 Python 文件 | PC 前端 105 个 Vue/JS 文件 | 小程序 73 个 Vue/JS 文件 | 评分引擎 44 个 Python 文件

---

## 3. 技术栈

| 层 | 技术 | 说明 |
|---|------|------|
| **后端框架** | FastAPI + Uvicorn | Python 3.10，异步 API |
| **数据库** | MySQL 8.0 + SQLAlchemy | InnoDB，JSON 字段存储题目元数据 |
| **缓存** | Redis 5.x | 评分结果缓存、用户会话 |
| **AI/LLM** | DeepSeek v4-Flash | 评分与证据抽取 |
| **ASR 转写** | OpenAI Whisper (base) | 本地部署，zhconv 繁简转换 |
| **PC 前端** | Vue 3 + Ant Design Vue 4 | Vite 构建，Pinia 状态管理 |
| **小程序** | uni-app (Vue 3) | 微信原生录音 API，mp-weixin 编译 |
| **部署** | Ubuntu 22.04 + Nginx | pyarmor 代码混淆，systemd 守护 |
| **支付** | 微信小程序虚拟支付 | 沙箱/现网切换，退款 API |

---

## 4. 核心功能模块

### 4.1 考试与练习

| 模式 | 说明 |
|------|------|
| **专项练习** (free) | 自由选择题型、数量、考试大类、地区、方向、年份 |
| **全真模拟** (fullExam) | 按真题套卷连续作答，保留真实题序与计时 |
| **定向备面** | 精准筛选：考试大类 → 地区 → 方向 → 年份生成题组 |
| **专项训练** | 按六维（综合分析/组织管理/应急应变/人际沟通/情景模拟/岗位认知）定向训练 |
| **试用模式** | 未付费用户体验 1 道引导题，含完整评分流程 |

### 4.2 AI 评分引擎

```
录音/录像 → ASR 转写(Whisper base+zhconv) → 两阶段 LLM 评分(DeepSeek v4-Flash)
                                              ├── 第1阶段: 证据抽取
                                              └── 第2阶段: 证据约束打分 → 六维雷达图
```

评分维度：综合分析(20) | 实务落地(20) | 应急应变(15) | 法治思维(15) | 逻辑结构(15) | 语言表达(15) = 满分 100

### 4.3 题库系统

- **550+ 道**结构化面试真题，覆盖 30+ 省份
- 多级筛选：考试大类 → 地区 → 方向 → 年份 → 三级/四级分类 → 题型维度
- 管理员：批量导入（JSON/docx）、编辑、删除
- 来源：事业单位考试 / 省级公务员考试 / 国家公务员考试 / 银行招考 / 法检书记员 / 医疗卫生 等

### 4.4 会员与支付

| 套餐 | 价格 | 时长 |
|------|------|------|
| 3小时体验包 | ¥99 | 总计 3 小时 |
| 包月每日1小时 | ¥299 | 30 天，每天 1 小时 |
| 试用版 | ¥0 | 1 道引导题 |

- 微信小程序虚拟支付（`wx.requestVirtualPayment`）
- 支持退款（扣时长）与补偿（加时长）
- 时长精确到秒级扣减

### 4.5 用户系统

- 首次注册引导：选择默认省份 + 考试大类 + 注重题型
- 考试设置：可随时修改省份、考试大类、准备/作答时间、注重题型
- 历史记录：过往考试报告、维度趋势图
- 错题本/收藏夹

---

## 5. 部署

### 一键部署到生产服务器

```bash
cd /home/quyu/kaogong_ai

# 仅部署前端+小程序
bash scripts/deploy_clean_to_server.sh

# 含后端部署
DEPLOY_BACKEND=1 bash scripts/deploy_clean_to_server.sh
```

部署流程：前端 Vite 构建 → 小程序 mp-weixin 编译 → 后端 pyarmor 混淆 → rsync 同步 → pip 安装依赖 → systemd 重启

### 生产服务器配置

| 资源 | 规格 |
|------|------|
| CPU | 2 核（虚拟化） |
| 内存 | 4 GB |
| 磁盘 | 50 GB |
| 系统 | Ubuntu 22.04 |
| Web | Nginx + Let's Encrypt SSL |
| 域名 | xzqianmianyuzhoukeji.com |

### 本地开发

```bash
# 后端
cd civil-interview-backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8050

# PC 前端
cd civil-interview-frontend
npm install && npm run dev

# 小程序（需微信开发者工具）
cd civil-interview-miniprogram
npm install && npm run dev:mp-weixin
```

### 环境变量关键配置

```env
# .env (civil-interview-backend/)
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-xxx
LLM_MODEL=deepseek-v4-flash
REDIS_URL=redis://127.0.0.1:6379/0
MYSQL_HOST=127.0.0.1
MYSQL_DATABASE=kaogong_ai
WECHAT_PAY_ENABLED=true
WECHAT_VIRTUAL_PAY_ENV=0          # 0=现网 1=沙箱
WHISPER_MODEL_SIZE=base           # tiny/base/small/medium
```

---

## 6. 主要 API

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/questions/random` | 随机抽题（支持省份/维度/考试大类/年份等筛选） |
| `GET` | `/questions` | 题库分页列表 |
| `POST` | `/scoring/transcribe` | 音频转文字（ASR） |
| `POST` | `/scoring/evaluate` | LLM 评分 |
| `POST` | `/targeted/focus` | 定向备面聚焦分析 |
| `POST` | `/targeted/generate` | 定向备面生成题目 |
| `POST` | `/training/generate` | 专项训练生成题目 |
| `POST` | `/payment/orders` | 创建支付订单 |
| `GET` | `/positions` | 获取岗位筛选树 |
| `GET` | `/health` | 健康检查 |

完整 API 文档：`http://127.0.0.1:8050/docs`（本地）/ `https://xzqianmianyuzhoukeji.com/api/docs`（生产需认证）

---

## 7. 数据库

- **引擎**: MySQL 8.0 + InnoDB
- **数据量**: ~20 MB（329 道题，~2000 行总记录）
- **查询性能**: p95 延迟 < 32ms（100 并发下），Buffer Pool 命中率 99.998%
- **表结构**: questions / users / exams / exam_answers / payment_orders / user_subscriptions / history_records 等 12 张表

---

## 8. 评分链路详解

```
用户作答（音频/视频）
  │
  ├─→ ASR 转写（Whisper base + zhconv 简繁转换）
  │     └─ 回退：音频 < 2KB → 占位文本提示
  │
  ├─→ 第1阶段 LLM：证据抽取
  │     输入：题目全文 + 采分点 + 用户转录文本
  │     输出：present/absent/penalty/bonus 四类结构化证据
  │
  ├─→ 第2阶段 LLM：证据约束评分
  │     输入：第1阶段输出的证据 JSON + 评分维度
  │     输出：六维分数 + 理由 + evidence_ids 绑定
  │
  ├─→ 后处理校验
  │     - 维度名合法性校验
  │     - 分项分与总分一致性
  │     - 证据引用核验
  │     - 缺失型扣分验证
  │
  └─→ 结果返回
        - 总分 + 六维雷达图
        - 逐维度评语
        - 扣分/加分项目
        - 答案改进建议
```

---

## 9. 题库导入

支持两种导入方式：

1. **JSON 批量导入**（管理员 PC 端上传）
2. **docx 文档导入**（解析 Word 题库文档，自动提取题干/采分点/标签等）

导入脚本位于 `ai_gongwu_backend/scripts/import_question_bank.py`。

当前题库覆盖省份：北京/上海/广东/江苏/浙江/山东/河南/四川/安徽/福建/湖南/湖北/河北/辽宁/陕西等 30+ 省份。

---

## 10. 微信小程序

- **AppID**: wxa31c6e32dfa4b178
- **框架**: uni-app (Vue 3) → 编译为微信小程序
- **支付**: 微信虚拟支付（`wx.requestVirtualPayment`）
- **录音**: 使用微信原生 `RecorderManager` API
- **发布**: 通过微信开发者工具上传，审核后发布

小程序页面：首页 / 题库 / 练习准备 / 考试作答 / 结果 / 定向备面 / 专项训练 / 我的 / 支付 / 历史

---

## 11. 开发指南

### 目录约定

| 目录 | 说明 |
|------|------|
| `civil-interview-backend/app/api/v1/routes/` | 接口路由，按功能模块分文件 |
| `civil-interview-backend/app/services/` | 业务逻辑，与路由一一对应 |
| `civil-interview-backend/app/schemas/` | Pydantic 请求/响应模型 |
| `civil-interview-backend/app/core/` | 配置、安全、AI 调用、访问控制 |
| `civil-interview-frontend/src/views/` | 页面级组件 |
| `civil-interview-frontend/src/components/` | 可复用组件 |
| `civil-interview-frontend/src/stores/` | Pinia store |
| `civil-interview-frontend/src/utils/` | 工具函数、常量 |

### 关键文件

| 文件 | 作用 |
|------|------|
| `question_service.py` | 题库查询、随机抽题、题目筛选 |
| `scoring_service.py` | 两阶段 LLM 评分主流程 |
| `two_stage_scoring.py` | 证据抽取+约束评分 Prompt 构建 |
| `ai.py` | LLM/ASR 调用客户端 |
| `payment_service.py` | 支付/退款/补偿业务逻辑 |
| `wechat_pay_service.py` | 微信虚拟支付 API 封装 |
| `targetedOptions.js` | 前端岗位筛选树数据源 |
| `useMediaRecorder.js` | 浏览器录音/录像封装 |

### 新增功能检查清单

1. 接口路由 → `routes/`
2. 请求/响应 Schema → `schemas/common.py`
3. 业务逻辑 → `services/`
4. 前端页面 → `views/`
5. 前端 API 调用 → `api/`
6. 权限控制 → `access.py`
7. 数据库迁移 → `entities.py` + `database_setup.py`

---

## 12. 性能基准

| 指标 | 值 |
|------|-----|
| MySQL 查询 p95（100并发） | < 32ms |
| Buffer Pool 命中率 | 99.998% |
| LLM 评分（单题） | 15-30s（两次 API 调用） |
| ASR 转写（3分钟音频） | 10-30s（Whisper base CPU） |
| 前端首屏加载 | < 2s |
| 服务器内存占用 | Python 688MB + MySQL 82MB + Redis ~1MB |

---

## 13. 后续规划

- [ ] ASR 升级：Whisper base → 云端 qwen3-asr-flash，进一步提升转写质量
- [ ] 视频分析：OpenCV 面部/姿态检测在服务端稳定落地（当前音频可用）
- [ ] 题目自动生成：LLM 根据岗位/题型自动出题
- [ ] 多语言支持：粤语/方言 ASR
- [ ] 评分模型微调：基于人工标注数据 fine-tune
