# 题库导入、重建与验收运行手册

## 适用范围

本手册用于维护外置题源、题库导入器、生成 JSON、回归样本和题源清单。医疗卫生三批的领域规则见 [医疗卫生题库知识库](../data/medical-question-bank.md)。

核心原则：原始 DOC/DOCX 是外部可追溯输入，generated_* JSON 是仓库内运行资产。不要以手改生成文件替代可重复导入。

以下 Python 示例假设已经激活项目虚拟环境；在当前 WSL 默认 shell 中，请把 **python** 替换为 **.venv/bin/python**。

## 新题源的安全流程

### 1. 固定输入

1. 保留用户桌面或交付目录的原始文件；
2. 复制到 /home/quyu/doc_kaogong/question-bank/source/<profile>/；
3. 不移动、不删除原件，不把 DOC/DOCX 加入 Git；
4. 先按稳定文件名统计文件数量，再开始解析。

医疗卫生已有归档：

| Profile | 外部目录 | 预期 |
| --- | --- | --- |
| medical_general | /home/quyu/doc_kaogong/question-bank/source/medical_general | 1 文件，100 题 |
| shandong_medical | /home/quyu/doc_kaogong/question-bank/source/shandong_medical | 137 文件，259 题 |
| jiangsu_medical | /home/quyu/doc_kaogong/question-bank/source/jiangsu_medical | 70 实际文件，187 题；江苏新套03 缺失已记录 |

### 2. 更新清单与校验和

医疗卫生题源文件变化后，从仓库根目录执行：

~~~bash
python scripts/update_question_bank_manifest.py
sha256sum -c data/question-bank/checksums.sha256 --ignore-missing
~~~

该脚本只扫描预定义的三批医疗目录，更新 inventory.json 与 checksums.sha256；不会移动、删除或修改任何源文件。若新增的是其他地区，不要误用它覆盖该地区的清单规则，应按相同数据模型扩展清单工具或做专门的可审计脚本。

### 3. 重建生成资产

医疗 profile 可以直接读取 DOCX XML，因此推荐通过 source-dir 传入外部归档目录。可重复传入多个 source-dir；目录和文件都会按稳定文件名排序。

~~~bash
cd /home/quyu/kaogong_ai
python ai_gongwu_backend/scripts/import_question_bank.py \
  --profile-name medical_general \
  --source-dir /home/quyu/doc_kaogong/question-bank/source/medical_general

python ai_gongwu_backend/scripts/import_question_bank.py \
  --profile-name shandong_medical \
  --source-dir /home/quyu/doc_kaogong/question-bank/source/shandong_medical

python ai_gongwu_backend/scripts/import_question_bank.py \
  --profile-name jiangsu_medical \
  --source-dir /home/quyu/doc_kaogong/question-bank/source/jiangsu_medical
~~~

同一个内置 profile 也可使用 **--profile**。**--source-file** 仍可重复传入，适合单个 .docx、.doc 或 .extracted.txt；legacy .doc 需要相邻的 .extracted.txt 兜底文件。

输出目录是：

| Profile | 题库 JSON | 回归样本 |
| --- | --- | --- |
| medical_general | ai_gongwu_backend/assets/questions/generated_medical_general | ai_gongwu_backend/assets/regression_samples/generated_medical_general |
| shandong_medical | ai_gongwu_backend/assets/questions/generated_shandong_medical | ai_gongwu_backend/assets/regression_samples/generated_shandong_medical |
| jiangsu_medical | ai_gongwu_backend/assets/questions/generated_jiangsu_medical | ai_gongwu_backend/assets/regression_samples/generated_jiangsu_medical |

不要覆盖 generated_shandong、generated_jiangsu_shiye 或任何旧题库输出目录。

### 4. 验收生成结果

导入器遇到硬解析失败会停止写入完整题库。成功后仍需验证：

~~~bash
cd /home/quyu/kaogong_ai
PYTHONPATH=ai_gongwu_backend .venv/bin/python -m pytest -q \
  ai_gongwu_backend/tests/test_medical_question_bank.py

cd civil-interview-backend
pytest -q tests/test_medical_question_bank_assets.py \
  tests/test_scoring_appearance_score.py
~~~

最低验收条件：

| 项目 | 要求 |
| --- | --- |
| 数量 | 通用 100/100，山东 259/259 且 137/137 文件有题，江苏 187/187 且 70/70 实际文件有题。 |
| ID | 所有新题 ID 全局唯一；山东/江苏按稳定 SET 规则生成。 |
| 套题 | 山东/江苏每套题号从 1 连续；JS 039 为 3 题、JS 045 为 2 题、无 JS 003。 |
| 分类 | 三批都为 事业单位考试；医疗卫生面试只作为门户标签。 |
| 分值 | 有 appearanceScore、appearanceScoreMax、source、scope；默认仪态分不会变成待确认或冲突。 |
| 套题展示 | 通用批次不进正式套题；山东/江苏符合完整资格的源文件套题可返回。 |

### 5. 后端同步与接口验证

后端启动生命周期会幂等同步仓库内题库 JSON。对题库服务或资产结构有改动时，还应运行：

~~~bash
cd /home/quyu/kaogong_ai/civil-interview-backend
pytest -q

cd /home/quyu/kaogong_ai
.venv/bin/python scripts/validate_project_docs.py
git diff --check
~~~

对于真实 LLM 回归，先使用确定性回归作为前置；真实模型回归须显式记录模型、时间、样本和是否写回标定，不能把一次不稳定远程结果当作解析失败。

## 故障分类与处理

| 症状 | 首先检查 | 处理原则 |
| --- | --- | --- |
| source-dir 找不到文件 | 外部目录、扩展名、权限 | 目录仅接受 .docx、.doc、.extracted.txt；不要把临时文件混入。 |
| legacy .doc 无法读取 | 同名 .extracted.txt | 先用提取脚本生成兜底文本。 |
| 题号或题数不足 | 源文本、裸题头、卷首汇总行、特殊布局 | 修通用解析器并重建，不手补 JSON。 |
| 采分点缺失 | 得分标准标签与新格式 | 先补通用标准化和采分点规则。 |
| 95+5 被标为问题 | appearanceScoreScope 与 scoreCalculationNote | 这是合法结构，检查是否有旧的总分反推逻辑残留。 |
| 同题干题被覆盖 | stable source ID 同步逻辑 | 医疗资产必须按 ID 更新，不可按题干合并。 |
| 通用 100 题出现在全真列表 | hasCompleteSuiteLevel | 应为 false；检查同步出的 keywords._meta。 |
| 江苏 03 报解析失败 | inventory sourceBatches | 它是显式缺失输入，不应计入失败。 |

## 文档与变更检查

题库流程、字段、接口或验收口径变化时，同步更新：

1. data/question-bank/README.md；
2. docs/data/medical-question-bank.md；
3. docs/api/question-bank-and-suites.md；
4. docs/api/scoring.md（如涉及分数）；
5. docs/decisions/ADR-005-medical-question-bank-and-appearance-score.md（如改变长期决策）；
6. AI 项目知识库入口与 docs/README.md。

结束前运行 scripts/validate_project_docs.py、git diff --check 和项目要求的变更检测。生成资产、题源清单和测试结果应同时提交；原始题源不提交。
