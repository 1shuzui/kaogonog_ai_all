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

接受 **province**、**count**、**dimension**、**position**。这是普通随机练习接口，不接受 portalTag、displayPortal 或 positionTags 这一组高级筛选；需要按门户/岗位/真实考试体系精确选题时，使用 [定向备面接口](targeted-training.md)。

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
