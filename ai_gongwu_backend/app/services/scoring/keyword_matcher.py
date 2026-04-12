"""关键词匹配模块。

它不是评分主引擎，而是一个“轻量确定性补充”：
模型可能会漏掉一些明显关键词，
所以系统自己再做一次简单匹配，作为辅助信息返回。
"""

from typing import Any, Dict, List


def _normalize_text(value: str) -> str:
    """做最基础的文本归一化。

    当前仅处理两件事：
    1. 转小写
    2. 去掉空白字符

    对中文场景来说，这样已经能覆盖很多简单匹配需求。
    """

    return "".join(value.lower().split())


def keyword_match(text: str, keywords: List[str]) -> List[str]:
    """返回文本中实际命中的关键词列表。

    这里使用的是非常直接的“子串包含”策略，
    优点是简单、快、可解释。
    缺点是没有语义理解能力，所以它只能做辅助，不能完全替代 LLM。
    """

    normalized_text = _normalize_text(text)
    matched: List[str] = []
    seen = set()

    for keyword in keywords:
        normalized_keyword = _normalize_text(keyword)
        if not normalized_keyword or normalized_keyword in seen:
            continue
        if normalized_keyword in normalized_text:
            matched.append(keyword)
            seen.add(normalized_keyword)

    return matched


def match_all_categories(text: str, question_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """一次性匹配多个关键词分类。"""

    categories = {
        "core": question_data.get("coreKeywords", []),
        "strong": question_data.get("strongKeywords", []),
        "weak": question_data.get("weakKeywords", []),
        "bonus": question_data.get("bonusKeywords", []),
    }
    return {category: keyword_match(text, keywords) for category, keywords in categories.items()}
