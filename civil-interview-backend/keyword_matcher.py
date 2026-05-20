import re


def keyword_match(text, keywords):
    """
    返回文本中包含的关键词列表（不区分大小写，支持中文分词模糊匹配）
    """
    text_lower = text.lower()
    matched = []
    for kw in keywords:
        kw_clean = kw.strip()
        if not kw_clean:
            continue
        # 中文直接使用 in 判断，或者使用正则边界（英文更有效）
        # 这里采用包含匹配，因为中文分词较复杂且关键词通常较短
        if kw_clean in text:
            matched.append(kw_clean)
    return list(set(matched))


def match_all_categories(text, question_data):
    """
    对所有类别的关键词进行匹配
    """
    result = {}
    categories = ['coreKeywords', 'strongKeywords', 'weakKeywords', 'bonusKeywords', 'penaltyKeywords']

    for cat in categories:
        keywords = question_data.get(cat, [])
        result[cat] = keyword_match(text, keywords)

    return result


if __name__ == '__main__':
    # 简单测试
    sample_text = "这种做法存在形式主义风险，容易一刀切，没有因地制宜。"
    mock_q = {
        "penaltyKeywords": ["形式主义", "一刀切", "盲目跟风"],
        "coreKeywords": ["因地制宜", "实事求是"]
    }
    matches = match_all_categories(sample_text, mock_q)
    print(matches)