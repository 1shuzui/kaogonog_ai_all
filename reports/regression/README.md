# 回归报告目录

本目录只保留最近关键回归结果。旧回归报告已迁到 `/home/quyu/doc_kaogong/reports/archive/regression/`，完整迁移记录见 `/home/quyu/doc_kaogong/manifests/migration-moved-checksums.tsv`。

## 当前保留

| 文件 | 说明 |
| --- | --- |
| `jiangsu_targeted_final_high_errors/llm_regression_20260514_200908.json` | 江苏定向高分异常样本回归 JSON。 |
| `jiangsu_targeted_final_high_errors/llm_regression_20260514_200908.md` | 江苏定向高分异常样本回归摘要。 |
| `jiangsu_targeted_final_low_v2/llm_regression_20260514_200323.md` | 江苏定向低分样本回归摘要。 |
| `medical_targeted/regression_20260821_231101.json` | 医疗卫生定向题库接入后的确定性回归 JSON。 |
| `medical_targeted/regression_20260821_231101.md` | 医疗卫生定向题库接入后的确定性回归摘要。 |
| `medical_targeted_after_appearance/regression_20260821_234257.json` | 仪态分独立处理后的医疗卫生回归 JSON。 |
| `medical_targeted_after_appearance/regression_20260821_234257.md` | 仪态分独立处理后的医疗卫生回归摘要。 |

## 常用脚本

```bash
cd /home/quyu/kaogong_ai/ai_gongwu_backend
../.venv/bin/python scripts/run_regression.py
../.venv/bin/python scripts/run_llm_regression.py --repeat 3
```

## 使用原则

- 调整评分逻辑后，先跑小范围 `--question-id`。
- 真实 LLM 回归成本更高，默认不要全量无筛选运行。
- 旧报告需要追溯时，从外部归档恢复，不直接在仓库堆积历史批次。
