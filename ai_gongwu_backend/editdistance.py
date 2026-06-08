"""
这个文件提供最小编辑距离实现；在没有额外依赖时，ASR 和文本回归仍能计算差异。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

from __future__ import annotations


def eval(seq1, seq2) -> int:
    """
    eval 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param seq1: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param seq2: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    if not seq1:
        return len(seq2)
    if not seq2:
        return len(seq1)

    prev = list(range(len(seq2) + 1))
    for i, item1 in enumerate(seq1, start=1):
        curr = [i]
        for j, item2 in enumerate(seq2, start=1):
            insert_cost = curr[j - 1] + 1
            delete_cost = prev[j] + 1
            replace_cost = prev[j - 1] + (item1 != item2)
            curr.append(min(insert_cost, delete_cost, replace_cost))
        prev = curr
    return prev[-1]
