#!/usr/bin/env python3
"""Compatibility wrapper for gitnexus_detect_changes.

The current GitNexus CLI on this machine exposes `impact/context/query/...`
but not the `detect_changes` command documented by the MCP/tooling guides.
This script provides a local, graph-assisted approximation for this repo:

- reads git diff for a given scope
- infers changed symbols from changed line ranges
- asks GitNexus `context` for each inferred symbol to collect affected processes
- prints a compact JSON or text summary
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
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "command failed")
    return result.stdout


def repo_root() -> pathlib.Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return pathlib.Path(out.stdout.strip())


def infer_repo_name(root: pathlib.Path) -> str:
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
    if path.suffix == ".py":
        return PY_PATTERNS
    if path.suffix in {".js", ".ts", ".jsx", ".tsx", ".vue"}:
        return JS_PATTERNS
    return []


def infer_symbols_for_file(root: pathlib.Path, rel_path: str, ranges: list[tuple[int, int]]) -> list[dict]:
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
