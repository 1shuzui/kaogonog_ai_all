# 题库资产索引

题库原始 Word/doc、抽取文本和 normalized 文本已迁出 Git，统一归档到 `/home/quyu/doc_kaogong/question-bank/`。仓库内保留模板、索引和校验信息。

## 仓库内保留

| 路径 | 用途 |
| --- | --- |
| `templates/题库导入标准模板.json` | JSON 导入模板。 |
| `templates/题库导入标准模板.xlsx` | XLSX 导入模板。 |
| `templates/题库维护标准模板.docx` | DOCX 维护模板。 |
| `inventory.json` | 外置题库源文档清单。 |
| `checksums.sha256` | 外置题库源文档校验。 |

## 外部归档

- 原始题库源文档：`/home/quyu/doc_kaogong/question-bank/source/`
- 题库抽样报告：`/home/quyu/doc_kaogong/question-bank/reports/`
- 全量迁移记录：`/home/quyu/doc_kaogong/manifests/migration-moved.json`

医疗卫生题源按导入 profile 归档在以下目录：

- `source/medical_general`：通用医疗卫生 100 题，统一批次键，不作为正式 100 题套卷展示。
- `source/shandong_medical`：山东 137 个源文件、259 题，每个 DOCX 一个套题。
- `source/jiangsu_medical`：江苏实际 70 个源文件、187 题，每个 DOCX 一个套题；清单记录缺失的 `江苏新套03`，不计为解析失败。

源文档复制到外部归档时保留桌面原件，导入器支持重复传入 `--source-dir`；医疗题目统一使用真实考试大类 `事业单位考试`，`医疗卫生面试` 只作为门户展示标签。

医疗题库的完整导入、稳定 ID、套题资格、默认仪态分和验收规则见 [医疗卫生题库知识库](../../docs/data/medical-question-bank.md)；具体重建命令、清单更新与故障处理见 [题库导入、重建与验收](../../docs/ops/question-bank-maintenance.md)。

### 医疗卫生分值口径

- `questionScore` 是题目内容部分的上限，不能假定所有题都是 95 分。
- `appearanceScore` / `appearanceScoreMax` 是正式仪态分；无可执行标准时医疗 profile 默认 5 分。
- `effectiveFullScore` 是有效题目满分；`appearanceScoreScope=suite` 时，仪态分只能在套题合计中计入一次。
- 默认仪态分不是解析失败、分值冲突或待确认理由；未来真实仪态分必须替换默认值，不能重复相加。

## 恢复示例

```bash
cd /home/quyu/kaogong_ai
cp '/home/quyu/doc_kaogong/question-bank/source/2017-2025江苏事业单位真题题库.docx' .
sha256sum -c data/question-bank/checksums.sha256 --ignore-missing
```

## 运行资产不迁移

`ai_gongwu_backend/assets/questions/` 中的题库 JSON 仍留在仓库，因为后端题库同步、全真模拟、定向备面和回归测试都依赖它。
