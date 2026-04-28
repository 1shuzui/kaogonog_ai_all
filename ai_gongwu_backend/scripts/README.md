# scripts 使用说明

本目录下的脚本分成两类：

1. 题库导入与生成
2. 回归与标定

以后维护时，优先改这里的通用脚本，不要为每个地区继续复制一份新的大脚本。

## 1. 脚本总览

| 脚本 | 作用 | 什么时候用 |
| --- | --- | --- |
| `extract_docx_text.py` | 把 `.docx` 提取成逐段换行的 `.extracted.txt` | 新拿到 Word 题库原文时先跑它 |
| `import_question_bank.py` | 通用题库导入器，负责把 `.extracted.txt` 转成题库 JSON + 回归样本 | 湖南、安徽，以及未来新增地区都优先用它 |
| `import_hunan_question_bank.py` | 湖南兼容入口，内部实际调用 `import_question_bank.py` | 老命令兼容、已有文档/习惯不想改时 |
| `import_anhui_question_bank.py` | 安徽兼容入口，内部实际调用 `import_question_bank.py` | 想直接导安徽时 |
| `run_regression.py` | 跑确定性回归，检查题库样本是否落在预期分档 | 改了题库、样本、评分规则后先跑它 |
| `run_llm_regression.py` | 强制走真实 LLM 评分链路，可做回归和写回标定区间 | 要验证真实模型漂移，或更新 `llmExpectedMin/Max` 时 |

## 2. 推荐使用顺序

如果你拿到的是新的地区 Word 题库，推荐固定按下面顺序做：

```bash
cd ai_gongwu_backend
python scripts/extract_docx_text.py ../某地区题库.docx
python scripts/import_question_bank.py --profile-name 某地区英文名 --province 某地区中文名 --source-file ../某地区题库.extracted.txt
python scripts/run_regression.py
```

例如以后导入广东题库：

```bash
cd ai_gongwu_backend
python scripts/extract_docx_text.py ../广东-2025完全版.docx
python scripts/import_question_bank.py --profile-name guangdong --province 广东 --source-file ../广东-2025完全版.extracted.txt
```

执行后默认会生成：

1. `assets/questions/generated_guangdong/`
2. `assets/regression_samples/generated_guangdong/`
3. `assets/questions/generated_guangdong/import_summary.txt`

## 3. 通用导入器怎么用

### 3.1 使用内置地区 profile

先看当前内置 profile：

```bash
python scripts/import_question_bank.py --list-profiles
```

导入内置 profile：

```bash
python scripts/import_question_bank.py --profile hunan
python scripts/import_question_bank.py --profile anhui
```

### 3.2 使用临时自定义地区 profile

如果是未来新增地区，优先不要新建 `import_xxx_question_bank.py`，直接用：

```bash
python scripts/import_question_bank.py \
  --profile-name guangdong \
  --province 广东 \
  --source-file ../广东-2025完全版.extracted.txt
```

如果一个地区有多个源文件，也可以重复传：

```bash
python scripts/import_question_bank.py \
  --profile-name guangdong \
  --province 广东 \
  --source-file ../广东-2025-A.extracted.txt \
  --source-file ../广东-2025-B.extracted.txt
```

说明：

1. `--profile-name` 决定输出目录名里的 `generated_<profile-name>`
2. `--province` 是默认省份字段，落到题目 JSON 的 `province`
3. `--source-file` 传 `.extracted.txt`，不是 `.docx`
4. 如果同题号在多个源文件里重复，越靠前传入的 `--source-file` 优先级越高

## 4. 以后新增地区时，优先改哪里

如果新地区格式和安徽/湖南接近，通常不需要新脚本，只需要：

1. 先提取 `.docx`
2. 直接跑 `import_question_bank.py --profile-name ...`
3. 看是否导入成功
4. 如果失败，再补通用解析规则

优先修改 [import_question_bank.py](D:/8/1/kaogong_ai/kaogong_ai/ai_gongwu_backend/scripts/import_question_bank.py) 里的这些位置：

1. `SECTION_HEADERS`
   作用：补 section 标题别名，例如“核心观点”“核心采分基准”“总分计算规则”这些变体
2. `normalize_source_text()`
   作用：修“标题被拆行”“标题和正文粘连”“中文序号标题”等源文本脏格式
3. `canonical_section_name()`
   作用：把不同写法归并到统一 section 名
4. `FIELD_PATTERNS`
   作用：补“适用地区”“适用省份”“题型信息”等字段提取规则
5. `detect_template_family()`
   作用：把新题型映射到现有 `analysis / organization / interpersonal / scene`
6. `build_tags()`
   作用：清洗新地区题库里混入的卷首说明、标题噪声、格式垃圾

结论：

1. 以后新增地区，优先改通用导入器
2. 不要先复制 `import_hunan_question_bank.py` 再改成 `import_guangdong_question_bank.py`
3. 只有当某个地区长期稳定、团队里又确实想保留短命令时，才考虑加一个很薄的 wrapper

## 5. 什么时候才需要新增内置 profile

只有下面两种情况，才建议把某地区正式写进 `IMPORT_PROFILES`：

1. 这个地区会被反复重跑，已经不是一次性导入
2. 这个地区有固定源文件、固定输出目录、固定优先级规则

做法：

1. 在 `import_question_bank.py` 的 `IMPORT_PROFILES` 里新增一项
2. 设定：
   - `name`
   - `default_province`
   - `question_output_dir`
   - `sample_output_dir`
   - `summary_path`
   - `regression_sample_base_path`
   - `source_files`
   - `source_priority`
3. 如有必要，再补一个兼容 wrapper，例如 `import_guangdong_question_bank.py`

但注意：wrapper 只是便捷入口，不应该再承载地区特有解析逻辑。

## 6. 维护原则

### 6.1 生成产物不要手改

以下目录都是脚本产物，尽量不要逐个手工改：

1. `assets/questions/generated_hunan/`
2. `assets/questions/generated_anhui/`
3. `assets/questions/generated_<其他地区>/`
4. `assets/regression_samples/generated_*/`

正确姿势是：

1. 改源文档或提取文本
2. 改通用导入逻辑
3. 重新执行导入
4. 再跑回归验证

### 6.2 新地区解析失败时的排查顺序

先按这个顺序看：

1. `.docx -> .extracted.txt` 是否正确
2. `题号` 是否被识别
3. section 标题是否被正确切开
4. `referenceAnswer / 得分标准 / tags / province` 是否成功提取
5. 中低档样本是否成功生成

如果报错出在“未能生成足够的中低档候选样本”，优先检查：

1. `detect_template_family()` 有没有识别到合适题型
2. 新题型是否应该复用已有模板家族
3. 是否只是候选被长度门槛或噪声过滤过严拦掉了

## 7. 回归脚本说明

### 7.1 `run_regression.py`

用途：

1. 跑题库里的 `regressionCases`
2. 使用确定性评分链路
3. 输出 `reports/regression/` 下的 JSON / Markdown 报表

常用命令：

```bash
python scripts/run_regression.py
python scripts/run_regression.py --question-id AHGWY-20201113PM-01
```

### 7.2 `run_llm_regression.py`

用途：

1. 强制走真实 LLM
2. 观察模型漂移
3. 可选把推荐区间写回题库

常用命令：

```bash
python scripts/run_llm_regression.py --question-id AHGWY-20201113PM-01 --repeat 3
python scripts/run_llm_regression.py --sample-level high --repeat 3
```

## 8. 当前建议

从现在开始，地区题库导入统一遵循下面原则：

1. 优先用 `import_question_bank.py`
2. `import_hunan_question_bank.py` / `import_anhui_question_bank.py` 只保留兼容
3. 未来新增地区优先走 `--profile-name + --province + --source-file`
4. 真正需要长期固定维护时，再升级成内置 profile
