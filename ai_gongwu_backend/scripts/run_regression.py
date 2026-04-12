#!/usr/bin/env python3
"""批量回归脚本。

用途：
1. 按题目批量执行文本样本评分
2. 对照题库里的 regressionCases 判断是否命中预期分档
3. 输出控制台摘要，同时把 JSON / Markdown 报表写入 reports/regression
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
DEFAULT_REPORT_DIR = REPO_ROOT / "reports" / "regression"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.core.dependencies import get_flow_service, get_question_bank
from app.models.schemas import RegressionCase, ScoreBand


@dataclass
class RegressionRow:
    question_id: str
    sample_label: str
    sample_path: str
    expected_range: str
    expected_band: str
    actual_score: float | None
    actual_band: str
    status: str
    validation_issue_count: int
    notes: list[str]
    error: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行题库回归样本批量评分。")
    parser.add_argument(
        "--question-id",
        action="append",
        dest="question_ids",
        help="只运行指定 question_id。可重复传入多个。",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_REPORT_DIR),
        help="回归报表输出目录。默认写入 reports/regression。",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="是否把回归结果也写入数据库。默认不落库，避免污染正式记录。",
    )
    return parser.parse_args()


def resolve_sample_path(sample_path: str) -> Path:
    candidates = [
        Path(sample_path),
        REPO_ROOT / sample_path,
        BACKEND_ROOT / sample_path,
        settings.resolve_path(sample_path),
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"未找到回归样本文件: {sample_path}")


def pick_band(score: float, score_bands: Iterable[ScoreBand]) -> str:
    for band in score_bands:
        if band.min_score <= score <= band.max_score:
            return band.label
    return "未命中分档"


def expected_band_name(case: RegressionCase, score_bands: Iterable[ScoreBand]) -> str:
    midpoint = round((case.expected_min + case.expected_max) / 2, 1)
    return pick_band(midpoint, score_bands)


def render_markdown(rows: list[RegressionRow], generated_at: str) -> str:
    lines = [
        "# 回归测试报告",
        "",
        f"- 生成时间: `{generated_at}`",
        f"- 样本数: `{len(rows)}`",
        "",
        "| question_id | 样本 | 期望区间 | 期望分档 | 实际分数 | 实际分档 | 状态 | 校验提示数 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        actual_score = "-" if row.actual_score is None else f"{row.actual_score:.1f}"
        lines.append(
            f"| {row.question_id} | {row.sample_label} | {row.expected_range} | "
            f"{row.expected_band} | {actual_score} | {row.actual_band} | "
            f"{row.status} | {row.validation_issue_count} |"
        )

    lines.append("")
    lines.append("## 失败明细")
    lines.append("")
    failed_rows = [row for row in rows if row.status != "PASS"]
    if not failed_rows:
        lines.append("本次回归全部通过。")
    else:
        for row in failed_rows:
            lines.append(f"### {row.question_id} / {row.sample_label}")
            lines.append("")
            lines.append(f"- 样本路径: `{row.sample_path}`")
            lines.append(f"- 期望区间: `{row.expected_range}`")
            lines.append(f"- 实际分数: `{row.actual_score}`")
            lines.append(f"- 实际分档: `{row.actual_band}`")
            if row.error:
                lines.append(f"- 错误: `{row.error}`")
            if row.notes:
                lines.append("- 备注: " + "；".join(row.notes[:5]))
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    question_bank = get_question_bank()
    flow_service = get_flow_service()

    selected_ids = set(args.question_ids or [])
    questions = [
        question
        for question in question_bank.list_questions()
        if not selected_ids or question.id in selected_ids
    ]
    if not questions:
        available = ", ".join(question_bank.list_ids()) or "无"
        raise SystemExit(f"未找到可执行的题目。当前可用题目: {available}")

    rows: list[RegressionRow] = []
    for question in questions:
        if not question.regressionCases:
            rows.append(
                RegressionRow(
                    question_id=question.id,
                    sample_label="无回归样本",
                    sample_path="",
                    expected_range="-",
                    expected_band="-",
                    actual_score=None,
                    actual_band="-",
                    status="SKIP",
                    validation_issue_count=0,
                    notes=["题目未配置 regressionCases。"],
                )
            )
            continue

        for case in question.regressionCases:
            expected_range = f"{case.expected_min:.1f}-{case.expected_max:.1f}"
            band_label = expected_band_name(case, question.scoreBands)
            try:
                sample_file = resolve_sample_path(case.sample_path)
                transcript = sample_file.read_text(encoding="utf-8")
                result = flow_service.evaluate_text_only(
                    question_id=question.id,
                    text_content=transcript,
                    source_filename=sample_file.name,
                    persist=args.persist,
                )
                actual_score = float(result.total_score)
                actual_band = pick_band(actual_score, question.scoreBands)
                status = (
                    "PASS"
                    if case.expected_min <= actual_score <= case.expected_max
                    else "FAIL"
                )
                rows.append(
                    RegressionRow(
                        question_id=question.id,
                        sample_label=case.label,
                        sample_path=str(sample_file),
                        expected_range=expected_range,
                        expected_band=band_label,
                        actual_score=actual_score,
                        actual_band=actual_band,
                        status=status,
                        validation_issue_count=len(result.validation_notes),
                        notes=result.validation_notes[:8] + ([case.notes] if case.notes else []),
                    )
                )
            except Exception as exc:  # noqa: BLE001 - 回归脚本需要把错误收集进报表
                rows.append(
                    RegressionRow(
                        question_id=question.id,
                        sample_label=case.label,
                        sample_path=case.sample_path,
                        expected_range=expected_range,
                        expected_band=band_label,
                        actual_score=None,
                        actual_band="执行失败",
                        status="ERROR",
                        validation_issue_count=0,
                        notes=[case.notes] if case.notes else [],
                        error=str(exc),
                    )
                )

    generated_at = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"regression_{generated_at}.json"
    md_path = output_dir / f"regression_{generated_at}.md"

    json_payload = {
        "generated_at": generated_at,
        "question_ids": [question.id for question in questions],
        "persist": args.persist,
        "summary": {
            "total": len(rows),
            "pass": sum(1 for row in rows if row.status == "PASS"),
            "fail": sum(1 for row in rows if row.status == "FAIL"),
            "error": sum(1 for row in rows if row.status == "ERROR"),
            "skip": sum(1 for row in rows if row.status == "SKIP"),
        },
        "rows": [asdict(row) for row in rows],
    }
    json_path.write_text(
        json.dumps(json_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(rows, generated_at), encoding="utf-8")

    print(f"回归样本总数: {json_payload['summary']['total']}")
    print(f"PASS: {json_payload['summary']['pass']}")
    print(f"FAIL: {json_payload['summary']['fail']}")
    print(f"ERROR: {json_payload['summary']['error']}")
    print(f"SKIP: {json_payload['summary']['skip']}")
    print(f"JSON 报表: {json_path}")
    print(f"Markdown 报表: {md_path}")

    return 0 if json_payload["summary"]["fail"] == 0 and json_payload["summary"]["error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
