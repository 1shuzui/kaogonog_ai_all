# 题库、元数据与全真套题接口契约

## 适用边界

本文描述后端 **/questions** 与 **/exam/full-suites** 路径，尤其说明医疗卫生题库从生成 JSON 到数据库、再到客户端响应时如何保留来源、分类、套题和评分元数据。

详细的导入与题源维护流程见 [医疗卫生题库知识库](../data/medical-question-bank.md) 和 [题库维护运行手册](../ops/question-bank-maintenance.md)。

## 题目查询

### GET /questions

需要登录及扩展题库访问权益。支持的查询参数：

| 参数 | 语义 | 说明 |
| --- | --- | --- |
| keyword | 全文检索词 | 用于题干、标签和来源相关筛选。 |
| dimension | 训练题型/旧维度兼容值 | 不是评分能力维度。 |
| province | 地区 | 例如 shandong、jiangsu、national。 |
| position | 岗位方向 | 例如 medical、general；服务层会结合 positionTags、门户和岗位文本判断。 |
| subcategory、subcategory2 | 旧/细分分类 | 保留兼容，不替代真实考试体系。 |
| examCategory | 真实考试体系 | 医疗三批应传 事业单位考试。 |
| year | 年份 | 支持服务层已有的年份匹配。 |
| current、pageSize | 分页 | current 从 1 开始。 |

返回外层为：

~~~json
{
  "list": [
    {
      "id": "SD-MED-SET001-01",
      "stem": "题干文本",
      "province": "shandong",
      "scoringPoints": [{"name": "采分点", "score": 30}],
      "examCategory": "事业单位考试",
      "examSubcategory": "山东省",
      "portalTags": ["医疗卫生面试"],
      "positionTags": ["medical", "医师岗"],
      "suiteKey": "SD-MED-SET001",
      "questionNo": 1,
      "questionScore": 95,
      "appearanceScore": 5,
      "appearanceScoreScope": "suite",
      "effectiveFullScore": 100
    }
  ],
  "total": 259,
  "current": 1,
  "pageSize": 10
}
~~~

示例中的数值只演示字段关系。实际题目的 **questionScore** 不保证恒为 95，客户端应读取 **effectiveFullScore**，不要在页面写死 100。

### GET /questions/random

接受 **province**、**count**、**dimension**、**position**、**keyword**、**examCategory**、**subcategory**、**subcategory2**、**year**。随机练习与题库列表共用筛选规则，年份可用逗号多选；没有匹配题时返回空列表，不自动放宽筛选。不接受 portalTag、displayPortal 或 positionTags 这一组高级筛选；高级定向选题使用 [定向备面接口](targeted-training.md)。

## 开考与练习类型

POST /exam/start 除 questionIds 外接收可选 practiceMode：free、fullExam、training、targeted、trial；旧客户端省略时保存 legacy。数据库启动时幂等补齐 exams.practice_mode 列，旧记录保持 legacy，不猜测其历史类型。历史列表和详情返回 practiceMode、practiceModeName，并据此显示练习标题。提前结束训练仍保留完整题目顺序、已答文字与未答占位。

### GET /questions/{questionId}

返回与列表一致的标准题目表示，并补齐元数据透传。参考答案不作为公共详情字段返回；客户端只能使用 **hasReferenceAnswer** 判断后端是否有评分依据。

### 管理接口

POST /questions、PUT /questions/{questionId}、DELETE /questions/{questionId}、POST /questions/import 与 POST /questions/import/docx 都需要管理员权限。

管理 CRUD 的 Pydantic 请求模型以 **stem**、核心题目列和已定义的分类字段为边界。完整的题源追溯/仪态字段契约属于生成资产和同步链路；不要把前台的任意扩展 JSON 直接当作可持久化字段。若要扩展管理员编辑能力，必须先扩展 schema、_question_input_meta、响应透传和对应测试。

## 从生成资产到数据库

### 字段映射

| 生成 JSON | 数据库/REST 表示 | 用途 |
| --- | --- | --- |
| id | Question.id / id | 稳定题源 ID；医疗题不可按题干覆盖。 |
| question | Question.stem / stem | 题干。 |
| scoringPoints | Question.scoring_points / scoringPoints | 评分采分点。 |
| province | Question.province / province | 规范化地区代码。 |
| keywords._meta 与顶层元数据 | Question.keywords._meta | 来源、分类、套题、门户和分数扩展信息。 |
| referenceAnswer | keywords._meta.referenceAnswer | 仅供评分上下文，前台不直接展示。 |

资产同步会优先保留显式元数据。生成器应让顶层字段与 **_meta** 中同名字段一致；不要手工制造互相矛盾的两套数值。

### 题目元数据字段

| 类别 | 字段 | 约束 |
| --- | --- | --- |
| 真实分类 | examCategory、examSubcategory、subcategory、subcategory2、province、system | examCategory 与 province 必须分开；医疗三批为 事业单位考试。 |
| 展示/岗位 | portalTags、displayPortals、positionTags、positionType、interviewFormat、questionTypeCategory | 医疗门户使用 医疗卫生面试；至少含 medical 岗位标签。 |
| 来源追溯 | sourceDocument、originFile、sourceQuestionId、sourceDocumentType | originFile 是文件级组套和问题定位依据。 |
| 套题 | suiteId、suiteKey、suiteName、questionNo、hasCompleteSuiteLevel | 省级医疗题同一源 DOCX 的题使用同一 suiteKey。 |
| 分值 | questionScore、appearanceScore、appearanceScoreMax、appearanceScoreSource、appearanceScoreScope、effectiveFullScore、scoreCalculationNote | 见 [评分接口](scoring.md)。 |
| 质量状态 | classificationSource、classificationConfidence、reviewStatus、reviewReason | 默认仪态分不是待确认或错误理由。 |

## 全真套题

### GET /exam/full-suites

需要付费权益。支持 **examCategory**、**province**、**examSubcategory**、**subcategory**、**subcategory2**、**year**。

该接口当前不接收 portalTag、displayPortal、positionTag 或 positionTags。需要从医疗门户做题目级定向筛选时使用定向接口；需要新增全真套题门户筛选时，应同时扩展 route、service 过滤器、客户端和本契约。

返回的每个 suite 包含：

| 字段 | 含义 |
| --- | --- |
| id | 经过编码的套题标识，后续详情请求必须原样传回。 |
| suiteKey、suiteName、sourceDocument | 稳定组套键、展示标题和来源文档。 |
| questionCount、questionIds、questions | 题目数量、顺序 ID 与轻量题号索引。 |
| examCategory、examSubcategory、province、interviewFormat | 真实分类与展示规则。 |
| answerScoreTotal、appearanceScore、appearanceScoreMax、totalScore | 内容合计、仪态分、仪态上限与整套总分。 |
| appearanceScoreSource、appearanceScoreScope、scoreCalculationNote | 分数来源、题目/套题作用域与显示提示。 |
| portalTags、displayPortals、hasAppearanceScore | 门户标记和仪态项存在性。 |

### GET /exam/full-suites/{suiteId}/questions

需要付费权益，返回：

~~~json
{
  "suite": {"id": "...", "questionCount": 2, "appearanceScoreScope": "suite"},
  "questions": [
    {"id": "SD-MED-SET001-01", "questionNo": 1, "stem": "..."},
    {"id": "SD-MED-SET001-02", "questionNo": 2, "stem": "..."}
  ]
}
~~~

不要让客户端基于 GET /questions 的全量列表自行按 suiteKey 聚合。服务端的完整性检查、排序和来源约束才是正式套题资格的唯一来源。

### 正式套题资格

一个 suite 只有同时满足以下条件才会出现在全真列表：

1. 至少有 2 道题；
2. 题号从 1 开始连续；
3. 同一组使用同一个源文件套题键；
4. 任一题没有把 **hasCompleteSuiteLevel** 显式设为 false。

因此，通用医疗卫生 100 题虽然共享 **MED-GENERAL-BATCH**，也不会进入正式套题列表；山东和江苏的每个源 DOCX 则可以作为正式套题候选。

## 医疗卫生资产的稳定 ID

| Profile | ID/套题键规则 | 套题展示资格 |
| --- | --- | --- |
| medical_general | 优先保留源显式 ID，如 YL-综合-059；统一 MED-GENERAL-BATCH | 否 |
| shandong_medical | SD-MED-SET001-01 形式 | 是 |
| jiangsu_medical | JS-MED-SET001-01 形式 | 是 |

后端同步对带稳定来源 ID 的资产不再按题干合并。相同题干但不同来源、不同题号或不同套题键是不同资产，必须共存。

## 真实筛选选项

### GET /questions/filter-options

与 GET /questions 使用相同的登录依赖和 ensure_paid_access 权益检查，不对匿名或未开通用户公开库存元数据。静态路径注册在 /questions/{questionId} 之前。

接受 keyword、dimension、province、position、examCategory、subcategory、subcategory2、year，均为可选字符串，默认空值。year 为兼容筛选参数快照而接受，**不参与任何选项或计数的筛选**。不支持分页、portalTag、positionTags 或 examSubcategory，也不采用定向接口的宽松分类匹配。

公共范围为 keyword、dimension、province、position、examCategory 的共同约束：keyword 只检索题干，dimension 精确匹配；province 为空或 all 表示不限，national 只表示全国题源，不自动包含各省；岗位复用题库现有匹配，examCategory、subcategory、subcategory2 均保持精确匹配。

| 响应字段 | 统计范围与含义 |
| --- | --- |
| options.subcategory | 公共范围内非空分类值，忽略两个细分类及 year。 |
| options.subcategory2 | 公共范围 + subcategory，忽略 subcategory2 及 year。 |
| options.year | 公共范围 + subcategory + subcategory2 内可解析年份，去重、降序。 |
| questionCount | 与 options.year 相同范围的题目数，含未知年份题，不按已选 year 收窄，也不是各年份计数相加。 |
| unclassifiedYearCount | 上述范围内无法按现有题库规则解析年份的题目数。 |

响应固定为以下结构；数值仅为契约示例，不代表线上库存：

~~~json
{
  "options": {
    "year": ["2026", "2016"],
    "subcategory": ["盐城市"],
    "subcategory2": ["东台", "盐都"]
  },
  "unclassifiedYearCount": 1,
  "questionCount": 3
}
~~~

分类选项去重、按字符串顺序排序；排除缺失、非字符串和纯空白值，但不改写有效原值，以便原样传回精确查询。年份复用 _question_years_from_meta：examDate 优先于显式 year，再按套题/来源标题、来源题号、来源文档/原文件名兜底，不从题干或配置树造年份。无匹配时对应选项为空数组、计数为 0；未知年份只计数，不新增 year=unknown 查询语义。选择父级后客户端应清空失效的子级选择；清空所有细分类恢复公共范围。

此接口仅返回上述白名单字段，不序列化题目，不返回题干、参考答案、完整 _meta、源文件路径或用户信息。聚合服务仅查询元数据及岗位匹配必要列，不执行数据库写入、AI 生成、题库同步，不增加缓存或隐式样本上限。既有 get_current_user 的节流活跃时间更新行为保持不变，因此“只读”指新增题库聚合逻辑，不改变统一鉴权的既有副作用。

前端不得用全量 GET /questions、当前页样本或 GET /positions 配置树生成这些选项。接口失败时保留同参数的有效结果或展示可重试状态，不回退到固定年份表；该接口只说明题库列表语义下的可用选项，不代表某个定向入口的可用年份。
