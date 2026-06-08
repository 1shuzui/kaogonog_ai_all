"""
这个文件处理旧题库和样本文件读取；路径和编码问题在这里兜住，业务代码不用反复判断文件来源。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

import json
from pathlib import Path
from typing import Any


def load_json_data(file_path: str | Path) -> Any:
    """
    从本地路径读取 JSON 数据。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param file_path: 本地文件路径；脚本需保留来源路径以便题库导入结果可追溯。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises FileNotFoundError, ValueError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
    """

    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"数据文件不存在: {path.resolve()}")

    try:
        with path.open("r", encoding="utf-8") as file_obj:
            return json.load(file_obj)
    except json.JSONDecodeError as exc:
        # 把底层 JSON 错误包装成更明确的业务错误信息，便于定位题库问题。
        raise ValueError(f"JSON 格式解析失败 [{path}]: {exc}") from exc
