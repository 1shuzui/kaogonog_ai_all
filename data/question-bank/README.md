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

## 恢复示例

```bash
cd /home/quyu/kaogong_ai
cp '/home/quyu/doc_kaogong/question-bank/source/2017-2025江苏事业单位真题题库.docx' .
sha256sum -c data/question-bank/checksums.sha256 --ignore-missing
```

## 运行资产不迁移

`ai_gongwu_backend/assets/questions/` 中的题库 JSON 仍留在仓库，因为后端题库同步、全真模拟、定向备面和回归测试都依赖它。
