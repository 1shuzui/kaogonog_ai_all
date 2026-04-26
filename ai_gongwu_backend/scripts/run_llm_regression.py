#!/usr/bin/env python3
"""真实大模型回归与标定脚本。

用途：
1. 强制走真实 LLM 评分链路，不接受确定性兜底冒充成功
2. 批量执行 regressionCases，并优先使用 llmExpectedMin/llmExpectedMax 判定
3. 输出 JSON / Markdown 报表，供后续分析模型漂移
4. 可选把本次实测结果回写到题库 JSON，完成 LLM 区间标定
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from dataclasses import asdict, dataclass, field
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
    level: str
    expected_range: str
    expectation_source: str
    expected_band: str
    actual_score: float | None
    actual_band: str
    status: str
    validation_issue_count: int
    notes: list[str]
    attempt_scores: list[float] = field(default_factory=list)
    fallback_used: bool = False
    error: str = ""


@dataclass(frozen=True)
class WritebackDecision:
    question_id: str
    allowed: bool
    updated: bool = False
    reason: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行真实大模型回归并可选标定 llmExpected 区间。")
    parser.add_argument(
        "--question-id",
        action="append",
        dest="question_ids",
        help="只运行指定 question_id。可重复传入多个。",
    )
    parser.add_argument(
        "--sample-level",
        choices=("all", "high", "mid", "low"),
        default="all",
        help="只运行指定档位样本。默认 all。",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_REPORT_DIR),
        help="报表输出目录。默认写入 reports/regression。",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="是否把测评结果写入数据库。默认不落库。",
    )
    parser.add_argument(
        "--allow-fallback",
        action="store_true",
        help="允许 LLM 失败后回落到确定性评分。默认不允许，出现回退即记为 ERROR。",
    )
    parser.add_argument(
        "--writeback",
        action="store_true",
        help="把本次实测得到的推荐 llmExpectedMin/llmExpectedMax 回写到题库 JSON。",
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=2.0,
        help="回写标定时的默认半宽。默认 2.0 分。",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="压低日志噪音，只保留关键输出。",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="每个样本重复运行次数，取中位数作为实际分数。默认 1。",
    )
    return parser.parse_args()


def configure_logging(quiet: bool) -> None:
    if not quiet:
        return
    logging.getLogger().setLevel(logging.WARNING)
    for name in ("httpx", "openai", "app.services.flow", "app.services.question_bank", "app.services.llm.client"):
        logging.getLogger(name).setLevel(logging.WARNING)


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


def resolve_question_json_path(question_id: str) -> Path:
    candidates = sorted((BACKEND_ROOT / "assets" / "questions").rglob(f"{question_id}.json"))
    if not candidates:
        raise FileNotFoundError(f"未找到题目 JSON: {question_id}")
    return candidates[0]


def pick_band(score: float, score_bands: Iterable[ScoreBand]) -> str:
    for band in score_bands:
        if band.min_score <= score <= band.max_score:
            return band.label
    return "未命中分档"


def infer_case_level(case: RegressionCase) -> str:
    sample_name = Path(case.sample_path).name.lower()
    if "high" in sample_name or "高分" in case.label:
        return "high"
    if "mid" in sample_name or "中档" in case.label:
        return "mid"
    if "low" in sample_name or "低档" in case.label:
        return "low"
    return "unknown"


def select_expected_range(case: RegressionCase) -> tuple[float, float, str]:
    if case.llmExpectedMin is not None and case.llmExpectedMax is not None:
        return float(case.llmExpectedMin), float(case.llmExpectedMax), "llmExpected"
    return float(case.expected_min), float(case.expected_max), "deterministicExpected"


def expected_band_name(case: RegressionCase, score_bands: Iterable[ScoreBand]) -> str:
    expected_min, expected_max, _ = select_expected_range(case)
    midpoint = round((expected_min + expected_max) / 2, 1)
    return pick_band(midpoint, score_bands)


def render_markdown(rows: list[RegressionRow], generated_at: str) -> str:
    lines = [
        "# LLM 回归测试报告",
        "",
        f"- 生成时间: `{generated_at}`",
        f"- 样本数: `{len(rows)}`",
        "",
        "| question_id | 样本 | 档位 | 期望区间 | 来源 | 实际分数 | 状态 | 回退 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        actual_score = "-" if row.actual_score is None else f"{row.actual_score:.1f}"
        attempt_scores = "-" if not row.attempt_scores else ", ".join(f"{score:.1f}" for score in row.attempt_scores)
        lines.append(
            f"| {row.question_id} | {row.sample_label} | {row.level} | "
            f"{row.expected_range} | {row.expectation_source} | {actual_score} | "
            f"{row.status} | {'是' if row.fallback_used else '否'} |"
        )

    lines.append("")
    lines.append("## 失败明细")
    lines.append("")
    failed_rows = [row for row in rows if row.status != "PASS"]
    if not failed_rows:
        lines.append("本次真实大模型回归全部通过。")
    else:
        for row in failed_rows:
            lines.append(f"### {row.question_id} / {row.sample_label}")
            lines.append("")
            lines.append(f"- 样本路径: `{row.sample_path}`")
            lines.append(f"- 档位: `{row.level}`")
            lines.append(f"- 期望区间: `{row.expected_range}`")
            lines.append(f"- 期望来源: `{row.expectation_source}`")
            lines.append(f"- 实际分数: `{row.actual_score}`")
            if row.attempt_scores:
                attempt_scores = ", ".join(f"{score:.1f}" for score in row.attempt_scores)
                lines.append(f"- 多次得分: `{attempt_scores}`")
            lines.append(f"- 是否回退: `{'是' if row.fallback_used else '否'}`")
            if row.error:
                lines.append(f"- 错误: `{row.error}`")
            if row.notes:
                lines.append("- 备注: " + "；".join(row.notes[:6]))
            lines.append("")

    return "\n".join(lines)


def emit(message: str) -> None:
    """统一输出进度，并强制刷新，避免长任务时看起来像卡死。"""

    print(message, flush=True)


def normalize_range(lower: float, upper: float, *, lower_bound: float, upper_bound: float) -> tuple[float, float]:
    upper_bound = max(upper_bound, lower_bound)
    lower = round(min(max(lower_bound, lower), upper_bound), 1)
    upper = round(min(max(lower_bound, upper), upper_bound), 1)
    if upper < lower:
        center = round(min(max((lower + upper) / 2, lower_bound), upper_bound), 1)
        lower = round(max(lower_bound, center - 1.0), 1)
        upper = round(min(upper_bound, center + 1.0), 1)
        if upper < lower:
            lower = upper = center
    return lower, upper


def build_calibrated_ranges(rows: list[RegressionRow], question) -> dict[str, tuple[float, float]]:
    margin_by_level = {
        "high": max(1.5, question.fullScore * 0.03),
        "mid": max(2.0, question.fullScore * 0.04),
        "low": max(2.5, question.fullScore * 0.05),
    }
    by_level = {row.level: row for row in rows if row.actual_score is not None and row.level in {"high", "mid", "low"}}
    calibrated: dict[str, tuple[float, float]] = {}

    if "high" in by_level:
        row = by_level["high"]
        calibrated["high"] = normalize_range(
            row.actual_score - margin_by_level["high"],
            row.actual_score + margin_by_level["high"],
            lower_bound=max(question.fullScore * 0.8, 0.0),
            upper_bound=question.fullScore,
        )
    if "mid" in by_level:
        row = by_level["mid"]
        upper_bound = calibrated.get("high", (question.fullScore, question.fullScore))[0] - 0.5
        calibrated["mid"] = normalize_range(
            row.actual_score - margin_by_level["mid"],
            row.actual_score + margin_by_level["mid"],
            lower_bound=0.0,
            upper_bound=max(upper_bound, 0.0),
        )
    if "low" in by_level:
        row = by_level["low"]
        upper_bound = calibrated.get("mid", (question.fullScore, question.fullScore))[0] - 0.5
        calibrated["low"] = normalize_range(
            row.actual_score - margin_by_level["low"],
            row.actual_score + margin_by_level["low"],
            lower_bound=0.0,
            upper_bound=max(upper_bound, 0.0),
        )

    # 再做一次顺序修正，保证 high > mid > low。
    if "high" in calibrated and "mid" in calibrated:
        mid_lower, mid_upper = calibrated["mid"]
        high_lower, _ = calibrated["high"]
        if mid_upper >= high_lower:
            calibrated["mid"] = normalize_range(
                mid_lower,
                high_lower - 0.5,
                lower_bound=0.0,
                upper_bound=high_lower - 0.5,
            )
    if "mid" in calibrated and "low" in calibrated:
        low_lower, low_upper = calibrated["low"]
        mid_lower, _ = calibrated["mid"]
        if low_upper >= mid_lower:
            calibrated["low"] = normalize_range(
                low_lower,
                mid_lower - 0.5,
                lower_bound=0.0,
                upper_bound=mid_lower - 0.5,
            )

    return calibrated


def assess_writeback_stability(rows: list[RegressionRow], question) -> tuple[bool, str]:
    core_levels = {"high", "mid", "low"}
    core_rows = [row for row in rows if row.level in core_levels]
    if not core_rows:
        return False, "未找到可用于标定的 high/mid/low 样本。"

    missing_levels = sorted(core_levels - {row.level for row in core_rows})
    if missing_levels:
        return False, f"缺少核心档位样本: {', '.join(missing_levels)}"

    non_pass_rows = [row for row in core_rows if row.status != "PASS"]
    if non_pass_rows:
        detail = ", ".join(f"{row.level}:{row.status}" for row in non_pass_rows)
        return False, f"存在未通过样本，跳过回写: {detail}"

    fallback_rows = [row for row in core_rows if row.fallback_used]
    if fallback_rows:
        detail = ", ".join(row.level for row in fallback_rows)
        return False, f"存在回退到确定性评分的样本，跳过回写: {detail}"

    by_level = {row.level: row for row in core_rows}
    high_score = by_level["high"].actual_score
    mid_score = by_level["mid"].actual_score
    low_score = by_level["low"].actual_score
    if high_score is None or mid_score is None or low_score is None:
        return False, "存在空分数样本，跳过回写。"
    if not (high_score > mid_score > low_score):
        return False, (
            "样本排序未满足 high > mid > low，"
            f"当前为 {high_score:.1f} > {mid_score:.1f} > {low_score:.1f}"
        )

    allowed_attempt_range = max(3.0, question.fullScore * 0.08)
    unstable_rows: list[str] = []
    for row in core_rows:
        if not row.attempt_scores:
            continue
        attempt_range = max(row.attempt_scores) - min(row.attempt_scores)
        if attempt_range > allowed_attempt_range:
            unstable_rows.append(f"{row.level}:波动{attempt_range:.1f}")
    if unstable_rows:
        return False, "多次采样波动过大，跳过回写: " + ", ".join(unstable_rows)

    return True, ""


def writeback_llm_ranges(question_id: str, rows: list[RegressionRow], question) -> WritebackDecision:
    allowed, reason = assess_writeback_stability(rows, question)
    if not allowed:
        return WritebackDecision(question_id=question_id, allowed=False, updated=False, reason=reason)

    calibrated = build_calibrated_ranges(rows, question)
    if not calibrated:
        return WritebackDecision(
            question_id=question_id,
            allowed=False,
            updated=False,
            reason="未生成可回写的标定区间。",
        )

    json_path = resolve_question_json_path(question_id)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    updated = False
    for case in payload.get("regressionCases", []):
        level = infer_case_level(RegressionCase.model_validate(case))
        if level not in calibrated:
            continue
        llm_min, llm_max = calibrated[level]
        if case.get("llmExpectedMin") == llm_min and case.get("llmExpectedMax") == llm_max:
            continue
        case["llmExpectedMin"] = llm_min
        case["llmExpectedMax"] = llm_max
        updated = True

    if updated:
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if not updated:
        return WritebackDecision(
            question_id=question_id,
            allowed=True,
            updated=False,
            reason="区间与现有题库一致，无需回写。",
        )
    return WritebackDecision(
        question_id=question_id,
        allowed=True,
        updated=True,
        reason="已按稳定样本结果回写区间。",
    )


def main() -> int:
    args = parse_args()
    if args.repeat < 1:
        raise SystemExit("--repeat 至少为 1。")
    configure_logging(args.quiet)

    question_bank = get_question_bank()
    flow_service = get_flow_service()
    if flow_service.llm_client.client is None:
        raise SystemExit("LLM 客户端未初始化，无法运行真实大模型回归。")

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
    rows_by_question: dict[str, list[RegressionRow]] = {}
    for question in questions:
        if not question.regressionCases:
            rows.append(
                RegressionRow(
                    question_id=question.id,
                    sample_label="无回归样本",
                    sample_path="",
                    level="unknown",
                    expected_range="-",
                    expectation_source="-",
                    expected_band="-",
                    actual_score=None,
                    actual_band="-",
                    status="SKIP",
                    validation_issue_count=0,
                    notes=["题目未配置 regressionCases。"],
                )
            )
            continue

        question_rows: list[RegressionRow] = []
        emit(f"[{question.id}]")
        for case in question.regressionCases:
            level = infer_case_level(case)
            if args.sample_level != "all" and level != args.sample_level:
                continue

            expected_min, expected_max, expectation_source = select_expected_range(case)
            expected_range = f"{expected_min:.1f}-{expected_max:.1f}"
            band_label = expected_band_name(case, question.scoreBands)
            try:
                sample_file = resolve_sample_path(case.sample_path)
                transcript = sample_file.read_text(encoding="utf-8")
                attempt_scores: list[float] = []
                attempt_notes: list[str] = []
                validation_issue_count = 0
                fallback_used = False
                for attempt_index in range(args.repeat):
                    result = flow_service.evaluate_text_only(
                        question_id=question.id,
                        text_content=transcript,
                        source_filename=sample_file.name,
                        persist=args.persist,
                    )
                    current_fallback = any("回退到确定性证据评分" in note for note in result.validation_notes)
                    fallback_used = fallback_used or current_fallback
                    if current_fallback and not args.allow_fallback:
                        raise RuntimeError("检测到回退到确定性评分，本次不计入真实 LLM 回归。")
                    attempt_score = float(result.total_score)
                    attempt_scores.append(attempt_score)
                    validation_issue_count = max(validation_issue_count, len(result.validation_notes))
                    if args.repeat > 1:
                        attempt_notes.append(f"第{attempt_index + 1}次={attempt_score:.1f}")
                    for note in result.validation_notes[:8]:
                        if note not in attempt_notes:
                            attempt_notes.append(note)

                if not attempt_scores:
                    raise RuntimeError("未得到有效 LLM 分数。")

                actual_score = round(float(statistics.median(attempt_scores)), 1)
                actual_band = pick_band(actual_score, question.scoreBands)
                status = "PASS" if expected_min <= actual_score <= expected_max else "FAIL"
                row = RegressionRow(
                    question_id=question.id,
                    sample_label=case.label,
                    sample_path=str(sample_file),
                    level=level,
                    expected_range=expected_range,
                    expectation_source=expectation_source,
                    expected_band=band_label,
                    actual_score=actual_score,
                    actual_band=actual_band,
                    status=status,
                    validation_issue_count=validation_issue_count,
                    notes=attempt_notes[:12] + ([case.notes] if case.notes else []),
                    attempt_scores=attempt_scores,
                    fallback_used=fallback_used,
                )
                question_rows.append(row)
                rows.append(row)
                if args.repeat > 1:
                    attempt_summary = ", ".join(f"{score:.1f}" for score in attempt_scores)
                    emit(f"  - {case.label}: {actual_score:.1f} ({status}) [{attempt_summary}]")
                else:
                    emit(f"  - {case.label}: {actual_score:.1f} ({status})")
            except Exception as exc:  # noqa: BLE001 - 需要把错误收集进报表
                row = RegressionRow(
                    question_id=question.id,
                    sample_label=case.label,
                    sample_path=case.sample_path,
                    level=level,
                    expected_range=expected_range,
                    expectation_source=expectation_source,
                    expected_band=band_label,
                    actual_score=None,
                    actual_band="执行失败",
                    status="ERROR",
                    validation_issue_count=0,
                    notes=[case.notes] if case.notes else [],
                    error=str(exc),
                )
                question_rows.append(row)
                rows.append(row)
                emit(f"  - {case.label}: ERROR {exc}")

        rows_by_question[question.id] = question_rows

    if args.writeback:
        writeback_count = 0
        skipped_count = 0
        for question in questions:
            decision = writeback_llm_ranges(question.id, rows_by_question.get(question.id, []), question)
            if decision.updated:
                writeback_count += 1
            elif not decision.allowed:
                skipped_count += 1
                emit(f"[SKIP WRITEBACK] {question.id}: {decision.reason}")
        emit(f"已回写 llmExpected 区间的题目数: {writeback_count}")
        emit(f"因不稳定而跳过回写的题目数: {skipped_count}")

    generated_at = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"llm_regression_{generated_at}.json"
    md_path = output_dir / f"llm_regression_{generated_at}.md"

    json_payload = {
        "generated_at": generated_at,
        "question_ids": [question.id for question in questions],
        "persist": args.persist,
        "writeback": args.writeback,
        "repeat": args.repeat,
        "summary": {
            "total": len(rows),
            "pass": sum(1 for row in rows if row.status == "PASS"),
            "fail": sum(1 for row in rows if row.status == "FAIL"),
            "error": sum(1 for row in rows if row.status == "ERROR"),
            "skip": sum(1 for row in rows if row.status == "SKIP"),
        },
        "rows": [asdict(row) for row in rows],
    }
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(rows, generated_at), encoding="utf-8")

    emit(f"LLM 回归样本总数: {json_payload['summary']['total']}")
    emit(f"PASS: {json_payload['summary']['pass']}")
    emit(f"FAIL: {json_payload['summary']['fail']}")
    emit(f"ERROR: {json_payload['summary']['error']}")
    emit(f"SKIP: {json_payload['summary']['skip']}")
    emit(f"JSON 报表: {json_path}")
    emit(f"Markdown 报表: {md_path}")

    return 0 if json_payload["summary"]["fail"] == 0 and json_payload["summary"]["error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
