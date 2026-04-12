# 题库目录说明

这个目录用于存放“按题目拆分”的 JSON 配置文件。

推荐约定：

1. 一个题目一个 JSON 文件。
2. 文件名优先使用 `question_id.json`。
3. 每个文件除了题目本身，还可以写：
   - `scoreBands`：分档配置
   - `regressionCases`：回归样本配置
   - `sourceDocument`：原始题库文档名
   - `referenceAnswer`：题库中的高分基准答案
   - `tags`：检索标签 / 题目标签

这样后续新增题目时，不需要再去改一份巨大的总表，
只需要在这里新增一个 JSON 文件即可。

当前目录下的 `generated_hunan/` 是脚本自动生成的湖南题库，
对应样本文件位于 `assets/regression_samples/generated_hunan/`。
