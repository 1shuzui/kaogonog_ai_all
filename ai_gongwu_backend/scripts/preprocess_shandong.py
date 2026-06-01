#!/usr/bin/env python3
"""Pre-process Shandong docx to standard format expected by import_question_bank.py.

Converts:
    第X题\n1. 题干
to:
    题号：SD-{YYYYMMDD}-{SYSTEM}-{QN}\n1. 题干
"""

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DOCX = REPO_ROOT.parent / "山东公务员真题库（V7详细得分标准版）.docx"
OUTPUT_PATH = REPO_ROOT.parent / "山东公务员真题库_normalized.txt"

CN_NUM_MAP = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

SYSTEM_ALIASES = {
    "公安": "GA",
    "监狱": "JY",
    "省考": "SK",
    "选调": "XD",
}


def extract_docx_text(input_path: Path) -> str:
    with zipfile.ZipFile(input_path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    lines: list[str] = []
    for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
        parts = [node.text or "" for node in paragraph.findall(".//w:t", WORD_NAMESPACE)]
        line = "".join(parts).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def parse_chinese_num(text: str) -> int:
    num = text.removeprefix("第").removesuffix("题")
    return CN_NUM_MAP.get(num, 0)


def detect_system(header: str) -> str:
    for cn, abbr in SYSTEM_ALIASES.items():
        if cn in header:
            return abbr
    return "QT"


HEADER_PATTERN = re.compile(
    r"^(20\d{2}年\d{1,2}月\d{1,2}日(?:[上中下]午)?[^\n]*山东[^\n]*面试题[^\n]*)$",
    re.MULTILINE,
)

Q_BOUNDARY_PATTERN = re.compile(r"(第[一二三四五六七八九十]+题)\s*\n\s*(1\.\s*题干)")


def extract_date(text: str) -> str:
    m = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", text)
    if not m:
        return "00000000"
    date = f"{int(m.group(1)):04d}{int(m.group(2)):02d}{int(m.group(3)):02d}"
    if "下午" in text or "晚上" in text:
        period = "P"
    elif "上午" in text or "中午" in text:
        period = "A"
    else:
        period = "X"
    return f"{date}{period}"


def preprocess() -> str:
    text = extract_docx_text(SOURCE_DOCX)
    text = text.replace("\r", "\n")

    # Find all question boundaries across entire text
    q_matches = list(Q_BOUNDARY_PATTERN.finditer(text))
    if not q_matches:
        raise RuntimeError("No question boundaries (第X题 + 1. 题干) found")

    # Find all date headers for backward context lookup
    all_headers = [(m.start(), m.end(), re.sub(r"[（()）《》\"\"]", "", m.group(0)).strip())
                   for m in HEADER_PATTERN.finditer(text)]

    output_parts: list[str] = []
    last_header = ""

    for qi, qm in enumerate(q_matches):
        q_start = qm.start()
        q_label = qm.group(1)

        # Find nearest preceding date header
        context_header = ""
        for h_start, h_end, h_clean in all_headers:
            if h_start < q_start:
                context_header = h_clean
            else:
                break

        if not context_header:
            print(f"WARNING: No header found for question at offset {q_start}, question label: {q_label}")
            continue

        date_str = extract_date(context_header)
        system = detect_system(context_header)
        q_num = parse_chinese_num(q_label)
        q_id = f"SD-{date_str}-{system}-{q_num:02d}"

        # Get question block: from this match to next match (or end of text)
        block_end = q_matches[qi + 1].start() if qi + 1 < len(q_matches) else len(text)
        block = text[q_start:block_end].strip()

        # Add suite header if it changed (for grouping in output)
        if context_header != last_header:
            output_parts.append(context_header)
            last_header = context_header

        # Replace 第X题 with 题号：ID
        normalized = re.sub(r"^第[一二三四五六七八九十]+题", f"题号：{q_id}", block, count=1)
        output_parts.append(normalized)

    result = "\n\n".join(output_parts)
    print(f"Preprocessed {len(set(h for _, _, h in all_headers))} unique suites, {len(q_matches)} questions")
    return result


if __name__ == "__main__":
    normalized = preprocess()
    OUTPUT_PATH.write_text(normalized, encoding="utf-8")
    print(f"Output written to: {OUTPUT_PATH}")

    # Show first question as verification
    lines = normalized.split("\n")
    print("\nFirst 15 lines:")
    for line in lines[:15]:
        print(f"  {line}")
