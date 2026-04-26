# 回归样本目录说明

这个目录用于存放批量回归脚本实际读取的样本文本。

## 目录结构

当前主要使用：

1. `generated_hunan/`

目录形式为：

```text
assets/regression_samples/
└── generated_hunan/
    └── <question_id>/
        ├── reference_high.txt
        ├── reference_mid.txt
        └── reference_low.txt
```

每个题目一个目录，每个目录默认三份文本。

## 三档样本含义

1. `reference_high.txt`
   当前题目的高分基准答案，通常来自题库文档原始参考答案或清洗后的高质量版本。
2. `reference_mid.txt`
   当前题目的中档参考答案，通常由模板或程序规则生成，用来验证系统能否把“基本合格但不突出”的答案识别到中间分段。
3. `reference_low.txt`
   当前题目的低档参考答案，用来验证系统是否能识别明显泛化、口语化、结构弱或细节不足的答案。

## 和题目 JSON 的关系

题目 JSON 中的 `regressionCases` 会引用这里的文件路径。

也就是说：

1. 回归脚本不是扫这个目录自动猜题
2. 而是先读取题目 JSON
3. 再根据 `regressionCases[*].sample_path` 找到这里的文本

## generated_hunan 的维护方式

`generated_hunan/` 是由下面脚本自动生成的：

```bash
cd /home/quyu/ai_interview/ai_gongwu_backend
./venv/bin/python scripts/import_hunan_question_bank.py
```

因此：

1. 不建议手工逐个改 `generated_hunan` 下的样本文本
2. 如果你想批量调整样本风格、长度或题型模板，应修改导入脚本后重新生成
3. 手工逐个修改很容易和下一次导入结果冲突

## 当前状态

截至 2026-04-11：

1. `generated_hunan/` 共 `29` 个题目样本目录
2. 每题默认配套高 / 中 / 低三档文本
3. 这些样本已经用于：
   - `scripts/run_regression.py`
   - `scripts/run_llm_regression.py`

## 使用建议

1. 做规则回归时，先看中低档样本是否真的像“真实口述答案”，而不是只像删减稿
2. 做 LLM 标定时，建议固定 `--repeat 3`
3. 如果某题三档样本都不合理，优先回头修样本生成器，不要只在评分端硬调分数
