import json


def build_prompt(answer, question_data):
    """
    构建评分 Prompt
    """
    # 提取维度信息
    dims = question_data.get('dimensions', [])
    dim_lines = []
    criteria_lines = []

    for i, dim in enumerate(dims):
        name = dim.get('name', f'维度{i + 1}')
        max_score = dim.get('score', 0)
        dim_lines.append(f"{i + 1}. {name}（{max_score}分）")

        # 获取对应的评分标准描述（如果没有详细标准，使用通用描述）
        criteria = question_data.get('scoringCriteria', [])
        if i < len(criteria):
            criteria_lines.append(f"- {name}: {criteria[i]}")
        else:
            criteria_lines.append(f"- {name}: 观点明确，逻辑清晰，结合省情。")

    # 关键词列表格式化
    def fmt_list(lst):
        return "、".join(lst) if lst else "无"

    core_kw = fmt_list(question_data.get('coreKeywords', []))
    penalty_kw = fmt_list(question_data.get('penaltyKeywords', []))
    bonus_kw = fmt_list(question_data.get('bonusKeywords', []))

    prompt = f"""
你是一位资深的公务员面试考官（特别是河南省直机关遴选），现需对一道面试题进行严格评分。
请仔细阅读【题目】、【评分标准】和【关键词规则】，对【考生答案】进行客观评价。

【题目信息】
题干：{question_data.get('question', '')}
题型：{question_data.get('type', '综合分析')}
满分：{question_data.get('fullScore', 30)}

【评分维度及标准】
{chr(10).join(dim_lines)}
具体标准：
{chr(10).join(criteria_lines)}

【关键词评分规则】
1. 核心采分点（必须涵盖）：{core_kw}
   - 缺失核心点将严重影响“现象解读”和“科学决策”维度得分。
2. 扣分陷阱（出现即扣分，每处扣 1.5-2 分）：{penalty_kw}
   - 如出现“一刀切”、“形式主义”等负面描述且未批判，或考生答案本身体现了这些错误思维，需扣分。
   - 注意：如果考生是在批判这些现象，则不扣分。请根据语境判断。
3. 加分亮点（出现可加 1-2 分）：{bonus_kw}

【考生答案】
{answer}

【输出要求】
请仅输出一个标准的 JSON 对象，不要包含任何 Markdown 标记（如 ```json）或其他解释性文字。JSON 结构如下：
{{
    "dimension_scores": {{
        "{dims[0]['name'] if dims else '维度1'}": 整数,
        "{dims[1]['name'] if len(dims) > 1 else '维度2'}": 整数,
        "{dims[2]['name'] if len(dims) > 2 else '维度3'}": 整数,
        "{dims[3]['name'] if len(dims) > 3 else '维度4'}": 整数,
        "{dims[4]['name'] if len(dims) > 4 else '维度5'}": 整数
    }},
    "matched_keywords": {{
        "core": ["命中的核心词"],
        "penalty": ["命中的扣分词（仅限考生答案体现错误观点时）"],
        "bonus": ["命中的加分词"]
    }},
    "deduction_details": ["扣分原因简述"],
    "rationale": "简短的评分理由，指出主要优缺点",
    "total_score": 整数总分
}}

注意：
1. 总分 = 各维度分数之和。
2. 扣分项已在维度打分中体现，无需在总分中重复扣除，但需在 deduction_details 中说明。
3. 确保所有分数为整数，且不超过该维度满分。
"""
    return prompt