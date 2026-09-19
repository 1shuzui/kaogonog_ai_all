# 评分接口与仪态分契约

## 目标

评分结果要同时表达题目内容质量和仪态评分，且必须保证默认仪态分不会在缓存、二次装饰或后续真实仪态评分中重复累加。

本契约适用于后端 **/scoring** 路径和医疗卫生题库。历史非医疗题如果没有 **hasAppearanceScore**，继续使用原有的单一题目满分口径。

## 接口

### POST /scoring/evaluate

请求体：

~~~json
{
  "questionId": "SD-MED-SET001-01",
  "transcript": "考生作答文字稿，最长 5000 字符",
  "examId": "可选考试 ID",
  "answerMeta": {
    "answerTiming": {
      "actualSeconds": 240,
      "standardSeconds": 300,
      "overtimeSeconds": 0
    },
    "skipReason": "",
    "asrStatus": "success"
  }
}
~~~

**questionId** 与 **transcript** 是必填，**examId** 和 **answerMeta** 可选。answerMeta 是展示和审计信息，不能代替真实作答内容，也不是将实际仪态分从客户端写入后端的入口。

正常评分响应至少应按下列语义消费：

~~~json
{
  "contentScore": 76.0,
  "appearanceScore": 5.0,
  "appearanceScoreMax": 5.0,
  "appearanceScoreSource": "profile_default",
  "appearanceScoreScope": "question",
  "totalScore": 81.0,
  "maxScore": 100.0,
  "questionScore": 76.0,
  "questionMaxScore": 100.0,
  "scoreCalculationNote": "仪态分已按默认值计入。",
  "dimensions": [],
  "grade": "B",
  "aiComment": "评分完成"
}
~~~

字段含义：

| 字段 | 含义 | 消费规则 |
| --- | --- | --- |
| contentScore | 归一化后映射回题目内容上限的得分 | 与题目 questionScore 同量纲。 |
| appearanceScore | 当前实际生效的仪态得分 | 默认或真实值，只取一个。 |
| appearanceScoreMax | 仪态分上限 | 用于展示和夹取真实分。 |
| appearanceScoreSource | source_explicit、profile_default 或 actual | actual 表示真实评分已经替换默认值。 |
| appearanceScoreScope | question 或 suite | suite 作用域不得按题累加。 |
| totalScore | 当前题的有效总分 | 通常为 contentScore + appearanceScore。 |
| maxScore | 当前题有效满分 | 通常为 questionScore + appearanceScoreMax。 |
| questionScore | 为兼容旧页面保留的当前内容得分别名 | 不再表示含仪态的总分。 |
| questionMaxScore | 有效题目满分 | 与 maxScore 对齐。 |
| scoreCalculationNote | 面向页面与排障的分数说明 | 不是再次计算分数的输入。 |

### 其他评分接口

| 路径 | 作用 |
| --- | --- |
| POST /scoring/transcribe | 上传音频/视频进行 ASR；携带 examId 时先校验考试归属并保存文字稿。 |
| GET /scoring/asr-status | 返回 FunASR/远程 ASR、ffmpeg 和模型就绪情况。 |
| GET /scoring/result/{examId}/{questionId} | 获取已持久化评分结果。 |

## 分数计算规则

### 题目级仪态分

当 **appearanceScoreScope=question** 时：

~~~text
内容上限 = questionScore
有效满分 = questionScore + appearanceScoreMax
最终分 = contentScore + appearanceScore
~~~

例如内容上限为 95、默认仪态分为 5 时，内容评分 80/100 会换算成 76/95，最终得到 81/100。再次读取缓存或再次装饰同一结果时，必须复用已经存在的 contentScore，而不能再加一个 5。

### 套题级仪态分

当 **appearanceScoreScope=suite** 时：

~~~text
套题内容合计 = Σ questionScore
整套仪态分 = 一次 appearanceScore
整套总分 = 套题内容合计 + 整套仪态分
~~~

题目响应仍可带有仪态元数据，方便解释题源规则；但套题汇总只能读取 **/exam/full-suites** 返回的 **totalScore**、**appearanceScoreScope** 和 **scoreCalculationNote**，不能把每道题的 appearanceScore 相加。

### 默认值和真实值

| 情况 | appearanceScoreSource | 取值 |
| --- | --- | --- |
| 源文档明确写出可执行仪态分 | source_explicit | 使用源文档数值。 |
| 医疗 profile 没有可执行仪态细则 | profile_default | 当前默认 5，且 appearanceScoreMax 为 5。 |
| 未来真实仪态评分器已给出分数 | actual | 用真实分替换默认/源默认值，并限制在 0 到 appearanceScoreMax。 |

真实仪态分是服务层内部结果装饰契约：评分器应在调用评分结果装饰逻辑前提供 **appearanceScore** 与 **appearanceScoreSource=actual**。当前 EvaluateRequest 不把它暴露为客户端可写字段，以免客户端伪造评分。

当前的视频观察仍可留在评分结果中，但在没有经过批准的仪态评分器前，不能以视频观察自动扣减默认 5 分。

## 特殊边界

- 转写接口收到 `examId` 后立即保存文字稿；评分接口也在调用模型前保存原文，兼容旧客户端只在评分请求中传入 `examId`。点评失败后保留原文，不能转换为“未作答”。
- DeepSeek JSON 请求明确使用 `response_format={"type":"json_object"}` 和 `thinking.type=disabled`。当前 Flash 模型默认思考可能耗尽短输出预算，产生空正文；截断响应必须增加输出预算后重试，不能当成空答案。
- 第一阶段没有有效原文证据时，跳过空证据评分，直接把完整答案交给外部模型。正常第二阶段同时携带原文和题库参考答案，参考答案不能冒充考生内容。
- 评分缓存指纹包含 `scoringSchema=evidence-source-v2`，新版本不复用旧版空证据错误分数。小程序只有收到明确的 `totalScore` 才展示分数；已存文字稿、尚未点评的记录显示“答案已保存 · 待点评”。
- 对已结束考试继续点评后，后端同步刷新历史汇总，并保留原考试结束时间。小程序重试同一录音时复用已识别的文字稿，避免再次上传和转写。
- 小程序音频/视频转写超时统一为 120 秒，留出上传、模型冷启动和长录音推理余量；请求完成即返回，不固定等待。2026-09-19 线上实测约 147 秒录音的冷启动转写为 50.72 秒，随后外部模型点评为 10.83 秒。两段耗时应分开观察，不能把点评耗时当作整段流程耗时。
- 含仪态分的结果，标题、圆环和题目标签统一展示 `totalScore/maxScore`，不能把内容分别名 `questionScore` 与含仪态满分混搭。旧版非仪态题仍保留 `questionScore/questionMaxScore` 的题目赋分换算。标注“百分制”时必须实际换算为百分比，而不是直接将 36 分制等结果冠以百分制。

模型调用说明参见 [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/) 和 [Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)。维持 `LOCAL_REFERENCE_SCORING=false`，不因费用或速度限制正常用户的答题流程。

- 题库中 **95 + 5 = 100** 以及其他内容分上限加仪态分上限的组合都合法，不能产生分值冲突、待确认状态或缩放。
- **fullScore/effectiveFullScore** 应以源内容分和仪态分上限计算，不能由客户端猜测。部分通用医疗题的内容分并非 95。
- 无有效文字稿的路由预筛会走全零结果分支，早于正常的评分结果装饰路径。它是“无效作答”处理，不应用来推断正常医疗题的默认仪态分计算；若业务希望无效作答也保留仪态默认分，应先明确规则并改动该分支及测试。
- 短答收敛只压缩内容分，仪态分保持单独计入，避免为了短答规则意外把仪态分再次扣掉或重复加入。

## 回归要求

### 2026-09-19 验收口径修复

- 用户界面已停用文字作答，只保留录音、录像。`/scoring/evaluate` 的 `transcript` 参数继续支持录音转写和已保存原文重试，先保存原文再点评；原文直接重试不重复上传或调用 ASR，兼容既有文字答案。客户端显式传入原文的 5000 字校验保持不变，不能因停用输入框而封禁语音识别的文字稿。
- 能力维度统一为内容百分制权重：综合分析 20、实务落地 20，其余四项各 15。仪态题的题目内容赋分不再错误缩小能力条；contentMaxScore 明示内容上限。
- `score_summary.py` 是交卷、历史列表、统计、趋势的共同汇总入口。按已评分答案的实际题目赋分计算得分率，映射到 100 分；套题级仪态分按 suiteKey 仅计一次，实际仪态分替代默认值。能力表现合并本轮全部已评分题，不再只取最后一题。
- 读取旧数据时使用已保存的逐题成绩统一展示量纲，不重新调用模型，不改写原始评分 JSON 或完成时间。只有新交卷/重评才持久化新汇总；尚未点评的原文仍显示待点评。
- 小程序结果页补齐录像回放；本机临时录像或服务端已存录像均可显示。真机权限、微信域名配置、录像格式兼容仍须用微信开发者工具/真机复核。
- 保持 `LOCAL_REFERENCE_SCORING=false`。前期不新增评分限额或降级到本地评分；后续通过记录耗时、缓存命中率与费用评估优化。

任何评分改动至少覆盖：

1. 95 内容分 + 5 默认仪态分；
2. 连续两次装饰/缓存命中后总分不增加；
3. actual=3 替换默认 5 后总分减少 2，而不是变成 8；
4. suite 作用域总分只加一次仪态分；
5. 非医疗旧题的评分结果保持兼容。

现有最低回归入口是 civil-interview-backend/tests/test_scoring_appearance_score.py。
