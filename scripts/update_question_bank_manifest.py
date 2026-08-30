#!/usr/bin/env python3
"""更新外置题库源文档清单和 SHA-256 校验记录。

源 DOCX 保存在仓库外，清单是题源归档与可重复导入之间的稳定边界。脚本只
扫描传入归档目录中的文件，不会移动、删除或修改任何源文档。
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


BATCHES = (
    {
        "profile": "medical_general",
        "source_dir": "medical_general",
        "source_label": "通用100题_最终版",
        "province": "全国",
        "subcategory": "通用医疗卫生题库",
        "expected_source_file_count": 1,
        "expected_question_count": 100,
        "missing_source_ids": [],
    },
    {
        "profile": "shandong_medical",
        "source_dir": "shandong_medical",
        "source_label": "山东新_最终版",
        "province": "山东",
        "subcategory": "山东省",
        "expected_source_file_count": 137,
        "expected_question_count": 259,
        "missing_source_ids": [],
    },
    {
        "profile": "jiangsu_medical",
        "source_dir": "jiangsu_medical",
        "source_label": "江苏新_最终版",
        "province": "江苏",
        "subcategory": "江苏省",
        "expected_source_file_count": 71,
        "expected_question_count": 187,
        "missing_source_ids": ["江苏新套03"],
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_files(source_root: Path, source_dir: str) -> list[Path]:
    directory = source_root / source_dir
    return sorted(
        (path for path in directory.iterdir() if path.is_file()),
        key=lambda path: path.name,
    )


def update_inventory(inventory_path: Path, archive_root: Path, records: list[dict]) -> None:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    old_items = inventory.get("items", [])
    new_paths = {record["archivePath"] for record in records}
    retained_items = [item for item in old_items if item.get("archivePath") not in new_paths]
    inventory["items"] = retained_items + records
    inventory["sourceBatches"] = [
        {
            "profile": batch["profile"],
            "sourceDirectory": str(archive_root / batch["source_dir"]),
            "sourceLabel": batch["source_label"],
            "province": batch["province"],
            "examSubcategory": batch["subcategory"],
            "expectedSourceFileCount": batch["expected_source_file_count"],
            "actualSourceFileCount": sum(
                1 for record in records if record["profile"] == batch["profile"]
            ),
            "expectedQuestionCount": batch["expected_question_count"],
            "missingSourceIds": batch["missing_source_ids"],
            "note": (
                "缺失源文件按题源清单记录，不计入解析失败。"
                if batch["missing_source_ids"]
                else "源文件数量与题库导入验收口径一致。"
            ),
        }
        for batch in BATCHES
    ]
    inventory_path.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def update_checksums(checksum_path: Path, records: list[dict]) -> None:
    existing: dict[str, str] = {}
    if checksum_path.exists():
        for line in checksum_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            digest, archive_path = line.split(None, 1)
            existing[archive_path.strip()] = digest
    for record in records:
        existing[record["archivePath"]] = record["sha256"]
    lines = [f"{digest}  {archive_path}" for archive_path, digest in sorted(existing.items())]
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_records(source_root: Path) -> list[dict]:
    records: list[dict] = []
    for batch in BATCHES:
        for path in source_files(source_root, batch["source_dir"]):
            relative_name = f"{batch['source_dir']}/{path.name}"
            archive_path = source_root / relative_name
            records.append(
                {
                    "name": relative_name,
                    "originalRepoPath": (
                        "C:/Users/Administrator/Desktop/项目总的/考公项目资料/"
                        f"{batch['source_label']}/{path.name}"
                    ),
                    "archivePath": str(archive_path),
                    "profile": batch["profile"],
                    "category": "question-bank-source",
                    "size": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "note": "医疗卫生题库原始源文档，仓库保留索引，源文件不提交 Git",
                }
            )
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive-root",
        type=Path,
        default=Path("/home/quyu/doc_kaogong/question-bank/source"),
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path("data/question-bank/inventory.json"),
    )
    parser.add_argument(
        "--checksums",
        type=Path,
        default=Path("data/question-bank/checksums.sha256"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = build_records(args.archive_root)
    expected_actual = sum(
        batch["expected_source_file_count"] - len(batch["missing_source_ids"])
        for batch in BATCHES
    )
    if len(records) != expected_actual:
        raise SystemExit(
            f"医疗卫生源文件数量不符合实际清单：发现 {len(records)}，"
            f"期望 {expected_actual}（缺失源文件按清单记录）"
        )
    update_inventory(args.inventory, args.archive_root, records)
    update_checksums(args.checksums, records)
    print(f"updated {len(records)} source records")


if __name__ == "__main__":
    main()
