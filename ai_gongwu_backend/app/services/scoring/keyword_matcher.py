"""
这个文件负责关键词匹配；题型分类和采分点命中都依赖它保持同一套文本规则。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
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
    """
    返回文本中实际命中的关键词列表。 这里使用的是非常直接的“子串包含”策略， 优点是简单、快、可解释。 缺点是没有语义理解能力，所以它只能做辅助，不能完全替代 LLM。

    评分子模块封装关键词、分值和提示词策略，注释用于区分题型分类与能力维度。

    @param text: 待处理文本；通常来自题干、转写或导入文档，需保留原始语义以便复核。
    @param keywords: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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
    """
    一次性匹配多个关键词分类。

    评分子模块封装关键词、分值和提示词策略，注释用于区分题型分类与能力维度。

    @param text: 待处理文本；通常来自题干、转写或导入文档，需保留原始语义以便复核。
    @param question_data: 题目相关数据；真实题源、题型分类和能力维度需要分开处理。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    categories = {
        "core": question_data.get("coreKeywords", []),
        "strong": question_data.get("strongKeywords", []),
        "weak": question_data.get("weakKeywords", []),
        "bonus": question_data.get("bonusKeywords", []),
    }
    return {category: keyword_match(text, keywords) for category, keywords in categories.items()}
