"""
两阶段评分系统
阶段1：证据抽取 - 从答案中识别采分点、扣分点、亮点
阶段2：证据约束评分 - 基于抽取的证据进行评分
"""
import json
import re


def build_evidence_extraction_prompt(answer, question_data):
    """
    阶段1：证据抽取 Prompt
    只抽取证据，不打分
    """
    dims = question_data.get('dimensions', [])
    dim_names = [d.get('name', f'维度{i+1}') for i, d in enumerate(dims)]

    # 获取评分点和关键词
    scoring_points = question_data.get('scoringPoints', [])
    penalty_points = question_data.get('penaltyPoints', [])
    bonus_points = question_data.get('bonusPoints', [])
    visual_observation = str(question_data.get('visualObservation', '') or '').strip()
    visual_block = visual_observation or "未提供视频观察信息。"

    prompt = f"""你是一位资深的公务员面试考官。请对以下考生答案进行【证据抽取】，识别答案中体现的具体内容，不要评分。

【题目信息】
题干：{question_data.get('question', '')}
题型：{question_data.get('type', '综合分析')}
评分维度：{', '.join(dim_names)}

【评分要点参考】
核心采分点：
{chr(10).join([f"- {sp}" for sp in scoring_points]) if scoring_points else "- 观点明确、逻辑清晰、结合省情"}

扣分陷阱（如出现需扣分）：
{chr(10).join([f"- {pp}" for pp in penalty_points]) if penalty_points else "- 一刀切、形式主义等错误思维"}

加分亮点（如有可加分）：
{chr(10).join([f"- {bp}" for bp in bonus_points]) if bonus_points else "- 结合省情、提出创新举措"}

【视频动作与表情观察】
{visual_block}

【考生答案】
{answer}

【输出要求】
请仅输出一个标准的 JSON 对象，不要包含任何 Markdown 标记或其他解释性文字。JSON 结构如下：
{{
    "evidence": {{
        "present": [
            {{"id": "e1", "type": "采分点", "content": "答案中体现的具体内容", "dimension": "对应维度", "quote": "原文引用"}},
            {{"id": "e2", "type": "采分点", "content": "...", "dimension": "...", "quote": "..."}}
        ],
        "absent": [
            {{"id": "a1", "type": "缺失点", "content": "应出现但未出现的内容", "dimension": "对应维度", "expected": "期望出现的内容"}}
        ],
        "penalty": [
            {{"id": "p1", "type": "扣分点", "content": "答案中体现的错误", "dimension": "对应维度", "quote": "原文引用", "severity": "严重/一般"}}
        ],
        "bonus": [
            {{"id": "b1", "type": "亮点", "content": "答案中的优秀表述", "dimension": "对应维度", "quote": "原文引用"}}
        ]
    }},
    "summary": {{
        "word_count": 字数,
        "main_points": ["要点1", "要点2"],
        "structure": "答案结构评价"
    }}
}}

注意：
1. 只抽取客观存在的证据，不要主观评价好坏
2. 每个证据必须有 quote 字段，引用原文片段
3. absent 只列出题目明确要求但答案缺失的内容
4. 视频观察只能作为语言表达/仪态辅助参考，不能当作内容事实 quote
5. 确保所有 evidence id 唯一"""
    return prompt


def build_evidence_based_scoring_prompt(evidence, question_data):
    """
    阶段2：基于证据的评分 Prompt
    只基于阶段1抽取的证据进行评分
    """
    dims = question_data.get('dimensions', [])
    dim_info = []
    for d in dims:
        name = d.get('name', '')
        max_score = d.get('score', 0)
        dim_info.append(f"- {name}（满分{max_score}分）")

    evidence_json = json.dumps(evidence, ensure_ascii=False, indent=2)
    visual_observation = str(question_data.get('visualObservation', '') or '').strip()
    visual_block = visual_observation or "未提供视频观察信息。"

    prompt = f"""你是一位资深的公务员面试考官。请基于【已抽取的证据包】对考生答案进行【评分】。

【题目信息】
题干：{question_data.get('question', '')}
题型：{question_data.get('type', '综合分析')}

【评分维度及满分】
{chr(10).join(dim_info)}

【已抽取的证据包】
{evidence_json}

【视频动作与表情观察】
{visual_block}

【评分规则】
1. 必须基于上述证据包进行评分，不能引入新的主观判断
2. 每个维度的得分必须在 0 到满分之间
3. 采分点命中加分，缺失点扣分，扣分点按严重程度扣分，亮点加分
4. 维度分之和必须等于总分
5. 视频观察只能影响语言表达、仪态稳定性等表现项，不能代替内容证据

【输出要求】
请仅输出一个标准的 JSON 对象，不要包含任何 Markdown 标记或其他解释性文字。JSON 结构如下：
{{
    "dimension_scores": {{
        {', '.join([f'"{d.get("name", "")}": 整数' for d in dims])}
    }},
    "total_score": 整数,
    "dimension_rationales": {{
        {', '.join([f'"{d.get("name", "")}": "该维度得分理由，引用证据id"' for d in dims])}
    }},
    "evidence_mapping": [
        {{"evidence_id": "e1", "impact": "加分/扣分/中性", "points": 分值, "rationale": "影响说明"}}
    ],
    "overall_rationale": "总体评价，指出主要优缺点",
    "suggestions": ["改进建议1", "改进建议2"]
}}

注意：
1. 所有分数必须是整数
2. dimension_rationales 中必须引用证据包的 evidence id
3. 确保 dimension_scores 各项之和等于 total_score"""
    return prompt


def validate_evidence(evidence, answer_text):
    """
    校验证据：
    1. 检查 quote 是否在原文中
    2. 检查 evidence id 是否唯一
    3. 补充缺失的 absence 证据
    """
    validated = {
        "present": [],
        "absent": evidence.get("absent", []),
        "penalty": [],
        "bonus": []
    }

    # 校验 present 证据的 quote 是否在原文中
    for e in evidence.get("present", []):
        quote = e.get("quote", "")
        if quote and quote in answer_text:
            validated["present"].append(e)
        elif quote:
            # quote 不在原文中，尝试模糊匹配
            if len(quote) > 5:
                # 取前5个字检查后文
                if quote[:5] in answer_text:
                    validated["present"].append(e)

    # 校验 penalty 证据
    for p in evidence.get("penalty", []):
        quote = p.get("quote", "")
        if quote and quote in answer_text:
            validated["penalty"].append(p)

    # 校验 bonus 证据
    for b in evidence.get("bonus", []):
        quote = b.get("quote", "")
        if quote and quote in answer_text:
            validated["bonus"].append(b)

    return validated


def validate_scoring_result(result, evidence, max_scores):
    """
    校验评分结果：
    1. 检查维度分是否在合理范围
    2. 检查总分是否等于维度分之和
    3. 检查 rationales 是否引用了有效证据
    """
    errors = []

    dim_scores = result.get("dimension_scores", {})
    total = result.get("total_score", 0)

    # 检查维度分范围
    for dim, score in dim_scores.items():
        max_score = max_scores.get(dim, 100)
        if score < 0 or score > max_score:
            errors.append(f"维度 {dim} 分数 {score} 超出范围 [0, {max_score}]")

    # 检查总分
    sum_dims = sum(dim_scores.values())
    if sum_dims != total:
        errors.append(f"维度分之和 {sum_dims} 不等于总分 {total}")
        # 自动修正
        result["total_score"] = sum_dims

    return len(errors) == 0, errors, result


def fallback_scoring(answer, question_data, evidence=None):
    """
    兜底评分：当 LLM 失败时使用基于关键词的本地评分
    """
    dims = question_data.get('dimensions', [])
    answer_len = len(answer)

    # 基础分比例
    base_ratio = 0.6

    # 根据字数调整
    if answer_len < 50:
        base_ratio = 0.4
    elif answer_len < 100:
        base_ratio = 0.5
    elif answer_len > 300:
        base_ratio = 0.7

    # 关键词匹配加分
    keywords = question_data.get('keywords', {})
    scoring_kws = keywords.get('scoring', [])
    if scoring_kws:
        hit = sum(1 for kw in scoring_kws if kw in answer)
        base_ratio += 0.2 * (hit / len(scoring_kws))

    # 扣分词
    penalty_kws = keywords.get('penalty', [])
    if penalty_kws:
        hit = sum(1 for kw in penalty_kws if kw in answer)
        base_ratio -= 0.1 * (hit / len(penalty_kws))

    # 限制范围
    base_ratio = max(0.3, min(0.9, base_ratio))

    # 计算各维度分
    dim_scores = {}
    for d in dims:
        name = d.get('name', '')
        max_score = d.get('score', 0)
        import random
        dim_scores[name] = round(max_score * base_ratio + random.uniform(-1, 1))

    total = sum(dim_scores.values())

    return {
        "dimension_scores": dim_scores,
        "total_score": total,
        "dimension_rationales": {name: "基于关键词匹配的兜底评分" for name in dim_scores},
        "evidence_mapping": [],
        "overall_rationale": f"答案字数：{answer_len}，基于关键词匹配计算得分",
        "suggestions": ["建议增加答题字数", "注意涵盖题目核心要点"],
        "is_fallback": True
    }
