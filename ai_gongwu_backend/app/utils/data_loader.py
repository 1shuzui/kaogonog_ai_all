"""数据加载工具。

目前这里只有一个简单能力：读取本地 JSON。
虽然代码不长，但单独抽成工具函数有两个好处：
1. 复用方便
2. 以后想加缓存、日志、远程文件读取时，改动点集中
"""

import json
from pathlib import Path
from typing import Any


def load_json_data(file_path: str | Path) -> Any:
    """从本地路径读取 JSON 数据。"""

    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"数据文件不存在: {path.resolve()}")

    try:
        with path.open("r", encoding="utf-8") as file_obj:
            return json.load(file_obj)
    except json.JSONDecodeError as exc:
        # 把底层 JSON 错误包装成更明确的业务错误信息，便于定位题库问题。
        raise ValueError(f"JSON 格式解析失败 [{path}]: {exc}") from exc
