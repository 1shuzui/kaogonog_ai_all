#!/usr/bin/env python3
"""Validate the maintained project knowledge base without third-party packages.

The project deliberately keeps Markdown as the human and AI-readable source of
truth for cross-module contracts. This validator makes common documentation
regressions visible in CI or before handoff: a required knowledge-base document
was removed, a critical contract term disappeared, or an internal Markdown link
no longer resolves.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_DOCUMENTS = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/README.md",
    "docs/ai/README.md",
    "docs/ai/project-context.md",
    "docs/api/README.md",
    "docs/api/question-bank-and-suites.md",
    "docs/api/scoring.md",
    "docs/api/targeted-training.md",
    "docs/data/medical-question-bank.md",
    "docs/ops/question-bank-maintenance.md",
    "docs/decisions/ADR-005-medical-question-bank-and-appearance-score.md",
    "data/question-bank/README.md",
)

REQUIRED_TERMS = {
    "docs/ai/README.md": (
        "questions.keywords._meta",
        "hasCompleteSuiteLevel",
        "appearanceScoreScope",
    ),
    "docs/api/question-bank-and-suites.md": (
        "GET /questions",
        "GET /exam/full-suites",
        "hasCompleteSuiteLevel",
    ),
    "docs/api/scoring.md": (
        "contentScore",
        "appearanceScore",
        "appearanceScoreSource",
        "95 + 5",
    ),
    "docs/api/targeted-training.md": (
        "GET /positions",
        "portalTag",
        "positionTags",
    ),
    "docs/data/medical-question-bank.md": (
        "medical_general",
        "shandong_medical",
        "jiangsu_medical",
        "江苏新套03",
        "appearanceScoreScope",
    ),
    "docs/ops/question-bank-maintenance.md": (
        "--source-dir",
        "sha256sum",
        "generated_shandong_medical",
    ),
    "docs/decisions/ADR-005-medical-question-bank-and-appearance-score.md": (
        "事业单位考试",
        "profile_default",
        "actual",
    ),
}

MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
EXTERNAL_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
ROOT_MARKDOWN_DOCUMENTS = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "ai_gongwu_backend/scripts/README.md",
    "ai_gongwu_backend/assets/questions/README.md",
    "ai_gongwu_backend/assets/regression_samples/README.md",
    "reports/README.md",
    "reports/regression/README.md",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to the parent of scripts/.",
    )
    return parser.parse_args()


def is_external_target(target: str) -> bool:
    return (
        not target
        or target.startswith("#")
        or target.startswith("/")
        or target.startswith("//")
        or EXTERNAL_SCHEME_RE.match(target) is not None
    )


def clean_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split("#", 1)[0].strip()
    # Markdown permits an optional title after a destination. None of the
    # maintained docs require spaces in local names, so this is sufficient and
    # deliberately conservative.
    if " " in target:
        target = target.split(" ", 1)[0]
    return target


def validate_internal_links(root: Path, markdown_files: list[Path]) -> list[str]:
    errors: list[str] = []
    for document in markdown_files:
        content = document.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK_RE.findall(content):
            target = clean_link_target(raw_target)
            if is_external_target(target):
                continue
            target_path = (document.parent / target).resolve()
            if not target_path.exists():
                relative_doc = document.relative_to(root)
                errors.append(f"{relative_doc}: broken local link -> {raw_target}")
    return errors


def validate_required_documents(root: Path) -> list[str]:
    return [
        f"missing required document: {relative_path}"
        for relative_path in REQUIRED_DOCUMENTS
        if not (root / relative_path).is_file()
    ]


def validate_required_terms(root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path, terms in REQUIRED_TERMS.items():
        document = root / relative_path
        if not document.is_file():
            continue
        content = document.read_text(encoding="utf-8")
        for term in terms:
            if term not in content:
                errors.append(f"{relative_path}: missing required contract term {term!r}")
    return errors


def maintained_markdown_files(root: Path) -> list[Path]:
    """Return first-party maintained docs, excluding archives and dependencies.

    The repository contains node_modules, virtual environments and historical
    archive material with third-party or intentionally stale README links.
    Validating those files would turn a project-documentation check into a
    dependency-integrity scanner and obscure actionable failures.
    """

    candidates: set[Path] = set()
    for relative_path in ROOT_MARKDOWN_DOCUMENTS:
        path = root / relative_path
        if path.is_file():
            candidates.add(path)

    for relative_directory in ("docs", "data/question-bank"):
        directory = root / relative_directory
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.md"):
            relative_parts = path.relative_to(root).parts
            if "archive" in relative_parts:
                continue
            candidates.add(path)
    return sorted(candidates)


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not (root / ".git").exists():
        print(f"error: repository root does not contain .git: {root}", file=sys.stderr)
        return 2

    markdown_files = maintained_markdown_files(root)
    errors = [
        *validate_required_documents(root),
        *validate_required_terms(root),
        *validate_internal_links(root, markdown_files),
    ]
    if errors:
        print("Project documentation validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "Project documentation validation passed: "
        f"{len(REQUIRED_DOCUMENTS)} required documents, "
        f"{sum(len(items) for items in REQUIRED_TERMS.values())} contract terms, "
        f"{len(markdown_files)} Markdown files scanned."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
