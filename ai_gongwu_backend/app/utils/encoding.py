"""
这个文件处理中文文本编码兜底；历史资料来源混杂时，先保证脚本能读出可复核文本。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

from __future__ import annotations

import sys


def ensure_utf8_stdio() -> None:
    """
    ensure_utf8_stdio 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            # Some embedded terminals or wrapped streams do not support reconfigure().
            continue
