#!/usr/bin/env python3
"""兼容入口：默认按安徽 profile 导入题库。"""

from __future__ import annotations

try:
    from scripts.import_question_bank import run_profile_import
except ImportError:
    from import_question_bank import run_profile_import


def main() -> int:
    return run_profile_import("anhui")


if __name__ == "__main__":
    raise SystemExit(main())
