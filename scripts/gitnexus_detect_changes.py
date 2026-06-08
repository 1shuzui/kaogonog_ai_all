#!/usr/bin/env python3
"""
这个脚本处理 `gitnexus_detect_changes` 相关的本地运维或数据检查；放在仓库根目录是为了部署和排查时直接调用。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
from collections import defaultdict


def run(cmd: list[str], cwd: str, timeout: int | None = None) -> str:
    """
    run 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param cmd: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param cwd: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param timeout: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises RuntimeError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
    """
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "command failed")
    return result.stdout


def repo_root() -> pathlib.Path:
    """
    repo_root 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return pathlib.Path(out.stdout.strip())


def infer_repo_name(root: pathlib.Path) -> str:
    """
    infer_repo_name 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param root: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    registry_path = pathlib.Path.home() / ".gitnexus" / "registry.json"
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            for name, meta in registry.items():
                if pathlib.Path(meta.get("path", "")).resolve() == root.resolve():
                    return name
        except Exception:
            pass
    return root.name


def diff_args(scope: str, base_ref: str | None) -> tuple[list[str], list[str]]:
    """
    diff_args 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param scope: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param base_ref: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises ValueError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
    """
    if scope == "staged":
        return ["git", "diff", "--cached", "--name-only"], ["git", "diff", "--cached", "--unified=0", "--no-color"]
    if scope == "unstaged":
        return ["git", "diff", "--name-only"], ["git", "diff", "--unified=0", "--no-color"]
    if scope == "all":
        return ["git", "diff", "--name-only", "HEAD"], ["git", "diff", "HEAD", "--unified=0", "--no-color"]
    if scope == "compare":
        ref = base_ref or "main"
        return (
            ["git", "diff", "--name-only", f"{ref}...HEAD"],
            ["git", "diff", f"{ref}...HEAD", "--unified=0", "--no-color"],
        )
    raise ValueError(f"unsupported scope: {scope}")


def parse_changed_ranges(diff_text: str) -> dict[str, list[tuple[int, int]]]:
    """
    parse_changed_ranges 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param diff_text: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    changed: dict[str, list[tuple[int, int]]] = defaultdict(list)
    current_file = ""
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        if not current_file or not line.startswith("@@"):
            continue
        match = re.search(r"\+(\d+)(?:,(\d+))?", line)
        if not match:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or "1")
        changed[current_file].append((start, max(count, 1)))
    return dict(changed)


PY_PATTERNS = [
    re.compile(r"^\s*async\s+def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("),
    re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("),
    re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
]
JS_PATTERNS = [
    re.compile(r"^\s*export\s+async\s+function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\("),
    re.compile(r"^\s*export\s+function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\("),
    re.compile(r"^\s*async\s+function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\("),
    re.compile(r"^\s*function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\("),
    re.compile(
        r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>|[A-Za-z_$][A-Za-z0-9_$]*\s*=>)"
    ),
]


def symbol_patterns(path: pathlib.Path) -> list[re.Pattern[str]]:
    """
    symbol_patterns 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param path: 本地路径或路由路径；调用方需区分文件系统路径与前端页面路径。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    if path.suffix == ".py":
        return PY_PATTERNS
    if path.suffix in {".js", ".ts", ".jsx", ".tsx", ".vue"}:
        return JS_PATTERNS
    return []


def infer_symbols_for_file(root: pathlib.Path, rel_path: str, ranges: list[tuple[int, int]]) -> list[dict]:
    """
    infer_symbols_for_file 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param root: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param rel_path: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param ranges: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    path = root / rel_path
    if not path.exists() or not path.is_file():
        return []

    patterns = symbol_patterns(path)
    if not patterns:
        return []

    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    results: list[dict] = []
    seen: set[tuple[str, int]] = set()

    for start, count in ranges:
        begin = max(1, start)
        end = start + max(count - 1, 0)
        symbol_name = ""
        symbol_line = 0
        for idx in range(min(begin - 1, len(lines) - 1), -1, -1):
            line = lines[idx]
            for pattern in patterns:
                match = pattern.search(line)
                if match:
                    symbol_name = match.group(1)
                    symbol_line = idx + 1
                    break
            if symbol_name:
                break

        if not symbol_name:
            continue
        key = (symbol_name, symbol_line)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "name": symbol_name,
                "line": symbol_line,
                "changedRange": f"{begin}-{end}",
            }
        )
    return results


def fetch_context(repo_name: str, root: pathlib.Path, rel_path: str, symbol_name: str) -> dict:
    """
    fetch_context 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param repo_name: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param root: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param rel_path: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param symbol_name: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    try:
        raw = run(
            [
                "npx",
                "gitnexus",
                "context",
                symbol_name,
                "--repo",
                repo_name,
                "--file",
                rel_path,
            ],
            str(root),
            timeout=6,
        )
        return json.loads(raw)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def render_text(summary: dict) -> str:
    """
    render_text 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param summary: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    lines = [
        f"repo: {summary['repo']}",
        f"scope: {summary['scope']}",
        f"base_ref: {summary.get('baseRef') or ''}",
        f"changed_files: {len(summary['changedFiles'])}",
        f"inferred_symbols: {len(summary['changedSymbols'])}",
    ]
    if summary["affectedProcesses"]:
        lines.append("affected_processes:")
        for process in summary["affectedProcesses"]:
            lines.append(f"  - {process}")
    if summary["changedSymbols"]:
        lines.append("symbols:")
        for item in summary["changedSymbols"]:
            process_suffix = f" | processes={','.join(item['processes'])}" if item["processes"] else ""
            lines.append(
                f"  - {item['file']}:{item['line']} {item['symbol']} [{item['changedRange']}]{process_suffix}"
            )
    return "\n".join(lines)


def main() -> int:
    """
    main 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    parser = argparse.ArgumentParser(description="Compatibility wrapper for gitnexus_detect_changes")
    parser.add_argument("--scope", default="staged", choices=["staged", "unstaged", "all", "compare"])
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--repo", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-symbols", type=int, default=40)
    args = parser.parse_args()

    root = repo_root()
    repo_name = args.repo or infer_repo_name(root)
    name_cmd, diff_cmd = diff_args(args.scope, args.base_ref if args.scope == "compare" else None)

    changed_files = [line.strip() for line in run(name_cmd, str(root)).splitlines() if line.strip()]
    changed_ranges = parse_changed_ranges(run(diff_cmd, str(root)))

    changed_symbols: list[dict] = []
    affected_processes: set[str] = set()

    symbol_budget = max(args.max_symbols, 0)
    for rel_path in changed_files:
        for symbol in infer_symbols_for_file(root, rel_path, changed_ranges.get(rel_path, [])):
            if symbol_budget and len(changed_symbols) >= symbol_budget:
                break
            ctx = fetch_context(repo_name, root, rel_path, symbol["name"])
            processes = []
            if isinstance(ctx, dict):
                for process in ctx.get("processes", []) or []:
                    name = str(process.get("name") or "").strip()
                    if name:
                        processes.append(name)
                        affected_processes.add(name)
            changed_symbols.append(
                {
                    "file": rel_path,
                    "symbol": symbol["name"],
                    "line": symbol["line"],
                    "changedRange": symbol["changedRange"],
                    "processes": processes,
                }
            )
        if symbol_budget and len(changed_symbols) >= symbol_budget:
            break

    summary = {
        "repo": repo_name,
        "root": str(root),
        "scope": args.scope,
        "baseRef": args.base_ref if args.scope == "compare" else "",
        "changedFiles": changed_files,
        "changedSymbols": changed_symbols,
        "affectedProcesses": sorted(affected_processes),
        "symbolLimitApplied": symbol_budget,
        "note": "Compatibility wrapper: official gitnexus CLI on this machine does not expose a detect_changes subcommand.",
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(render_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
