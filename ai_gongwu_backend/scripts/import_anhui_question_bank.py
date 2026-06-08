#!/usr/bin/env python3
"""
这个脚本是安徽题库导入入口；它复用通用导入器，避免安徽省考资料被错误套用到别的省份。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

from __future__ import annotations

try:
    from scripts.import_question_bank import run_profile_import
except ImportError:
    from import_question_bank import run_profile_import


def main() -> int:
    """
    main 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    题库导入脚本把 Word 真题转成结构化资产，注释重点记录真实题源优先和人工复核边界。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return run_profile_import("anhui")


if __name__ == "__main__":
    raise SystemExit(main())
