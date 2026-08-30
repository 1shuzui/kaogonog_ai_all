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

- 题库中 **95 + 5 = 100** 以及其他内容分上限加仪态分上限的组合都合法，不能产生分值冲突、待确认状态或缩放。
- **fullScore/effectiveFullScore** 应以源内容分和仪态分上限计算，不能由客户端猜测。部分通用医疗题的内容分并非 95。
- 无有效文字稿的路由预筛会走全零结果分支，早于正常的评分结果装饰路径。它是“无效作答”处理，不应用来推断正常医疗题的默认仪态分计算；若业务希望无效作答也保留仪态默认分，应先明确规则并改动该分支及测试。
- 短答收敛只压缩内容分，仪态分保持单独计入，避免为了短答规则意外把仪态分再次扣掉或重复加入。

## 回归要求

任何评分改动至少覆盖：

1. 95 内容分 + 5 默认仪态分；
2. 连续两次装饰/缓存命中后总分不增加；
3. actual=3 替换默认 5 后总分减少 2，而不是变成 8；
4. suite 作用域总分只加一次仪态分；
5. 非医疗旧题的评分结果保持兼容。

现有最低回归入口是 civil-interview-backend/tests/test_scoring_appearance_score.py。
