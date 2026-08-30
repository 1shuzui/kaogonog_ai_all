# 定向备面、门户与岗位筛选接口契约

## 设计边界

定向备面是展示和筛选能力，不是重新定义题源。一个医疗卫生题可以同时被：

- **事业单位考试 / 山东省** 的真实题源路径找到；
- **医疗卫生面试** 的门户路径找到；
- **医师岗、护理岗、医技岗、药师岗、行政岗** 等岗位方向继续收窄。

任何一层都不能覆盖另一个层的真实含义。

## GET /positions

返回后端权威的 **TARGETED_POSITION_TREE** 与 legacy positions。两端优先使用后端结果；PC 与小程序中的 DEFAULT_TARGETED_POSITION_TREE 仅作为请求失败时的兜底，更新分类树时必须保持语义一致。

医疗卫生的当前入口关系：

| 展示入口 | 真实筛选条件 | 岗位方向 |
| --- | --- | --- |
| 事业单位考试 → 山东省 | province=shandong、examCategory=事业单位考试、examSubcategory=山东省 | 常规事业单位及医疗门户可继续筛选 |
| 事业单位考试 → 江苏省 | province=jiangsu、examCategory=事业单位考试、examSubcategory=江苏省 | 已有医疗卫生相关岗位方向 |
| 医疗卫生面试 → 山东省 | 上述山东真实条件 + portalTag=医疗卫生面试 | 医师、护理、医技、药师、行政 |
| 医疗卫生面试 → 通用医疗卫生题库 | province=national、examCategory=事业单位考试、examSubcategory=通用医疗卫生题库、portalTag=医疗卫生面试 | 医师、护理、医技、药师、行政 |

## POST /targeted/focus

返回真实题库统计或管理员已发布的重点分析。需要付费权益。

请求中可用的关键筛选：

| 字段 | 语义 |
| --- | --- |
| province、position | 地区与旧岗位兼容筛选。 |
| examCategory、examSubcategory、subcategory、subcategory2 | 真实考试体系与层级。 |
| portalTag、displayPortal | 门户标签；与题库 portalTags/displayPortals 匹配。 |
| positionTag、positionTags、positionType | 岗位标签或岗位类型；支持字符串或标签列表。 |
| interviewFormat、timingMode、questionCount、prepTime、answerTime | 展示、时间和题量上下文。 |
| targetCode、targetName | 稳定入口标识及展示名。 |
| year | 真实来源年份筛选。 |

示例：山东医疗医师岗。

~~~json
{
  "province": "shandong",
  "position": "medical",
  "examCategory": "事业单位考试",
  "examSubcategory": "山东省",
  "portalTag": "医疗卫生面试",
  "displayPortal": "医疗卫生面试",
  "positionType": "医师岗",
  "interviewFormat": "医疗卫生结构化面试"
}
~~~

服务顺序是：先找管理员启用的目标配置；无配置时才从真实题库统计；若题库数量不足，返回明确空态，不能套用其他地区或其他考试体系的“通用重点”。

## POST /targeted/generate 与 POST /training/generate

两条接口都需要付费权益。

| 路径 | 输入重点 | 返回 |
| --- | --- | --- |
| POST /targeted/generate | province、position、count 与同一套真实/门户/岗位筛选字段 | 真实题库中的定向练习题与筛选回显。 |
| POST /training/generate | dimension、count、sourceMode 与可选 target filters | 按训练题型抽取/生成的专项练习题。 |

定向接口的 **sourceMode** 目前保留兼容和回显语义；当前路由会把实际题目选择固定到本地真实题库路径。新功能若要启用远程生成模式，必须先明确题源标记、审计和缓存边界，不能仅改变前端传参。

## 筛选匹配语义

1. 真实分类字段采用兼容的包含式匹配，以容纳历史分类文本；
2. portalTag/displayPortal 会在题目元数据的 **portalTags** 与 **displayPortals** 中查找；
3. positionType、positionTag、positionTags 会在岗位类型、岗位标签和原岗位文本中匹配；
4. **position=medical** 还兼容医疗标签和医疗门户；
5. province 与 examCategory 都必须保持一致，不能以“方向不限”跨省或跨考试体系；
6. 全国、通用、全国通用都会归一到 **national**。

## 管理员重点分析配置

| 路径 | 含义 |
| --- | --- |
| GET /targeted/focus/admin | 读取某个目标的自动统计、已发布配置与当前有效结果。 |
| PUT /targeted/focus/admin | 保存/发布人工重点分析；目标至少要有 targetCode、examCategory 或 portalTag。 |
| POST /targeted/focus/admin/disable | 停用配置，不删除历史记录，普通用户回退到真实统计或空态。 |

管理员发布内容可覆盖自动统计，但保存时必须带全量目标定位字段，避免“医疗卫生”这一展示名误覆盖不同省份、不同考试体系的配置。
