from keyword_matcher import match_all_categories


def post_process(llm_result, answer, question_data):
    """
    后处理：
    1. 融合本地关键词匹配结果（防止 LLM 漏判）
    2. 校验分数逻辑
    3. 格式化输出
    """
    # 1. 本地关键词匹配
    local_matches = match_all_categories(answer, question_data)

    # 初始化结果中的 matched_keywords
    if 'matched_keywords' not in llm_result:
        llm_result['matched_keywords'] = {}

    # 合并关键词（取并集，以本地匹配为准补充 LLM 可能遗漏的硬性关键词）
    # 注意：penalty 需要谨慎，LLM 能判断语境（是否在批判），本地匹配只能判断出现
    # 这里策略：Core/Bonus 直接合并；Penalty 仅在 LLM 也判定时确认，或强制提示
    for cat in ['core', 'bonus']:
        llm_key = 'core' if cat == 'core' else ('bonus' if cat == 'bonus' else cat)
        # 映射本地类别到结果类别
        local_key_map = {
            'coreKeywords': 'core',
            'strongKeywords': 'core',  # 归为核心
            'weakKeywords': 'core',
            'bonusKeywords': 'bonus',
            'penaltyKeywords': 'penalty'
        }

        target_key = local_key_map.get([k for k, v in local_key_map.items() if v == llm_key][0], None)
        if target_key and target_key in local_matches:
            existing = llm_result['matched_keywords'].get(llm_key, [])
            combined = list(set(existing + local_matches[target_key]))
            llm_result['matched_keywords'][llm_key] = combined

    # 2. 分数校验
    dim_scores = llm_result.get('dimension_scores', {})
    calculated_total = sum(dim_scores.values())
    reported_total = llm_result.get('total_score', 0)

    # 如果差异过大，以维度累加为准（或者记录警告）
    if abs(calculated_total - reported_total) > 1:
        print(f"[WARN] LLM total ({reported_total}) != dimension sum ({calculated_total}), corrected.")
        llm_result['total_score'] = calculated_total

    # 限制总分不超过满分
    full_score = question_data.get('fullScore', 30)
    if llm_result['total_score'] > full_score:
        llm_result['total_score'] = full_score

    # 3. 补充扣分详情（如果 LLM 没写但匹配到了扣分词）
    # 注意：这里假设匹配到的扣分词都是负面的，实际可能需要人工复核语境
    penalty_matched = local_matches.get('penaltyKeywords', [])
    if penalty_matched and not llm_result.get('deduction_details'):
        llm_result['deduction_details'] = [f"检测到潜在扣分表述：{', '.join(penalty_matched)}"]

    return llm_result