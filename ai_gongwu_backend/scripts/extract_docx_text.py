#!/usr/bin/env python3
"""从 .docx 提取纯文本，输出与现有 .extracted.txt 一致的段落拼接格式。"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from xml.etree import ElementTree


WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def extract_docx_text(input_path: str | Path) -> str:
    """读取 .docx 中的段落文本，并按行拼接。"""

    docx_path = Path(input_path)
    with zipfile.ZipFile(docx_path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))

    lines: list[str] = []
    for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
        parts = [node.text or "" for node in paragraph.findall(".//w:t", WORD_NAMESPACE)]
        line = "".join(parts).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def default_output_path(input_path: str | Path) -> Path:
    """为输入文档生成默认输出路径。"""

    docx_path = Path(input_path)
    return docx_path.with_suffix(".extracted.txt")


def write_extracted_text(input_path: str | Path, output_path: str | Path | None = None) -> Path:
    """提取并写出文本文件。"""

    resolved_output = Path(output_path) if output_path is not None else default_output_path(input_path)
    resolved_output.write_text(extract_docx_text(input_path), encoding="utf-8")
    return resolved_output


def build_argument_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""

    parser = argparse.ArgumentParser(description="从 .docx 提取纯文本。")
    parser.add_argument("input_docx", help="输入 .docx 文件路径")
    parser.add_argument("output_txt", nargs="?", help="输出 .extracted.txt 路径")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""

    args = build_argument_parser().parse_args(argv)
    output_path = write_extracted_text(args.input_docx, args.output_txt)
    print(f"已生成提取文本: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
