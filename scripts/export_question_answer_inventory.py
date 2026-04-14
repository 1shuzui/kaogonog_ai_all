#!/usr/bin/env python3
"""Export project question/answer inventory for manual testing."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = REPO_ROOT / "ai_gongwu_backend" / "assets" / "questions"
BACKEND_DB = REPO_ROOT / "civil-interview-backend" / "civil_interview.db"
REPORT_DIR = REPO_ROOT / "reports"


def answer_asset_status(has_reference: bool, regression_count: int) -> str:
    if has_reference and regression_count:
        return "reference+regression"
    if has_reference:
        return "reference_only"
    if regression_count:
        return "regression_only"
    return "none"


def export_asset_inventory() -> list[dict]:
    rows = []
    for path in sorted(ASSET_ROOT.rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        regression_cases = data.get("regressionCases") or []
        regression_samples = []
        for case in regression_cases:
            if isinstance(case, dict):
                sample = str(case.get("sample_path") or "").strip()
                if sample:
                    regression_samples.append(sample)
        has_reference = bool(str(data.get("referenceAnswer") or "").strip())
        rows.append(
            {
                "id": str(data.get("id") or path.stem),
                "province": str(data.get("province") or ""),
                "sourceDocument": str(data.get("sourceDocument") or ""),
                "path": str(path.relative_to(REPO_ROOT)),
                "hasReferenceAnswer": has_reference,
                "regressionCaseCount": len(regression_cases) if isinstance(regression_cases, list) else 0,
                "regressionSamples": regression_samples,
                "answerAssetStatus": answer_asset_status(has_reference, len(regression_samples)),
                "tags": data.get("tags") if isinstance(data.get("tags"), list) else [],
            }
        )
    return rows


def export_backend_inventory() -> list[dict]:
    if not BACKEND_DB.exists():
        return []
    conn = sqlite3.connect(BACKEND_DB)
    conn.row_factory = sqlite3.Row
    rows = []
    try:
        for record in conn.execute(
            "select id, stem, province, dimension, keywords from questions order by province, id"
        ):
            try:
                keywords = json.loads(record["keywords"]) if record["keywords"] else {}
            except Exception:
                keywords = {}
            meta = keywords.get("_meta") if isinstance(keywords.get("_meta"), dict) else {}
            has_reference = bool(str(meta.get("referenceAnswer") or "").strip())
            regression_cases = meta.get("regressionCases") if isinstance(meta.get("regressionCases"), list) else []
            rows.append(
                {
                    "id": record["id"],
                    "province": record["province"],
                    "dimension": record["dimension"],
                    "stem": record["stem"],
                    "questionSource": meta.get("source", ""),
                    "questionSourceLabel": meta.get("sourceLabel", ""),
                    "sourceDocument": meta.get("sourceDocument", ""),
                    "sourceQuestionId": meta.get("sourceQuestionId", ""),
                    "hasReferenceAnswer": has_reference,
                    "hasRegressionCases": bool(regression_cases),
                    "answerAssetStatus": answer_asset_status(has_reference, len(regression_cases)),
                }
            )
    finally:
        conn.close()
    return rows


def export_markdown(asset_rows: list[dict], backend_rows: list[dict]) -> str:
    lines = [
        "# Question Answer Inventory",
        "",
        "## Summary",
        "",
        f"- Asset questions: {len(asset_rows)}",
        f"- Backend DB questions: {len(backend_rows)}",
        f"- Asset questions with reference answers: {sum(1 for row in asset_rows if row['hasReferenceAnswer'])}",
        f"- Asset questions with regression samples: {sum(1 for row in asset_rows if row['regressionCaseCount'])}",
        f"- Backend questions with reference answers: {sum(1 for row in backend_rows if row['hasReferenceAnswer'])}",
        "",
        "## Asset Questions",
        "",
        "| ID | Province | Answer Assets | Reference | Regression Cases | Source Document | Path |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for row in asset_rows:
        lines.append(
            f"| {row['id']} | {row['province']} | {row['answerAssetStatus']} | "
            f"{'Y' if row['hasReferenceAnswer'] else 'N'} | {row['regressionCaseCount']} | "
            f"{row['sourceDocument'] or '-'} | `{row['path']}` |"
        )
    lines.extend(
        [
            "",
            "## Backend Questions",
            "",
            "| ID | Province | Source | Answer Assets | Reference | Source Document | Source Question ID |",
            "|---|---|---|---|---:|---|---|",
        ]
    )
    for row in backend_rows:
        lines.append(
            f"| {row['id']} | {row['province']} | {row['questionSourceLabel'] or row['questionSource'] or '-'} | "
            f"{row['answerAssetStatus']} | {'Y' if row['hasReferenceAnswer'] else 'N'} | "
            f"{row['sourceDocument'] or '-'} | {row['sourceQuestionId'] or '-'} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    asset_rows = export_asset_inventory()
    backend_rows = export_backend_inventory()

    (REPORT_DIR / "question_inventory.json").write_text(
        json.dumps(asset_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (REPORT_DIR / "backend_question_inventory.json").write_text(
        json.dumps(backend_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (REPORT_DIR / "question_inventory.md").write_text(
        export_markdown(asset_rows, backend_rows),
        encoding="utf-8",
    )

    print(REPORT_DIR / "question_inventory.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
