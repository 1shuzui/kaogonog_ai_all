#!/usr/bin/env python3
"""把题库提取文本导入为后端可读取的结构化 JSON。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
QUESTION_ASSET_ROOT = BACKEND_ROOT / "assets" / "questions"
REGRESSION_SAMPLE_ROOT = BACKEND_ROOT / "assets" / "regression_samples"


@dataclass(frozen=True)
class ImportProfile:
    """导入 profile 配置。"""

    name: str
    default_province: str
    question_output_dir: Path
    sample_output_dir: Path
    summary_path: Path
    regression_sample_base_path: str
    source_files: tuple[Path, ...]
    source_priority: dict[str, int]


def normalize_profile_key(raw_name: str) -> str:
    """把 profile 名称规整成适合目录名和 CLI 的 key。"""

    normalized = re.sub(r"\s+", "_", raw_name.strip().lower())
    normalized = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", normalized)
    return normalized.strip("_")


def build_source_priority(source_files: tuple[Path, ...]) -> dict[str, int]:
    """按声明顺序生成去重优先级，越靠前优先级越高。"""

    total = len(source_files)
    return {path.name: total - index for index, path in enumerate(source_files)}


def resolve_cli_path(raw_path: str | Path) -> Path:
    """解析 CLI 传入的路径，优先按当前工作目录，其次回退到仓库根目录。"""

    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path.resolve()

    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    repo_candidate = (REPO_ROOT / path).resolve()
    if repo_candidate.exists():
        return repo_candidate

    return cwd_candidate


def build_runtime_profile(
    profile_name: str,
    province: str,
    source_files: list[str | Path],
) -> ImportProfile:
    """根据 CLI 参数构造一个临时 profile，适合未来新增地区直接导入。"""

    profile_key = normalize_profile_key(profile_name)
    if not profile_key:
        raise ValueError("profile_name 不能为空")

    province_name = province.strip()
    if not province_name:
        raise ValueError("province 不能为空")

    resolved_source_files = tuple(resolve_cli_path(path) for path in source_files)
    if not resolved_source_files:
        raise ValueError("至少需要一个 source_file")

    question_output_dir = QUESTION_ASSET_ROOT / f"generated_{profile_key}"
    sample_output_dir = REGRESSION_SAMPLE_ROOT / f"generated_{profile_key}"
    return ImportProfile(
        name=profile_key,
        default_province=province_name,
        question_output_dir=question_output_dir,
        sample_output_dir=sample_output_dir,
        summary_path=question_output_dir / "import_summary.txt",
        regression_sample_base_path=f"assets/regression_samples/generated_{profile_key}",
        source_files=resolved_source_files,
        source_priority=build_source_priority(resolved_source_files),
    )


IMPORT_PROFILES = {
    "hunan": ImportProfile(
        name="hunan",
        default_province="湖南",
        question_output_dir=BACKEND_ROOT / "assets" / "questions" / "generated_hunan",
        sample_output_dir=BACKEND_ROOT / "assets" / "regression_samples" / "generated_hunan",
        summary_path=BACKEND_ROOT / "assets" / "questions" / "generated_hunan" / "import_summary.txt",
        regression_sample_base_path="assets/regression_samples/generated_hunan",
        source_files=(
            REPO_ROOT / "湖南-2020-乡镇岗、遴选岗全.extracted.txt",
            REPO_ROOT / "湖南-监狱-2020.extracted.txt",
            REPO_ROOT / "湖南-税务系统补录-2020-816.extracted.txt",
            REPO_ROOT / "湖南-2020-通用岗.extracted.txt",
        ),
        source_priority={
            "湖南-2020-乡镇岗、遴选岗全.extracted.txt": 100,
            "湖南-监狱-2020.extracted.txt": 90,
            "湖南-税务系统补录-2020-816.extracted.txt": 80,
            "湖南-2020-通用岗.extracted.txt": 70,
        },
    ),
    "anhui": ImportProfile(
        name="anhui",
        default_province="安徽",
        question_output_dir=BACKEND_ROOT / "assets" / "questions" / "generated_anhui",
        sample_output_dir=BACKEND_ROOT / "assets" / "regression_samples" / "generated_anhui",
        summary_path=BACKEND_ROOT / "assets" / "questions" / "generated_anhui" / "import_summary.txt",
        regression_sample_base_path="assets/regression_samples/generated_anhui",
        source_files=(
            REPO_ROOT / "2020-2025第二批次完全版.extracted.txt",
        ),
        source_priority={
            "2020-2025第二批次完全版.extracted.txt": 100,
        },
    ),
}

ACTIVE_PROFILE = IMPORT_PROFILES["hunan"]
QUESTION_OUTPUT_DIR = ACTIVE_PROFILE.question_output_dir
SAMPLE_OUTPUT_DIR = ACTIVE_PROFILE.sample_output_dir
SUMMARY_PATH = ACTIVE_PROFILE.summary_path
REGRESSION_SAMPLE_BASE_PATH = ACTIVE_PROFILE.regression_sample_base_path
SOURCE_FILES = list(ACTIVE_PROFILE.source_files)
SOURCE_PRIORITY = dict(ACTIVE_PROFILE.source_priority)
DEFAULT_PROVINCE = ACTIVE_PROFILE.default_province


def activate_profile(profile_name: str | ImportProfile) -> ImportProfile:
    """切换当前导入 profile，并同步兼容全局常量。"""

    global ACTIVE_PROFILE
    global QUESTION_OUTPUT_DIR
    global SAMPLE_OUTPUT_DIR
    global SUMMARY_PATH
    global REGRESSION_SAMPLE_BASE_PATH
    global SOURCE_FILES
    global SOURCE_PRIORITY
    global DEFAULT_PROVINCE

    ACTIVE_PROFILE = (
        IMPORT_PROFILES[profile_name]
        if isinstance(profile_name, str)
        else profile_name
    )
    QUESTION_OUTPUT_DIR = ACTIVE_PROFILE.question_output_dir
    SAMPLE_OUTPUT_DIR = ACTIVE_PROFILE.sample_output_dir
    SUMMARY_PATH = ACTIVE_PROFILE.summary_path
    REGRESSION_SAMPLE_BASE_PATH = ACTIVE_PROFILE.regression_sample_base_path
    SOURCE_FILES = list(ACTIVE_PROFILE.source_files)
    SOURCE_PRIORITY = dict(ACTIVE_PROFILE.source_priority)
    DEFAULT_PROVINCE = ACTIVE_PROFILE.default_province
    return ACTIVE_PROFILE

SECTION_HEADERS = (
    "题干",
    "题型定位",
    "核心观点",
    "核心观点（多维）",
    "核心采分基准",
    "核心采分基准表达",
    "核心采分基准答案",
    "多角度同义表述库",
    "加分点",
    "加分点（创新思维）",
    "得分标准",
    "扣分标准",
    "AI评分结构化数据",
    "AI评分使用的结构化数据",
    "全局统一表达",
    "全局统一仪态分",
    "全局统一表达仪态分",
    "总分计算规则",
    "本题总分计算规则",
    "检索标签",
)
SECTION_HEADERS_FOR_NORMALIZATION = tuple(sorted(SECTION_HEADERS, key=len, reverse=True))
SECTION_HEADER_ALTERNATION = "|".join(re.escape(header) for header in SECTION_HEADERS_FOR_NORMALIZATION)
SECTION_INDEX_ALIASES = {
    "一": "1",
    "二": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
    "十": "10",
    "十一": "11",
    "十二": "12",
}
SECTION_PATTERN = re.compile(
    r"(?:^|\n)\s*(\d{1,2})[.、 ]\s*"
    r"(题干|题型定位|核心观点(?:（多维）)?|核心采分基准(?:答案|表达)?|多角度同义表述库|"
    r"加分点(?:（创新思维）)?|得分标准|扣分标准|AI评分(?:使用的)?结构化数据|"
    r"全局统一(?:表达(?:仪态分)?|仪态分)|(?:本题)?总分计算规则|检索标签)"
)
QUESTION_ID_PATTERN = re.compile(r"题号[:：]\s*([^\n（(]+)")
HEADER_PATTERN = re.compile(r"题号[:：]\s*([^\n（(]+)(?:（([^）]+)）)?")
FIELD_PATTERNS = {
    "type": [
        r"题型[:：]\s*([^；。\n]+)",
        r"题型信息[:：]\s*([^；。\n]+)",
        r"题型定位\s*([^。\n]+)",
    ],
    "province": [
        r"适用省份[:：]\s*([^，；。\n]+)",
        r"适用地区[:：]\s*([^，；。\n]+)",
        r"适用[:：]\s*([^，；。\n]+)",
    ],
    "full_score": [
        r"满分[:：]\s*(\d+(?:\.\d+)?)分",
        r"赋分\s*(\d+(?:\.\d+)?)分",
    ],
    "core_keywords": [
        r"核心识别词(?:（[^）]*）)?[:：]\s*([^；。\n]+)",
        r"核心词[=＝:：]\s*([^；。\n]+)",
    ],
    "strong_keywords": [
        r"强关联识别词(?:（[^）]*）)?[:：]\s*([^；。\n]+)",
        r"强关联词[=＝:：]\s*([^；。\n]+)",
    ],
    "weak_keywords": [
        r"弱关联识别词(?:（[^）]*）)?[:：]\s*([^；。\n]+)",
        r"弱关联词[=＝:：]\s*([^；。\n]+)",
    ],
    "bonus_keywords": [
        r"加分触发词(?:（[^）]*）)?[:：]\s*([^；。\n]+)",
    ],
    "penalty_keywords": [
        r"扣分触发词(?:（[^）]*）)?[:：]\s*([^；。\n]+)",
        r"失分要点[:：]\s*([^；。\n]+)",
    ],
}
SCORE_MARK_PATTERN = re.compile(r"（\d+(?:\.\d+)?分）")
DEDUCTION_MARK_PATTERN = re.compile(r"扣\d+(?:\.\d+)?(?:[—-]\d+(?:\.\d+)?)?分")
EXPLICIT_SCORED_ITEM_PATTERN = re.compile(
    r"(?P<title>[^\s：:；;，,。、“”\"'（）()]{1,16})\s*(?P<score>（\d+(?:\.\d+)?分）)\s*(?P<colon>[：:]?)"
)
EXPLICIT_DIMENSION_TITLE_PATTERN = re.compile(
    r"^(?P<title>[^\s：:；;，,。、“”\"'（）()]{1,16})\s*(?P<score>（\d+(?:\.\d+)?分）)\s*(?P<colon>[：:]?)"
)
LEADING_NOTE_PATTERN = re.compile(r"^\s*(?:（[^）]*）\s*)+")
TRAILING_TOTAL_SCORE_PATTERN = re.compile(r"(?:[；;。]\s*)?总分\s*\d+(?:\.\d+)?分.*$")
TYPE_PREFIX_PATTERN = re.compile(r"^(?:题型信息|题型定位|题型)[:：]\s*")
TYPE_SCORE_PATTERN = re.compile(r"赋分\s*\d+(?:\.\d+)?\s*分")
TYPE_METADATA_PATTERN = re.compile(r"[，,]\s*(?:适用省份|适配岗位|满分)[:：].*$")
TYPE_NOISE_MARKERS = (
    "组合1：",
    "组合2：",
    "组合3：",
    "组合4：",
    "组合5：",
    "选择理由：",
    "核心沟通逻辑",
    "题库说明",
    "适配场景",
    "AI智能评分",
    "核心特色",
    "使用规范",
    "结构化数据",
    "支持自动核算总分",
    "支持AI智能采分",
    "仪态分计入",
)
TAG_NOISE_MARKERS = (
    "题库说明",
    "适配场景",
    "AI智能评分",
    "核心特色",
    "使用规范",
    "结构化数据",
    "支持自动核算总分",
    "支持AI智能采分",
    "仪态分计入",
)
TAG_HARD_STOP_MARKERS = TAG_NOISE_MARKERS + (
    "MERGEFORMAT",
    "Version",
    "SimSun",
    "GB2312",
    "Regular",
    "FZSJ-",
    "Default Paragraph Font",
    "默认段落字体",
    "普通表格",
    "正文文本",
)
TAG_STYLE_NOISE_TOKENS = {
    "MERGEFORMAT",
    "Version",
    "SimSun",
    "GB2312",
    "Regular",
    "Default Paragraph Font",
    "默认段落字体",
    "普通表格",
    "正文文本",
    "标题",
}
QUESTION_TRAILING_SCORE_PATTERN = re.compile(r"[（(]\s*(\d+(?:\.\d+)?)\s*分\s*[）)]\s*$")
HEADER_ASSIGNED_SCORE_PATTERN = re.compile(r"赋分\s*(\d+(?:\.\d+)?)\s*分")
SCORING_TOTAL_PATTERN = re.compile(r"总分\s*(\d+(?:\.\d+)?)\s*分")
CALCULATED_FULL_SCORE_PATTERN = re.compile(
    r"本题得分\s*[=＝]\s*得分标准得分\s*[（(]\s*(\d+(?:\.\d+)?)\s*分\s*[）)]"
)

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.utils.encoding import ensure_utf8_stdio
from app.models.schemas import QuestionDefinition
from app.services.scoring.calculator import (
    apply_post_processing,
    build_deterministic_stage_two_payload,
    prepare_evidence_packet,
)

ensure_utf8_stdio()


@dataclass
class ParsedQuestion:
    """单道题在导入阶段的临时结构。"""

    data: dict
    source_path: Path
    block_length: int


@dataclass(frozen=True)
class GeneratedSample:
    """程序化生成后的回归样本。"""

    label: str
    filename: str
    text: str
    score: float
    strategy: str
    count: int
    trim_chars: int | None
    sanitization: str
    oral: bool = False


def normalize_question_id(raw_id: str) -> str:
    """统一题号格式，便于落库、去重和生成文件名。"""

    normalized = raw_id.strip().upper()
    normalized = re.sub(r"[\s_]+", "-", normalized)
    normalized = re.sub(r"^([A-Z]{2,})(\d{6,}(?:[A-Z]+)?)", r"\1-\2", normalized)
    normalized = re.sub(r"-+", "-", normalized)
    return normalized.strip("-")


def normalize_section_index(raw_index: str) -> str:
    """把中文/数字 section 序号统一成阿拉伯数字。"""

    index = raw_index.strip()
    if index.isdigit():
        return str(int(index))
    return SECTION_INDEX_ALIASES.get(index, index)


def normalize_source_text(raw_text: str, source_name: str) -> str:
    """把文档提取文本先整理成更容易正则处理的形态。"""

    text = raw_text.replace("\r", "\n").replace("\u3000", " ")
    text = text.replace("－", "-").replace("＋", "+").replace("／", "/")
    text = re.sub(r"\n+", "\n", text)

    # `.doc` 粗提取结果会把题号拆成多行，这里先补回正常 question_id。
    if source_name == "湖南-税务系统补录-2020-816.extracted.txt":
        text = re.sub(
            r"题号：\s*HN\s*\n\s*20200816\s*\n\s*0?([1-9])",
            lambda match: f"题号：HN-20200816-0{match.group(1)}",
            text,
        )
        text = re.sub(
            r"湖南省考税务系统补录面试题库\s*题号：\s*HN\s*\n\s*0?([2-9])（",
            lambda match: (
                "湖南省考税务系统补录面试题库 题号："
                f"HN-20200816-0{match.group(1)}（"
            ),
            text,
        )

    text = re.sub(
        r"(题号[:：]\s*)([^\n（(]+)",
        lambda match: f"{match.group(1)}{normalize_question_id(match.group(2))}",
        text,
    )
    text = re.sub(
        rf"第([一二三四五六七八九十]{{1,3}}|\d{{1,2}})题[:：][^\S\n]*({SECTION_HEADER_ALTERNATION})",
        lambda match: f"{normalize_section_index(match.group(1))}. {match.group(2)}",
        text,
    )

    # 有些文档把 “1 + 换行 + 题干” 拆开了，这里统一修成 “1. 题干”。
    for header in SECTION_HEADERS_FOR_NORMALIZATION:
        text = re.sub(
            rf"([^\n\s\d])[^\S\n]*(\d{{1,2}})[、.][^\S\n]*{re.escape(header)}",
            rf"\1\n\2. {header}",
            text,
        )
        text = re.sub(
            rf"(\d)[^\S\n]+(\d{{1,2}})[、.][^\S\n]*{re.escape(header)}",
            rf"\1\n\2. {header}",
            text,
        )
        text = re.sub(
            rf"(?<!\d)(\d{{1,2}})\s*\n\s*{re.escape(header)}",
            rf"\1. {header}",
            text,
        )
        text = re.sub(
            rf"\s+(\d{{1,2}}\.\s*{re.escape(header)})",
            r"\n\1",
            text,
        )
        text = re.sub(
            rf"\s+(\d{{1,2}})[、.]\s*{re.escape(header)}",
            rf"\n\1. {header}",
            text,
        )

    return text


def infer_source_document(source_path: Path) -> str:
    """把 extracted 文本映射回用户真正提供的源文档名。"""

    stem = source_path.name.removesuffix(".extracted.txt")
    for suffix in (".docx", ".doc"):
        candidate = REPO_ROOT / f"{stem}{suffix}"
        if candidate.exists():
            return candidate.name
    return source_path.name


def iter_question_blocks(text: str) -> list[str]:
    """按题号切分题目块。"""

    matches = list(QUESTION_ID_PATTERN.finditer(text))
    blocks: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append(text[start:end].strip())
    return blocks


def canonical_section_name(raw_name: str) -> str:
    """把不同写法归并到统一节名。"""

    if raw_name.startswith("核心观点"):
        return "核心观点（多维）"
    if raw_name.startswith("核心采分基准"):
        return "核心采分基准答案"
    if raw_name.startswith("加分点"):
        return "加分点（创新思维）"
    if raw_name.startswith("AI评分"):
        return "AI评分结构化数据"
    if raw_name.startswith("全局统一表达") or raw_name.startswith("全局统一仪态分"):
        return "全局统一表达仪态分"
    if raw_name.startswith("总分计算规则") or raw_name.startswith("本题总分计算规则"):
        return "本题总分计算规则"
    return raw_name


def extract_sections(block: str) -> dict[str, str]:
    """抽出 1~12 节的正文内容。"""

    sections: dict[str, str] = {}
    matches = list(SECTION_PATTERN.finditer(block))
    for index, match in enumerate(matches):
        section_name = canonical_section_name(match.group(2))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        sections[section_name] = block[start:end].strip()
    return sections


def extract_field(text: str, patterns: list[str]) -> str:
    """按多个候选正则提取字段。"""

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


def extract_score_with_pattern(text: str, pattern: re.Pattern[str]) -> float | None:
    """从文本里提取单个分值。"""

    if not text:
        return None
    match = pattern.search(text)
    if not match:
        return None
    return round(float(match.group(1)), 1)


def choose_consensus_score(
    candidates: list[tuple[str, float]],
    *,
    priority: tuple[str, ...],
) -> float:
    """在多个候选分值中优先选择一致来源，平票时按来源优先级决策。"""

    grouped: dict[float, list[str]] = {}
    for source, value in candidates:
        grouped.setdefault(round(value, 1), []).append(source)

    def source_rank(name: str) -> int:
        try:
            return priority.index(name)
        except ValueError:
            return len(priority)

    score, _ = min(
        grouped.items(),
        key=lambda item: (
            -len(item[1]),
            min(source_rank(source) for source in item[1]),
            item[0],
        ),
    )
    return score


def resolve_full_score(
    *,
    question_text: str,
    header_description: str,
    scoring_section_text: str,
    ai_text: str,
    dimensions: list[dict],
) -> float:
    """综合多个来源决定题目的真实满分，避免被结构化脏值覆盖。"""

    explicit_candidates: list[tuple[str, float]] = []
    for source, value in (
        ("question_text", extract_score_with_pattern(question_text, QUESTION_TRAILING_SCORE_PATTERN)),
        ("header_description", extract_score_with_pattern(header_description, HEADER_ASSIGNED_SCORE_PATTERN)),
        ("scoring_total", extract_score_with_pattern(scoring_section_text, SCORING_TOTAL_PATTERN)),
        ("calc_rule", extract_score_with_pattern(ai_text, CALCULATED_FULL_SCORE_PATTERN)),
    ):
        if value is not None:
            explicit_candidates.append((source, value))

    content_candidates = list(explicit_candidates)
    dimension_total = round(sum(item["score"] for item in dimensions), 1) if dimensions else None
    if dimension_total is not None:
        content_candidates.append(("dimensions", dimension_total))

    if content_candidates:
        return choose_consensus_score(
            content_candidates,
            priority=("question_text", "header_description", "scoring_total", "calc_rule", "dimensions"),
        )

    configured_full_score = extract_field(ai_text, FIELD_PATTERNS["full_score"])
    if configured_full_score:
        return round(float(configured_full_score), 1)

    return dimension_total or 0.0


def split_list(text: str, *, include_whitespace: bool = False) -> list[str]:
    """把“关键词、标签”类字符串拆成列表。"""

    cleaned = re.sub(r"（说明：[^）]*）", "", text).strip()
    if not cleaned:
        return []

    separator = r"[、，,；;/]"
    if include_whitespace:
        separator = r"[、，,；;/\s]+"

    values = []
    seen = set()
    for item in re.split(separator, cleaned):
        value = item.strip().strip("：:；;，,。.!！？-— ")
        if not value or value in seen:
            continue
        values.append(value)
        seen.add(value)
    return values


def is_tag_noise(tag: str) -> bool:
    """过滤 Word 样式碎片、纯数字和明显异常标签。"""

    value = tag.strip()
    if not value:
        return True
    if "面试题库" in value:
        return True
    if "面试题" in value:
        return True
    if any(marker in value for marker in ("题库版", "完整12段", "完整标准", "网友回忆版", "结构化小组")):
        return True
    if value in TAG_STYLE_NOISE_TOKENS:
        return True
    if re.fullmatch(r"\d+(?:\.\d+)?", value):
        return True
    if len(value) > 24:
        return True
    if re.search(r"(MERGEFORMAT|SIMSUN|GB2312|FZSJ-|DEFAULT PARAGRAPH FONT|STYLE|VERSION)", value, re.IGNORECASE):
        return True
    if re.fullmatch(r"[A-Za-z0-9_-]{2,}", value) and not re.search(r"[\u4e00-\u9fff]", value):
        return True
    return False


def extract_type_tags(question_type: str) -> list[str]:
    """从题型文本里提取一小组可读标签，供标签兜底重建。"""

    if not question_type:
        return []

    base = re.sub(r"（[^）]*适配[^）]*）", "", question_type)
    pieces = re.split(r"[·+（）()/\s]+", base)
    values: list[str] = []
    seen = set()
    for piece in pieces:
        value = piece.strip().rstrip("类")
        if not value or is_tag_noise(value) or value in seen:
            continue
        values.append(value)
        seen.add(value)
    return values


def build_fallback_tags(question_type: str, keyword_groups: list[list[str]] | None = None) -> list[str]:
    """当检索标签为空或疑似污染时，用题型和关键词重建一组精简标签。"""

    values: list[str] = []
    seen = set()

    for tag in extract_type_tags(question_type):
        if tag not in seen:
            values.append(tag)
            seen.add(tag)

    for group in keyword_groups or []:
        for keyword in group:
            value = keyword.strip()
            if not value or is_tag_noise(value) or len(value) > 12 or value in seen:
                continue
            values.append(value)
            seen.add(value)
            if len(values) >= 8:
                return values

    return values[:8]


def build_tags(
    text: str,
    *,
    question_type: str = "",
    keyword_groups: list[list[str]] | None = None,
) -> list[str]:
    """标签单独清洗，去掉跨块残留和 Word 样式垃圾。"""

    text = cut_text_before_markers(text, TAG_HARD_STOP_MARKERS)
    tags = [
        tag
        for tag in split_list(text, include_whitespace=True)
        if tag and not is_tag_noise(tag)
    ]
    if not tags or len(tags) > 12:
        fallback = build_fallback_tags(question_type, keyword_groups)
        if fallback:
            return fallback
    return tags[:12]


def cut_text_before_markers(text: str, markers: tuple[str, ...]) -> str:
    """Trim noisy trailing metadata once any marker appears."""

    indices = [text.find(marker) for marker in markers if marker in text]
    if not indices:
        return text
    return text[: min(indices)]


def clean_dimension_fragment(text: str, *, limit: int = 14) -> str:
    """Normalize a short dimension label."""

    value = re.sub(r"^[：:\s]+", "", text.strip())
    value = re.split(r"[：:；;，,。]", value, maxsplit=1)[0]
    value = re.sub(r"\s+", "", value)
    return value[:limit]


def is_explicit_dimension_title(title: str) -> bool:
    """Decide whether a short scored-item prefix is a real dimension title."""

    value = clean_dimension_fragment(title, limit=20)
    if not value or len(value) > 12:
        return False
    if any(
        marker in value
        for marker in (
            "如果",
            "能够",
            "体现",
            "围绕",
            "通过",
            "针对",
            "做到",
            "主要",
            "内容",
        )
    ):
        return False
    return True


def normalize_scored_section_text(section_text: str) -> str:
    """Collapse scored criteria text into one line for parsing."""

    normalized = " ".join(section_text.split())
    normalized = LEADING_NOTE_PATTERN.sub("", normalized)
    normalized = TRAILING_TOTAL_SCORE_PATTERN.sub("", normalized)
    return normalized.strip("；; ")


def parse_scored_items(section_text: str) -> list[str]:
    """从“得分标准”中提取每条评分项。"""

    normalized = normalize_scored_section_text(section_text)
    if not normalized:
        return []

    explicit_matches = []
    for match in EXPLICIT_SCORED_ITEM_PATTERN.finditer(normalized):
        start = match.start("title")
        prefix = normalized[:start].rstrip()
        if prefix and prefix[-1] not in {"\uff1b", ";", "\u3002"}:
            continue
        if is_explicit_dimension_title(match.group("title")):
            explicit_matches.append(match)
    if len(explicit_matches) >= 2:
        items: list[str] = []
        for index, match in enumerate(explicit_matches):
            start = match.start("title")
            end = explicit_matches[index + 1].start("title") if index + 1 < len(explicit_matches) else len(normalized)
            item = normalized[start:end].strip("；; ")
            if item:
                items.append(item)
        return items

    cursor = 0
    items: list[str] = []
    for match in SCORE_MARK_PATTERN.finditer(normalized):
        end = match.end()
        while True:
            note_match = re.match(r"\s*[；;]?\s*（[^）]*）", normalized[end:])
            if not note_match:
                break
            end += note_match.end()

        item = normalized[cursor:end].strip("；; ")
        cursor = end
        if not item or "总分" in item or item.startswith("（"):
            continue
        items.append(item)
    return items


def parse_deduction_items(section_text: str) -> list[str]:
    """从“扣分标准”中提取每条扣分项。"""

    normalized = " ".join(section_text.split())
    cursor = 0
    items: list[str] = []
    for match in DEDUCTION_MARK_PATTERN.finditer(normalized):
        end = match.end()
        while True:
            note_match = re.match(r"\s*[；;]?\s*（[^）]*）", normalized[end:])
            if not note_match:
                break
            end += note_match.end()

        item = normalized[cursor:end].strip("；; ")
        cursor = end
        if not item or item.startswith("（"):
            continue
        items.append(item)
    return items


def extract_score(item_text: str) -> float:
    """提取评分项里的分值。"""

    match = re.search(r"（(\d+(?:\.\d+)?)分）", item_text)
    if not match:
        raise ValueError(f"无法从评分项中提取分值: {item_text}")
    return float(match.group(1))


def split_criterion_title_and_body(criterion_text: str) -> tuple[str, str]:
    """Split `标题（分值）：说明` style criteria into title/body."""

    text = normalize_scored_section_text(criterion_text)
    match = EXPLICIT_DIMENSION_TITLE_PATTERN.match(text)
    if match and is_explicit_dimension_title(match.group("title")):
        title = clean_dimension_fragment(match.group("title"))
        body = text[match.end() :].lstrip("：:；; ").strip()
        return title, body
    return "", text


def infer_dimension_base_name(title: str, criterion_text: str) -> str:
    """Infer the base dimension name before duplicate disambiguation."""

    if title:
        return clean_dimension_fragment(title)

    text = criterion_text
    if "创新" in text or "创意" in text or "亮点" in text:
        return "创新思维"
    if "宣传语" in text or "标语" in text or "口号" in text:
        return "宣传语创意"
    if "出发点" in text:
        return "出发点适配"
    if "词语" in text or "串词" in text:
        return "词语运用"
    if "价值导向" in text or ("价值" in text and "担当" in text):
        return "价值导向"
    if "两个活动方案" in text or "互不重复" in text:
        return "方案设计"
    if "适老化" in text:
        return "适老化设计"
    if "安全保障" in text or ("保障" in text and "安全" in text):
        return "安全保障"
    if any(marker in text for marker in ("流程", "实施", "筹备", "步骤", "排查", "长效机制", "跟进")):
        return "流程执行"
    if "方案" in text or "活动设计" in text:
        return "方案设计"
    if "立意" in text or "主题鲜明" in text:
        return "立意深度"
    if "语言" in text or "表达" in text or "感染力" in text:
        return "语言表达"
    if any(marker in text for marker in ("分析", "解读", "内涵", "实践价值", "政治站位", "意义", "影响", "根源", "理解")):
        return "分析理解"
    if "岗位" in text or "省情" in text or "履职" in text or "基层实际" in text or "结合实际" in text:
        return "岗位适配"
    if any(marker in text for marker in ("沟通", "劝说", "安抚", "回应顾虑", "协调")):
        return "沟通化解"
    if "统筹" in text or "交接" in text:
        return "工作统筹"
    if "案例选取" in text or text.startswith("案例"):
        return "案例适配"
    if "场景" in text or "现场模拟" in text or "宣讲" in text:
        return "场景适配"
    if "契合" in text or "完整逻辑" in text:
        return "整体契合度"
    if "措施" in text or "举措" in text or "路径" in text or "建议" in text or "办法" in text:
        return "对策措施"
    return clean_dimension_fragment(text.split("（", 1)[0].split("，", 1)[0]) or "评分维度"


def infer_dimension_direction_hint(base_name: str, title: str, criterion_text: str) -> str:
    """Try to turn a duplicate base name into a readable direction suffix."""

    cleaned_title = clean_dimension_fragment(title)
    if cleaned_title and cleaned_title != base_name:
        return cleaned_title

    text = criterion_text
    if base_name == "分析理解":
        mappings = (
            (("政治站位", "大局", "方向"), "政治站位"),
            (("内涵", "解读", "阐释"), "内涵解读"),
            (("结合实际", "实践", "落到", "长沙", "本地", "岗位"), "结合实际"),
            (("风险", "问题", "偏差", "短板"), "问题风险"),
        )
    elif base_name == "对策措施":
        mappings = (
            (("履职", "岗位", "基层", "省情", "结合实际"), "履职路径"),
            (("措施", "举措", "办法", "推进", "落实", "抓手"), "具体举措"),
            (("问题", "短板", "堵点"), "问题导向"),
        )
    elif base_name == "流程执行":
        mappings = (
            (("筹备", "准备", "摸排", "通知", "前期"), "前期准备"),
            (("实施", "现场", "组织", "开展", "排查"), "现场实施"),
            (("总结", "反馈", "跟进", "长效", "后续"), "后续跟进"),
        )
    elif base_name == "适老化设计":
        mappings = (
            (("安全", "保障", "风险"), "安全保障"),
            (("原则", "定位", "导向"), "服务原则"),
            (("设计", "适老", "方便", "便民", "无障碍"), "方案设计"),
            (("服务", "细节", "体验"), "服务细节"),
        )
    elif base_name == "沟通化解":
        mappings = (
            (("顾虑", "担心", "情绪", "理解"), "顾虑回应"),
            (("政策", "意义", "价值", "引导"), "价值传递"),
            (("逻辑", "算账", "说明", "解释"), "沟通逻辑"),
            (("配合", "方案", "办理"), "配合方式"),
        )
    elif base_name == "词语运用":
        mappings = (
            (("自然", "融入", "贴切"), "融合表达"),
            (("价值", "担当", "导向"), "价值导向"),
            (("岗位", "省情", "基层"), "岗位适配"),
        )
    elif base_name == "语言表达":
        mappings = (
            (("庄重", "规范", "准确", "流畅"), "表达规范"),
            (("感染", "情感", "打动"), "现场感染"),
            (("口语", "自然", "接地气"), "口语转化"),
        )
    else:
        mappings = ()

    for markers, label in mappings:
        if any(marker in text for marker in markers):
            return label
    return ""


def build_dimensions(scoring_criteria: list[str]) -> list[dict]:
    """从评分标准构造 schema 里的 dimensions 字段。"""

    parsed_items: list[tuple[str, str, str, str]] = []
    for item in scoring_criteria:
        title, body = split_criterion_title_and_body(item)
        base_name = infer_dimension_base_name(title, body or item)
        parsed_items.append((item, title, body, base_name))

    base_counts = Counter(base_name for _, _, _, base_name in parsed_items)
    current_counts: Counter[str] = Counter()
    used_names: set[str] = set()
    dimensions: list[dict[str, Any]] = []
    for item, title, body, base_name in parsed_items:
        current_counts[base_name] += 1
        if base_counts[base_name] == 1:
            name = base_name
        else:
            hint = infer_dimension_direction_hint(base_name, title, body or item)
            if hint:
                name = f"{base_name}（{hint}）"
            else:
                name = f"{base_name}（方向{current_counts[base_name]}）"

        while name in used_names:
            current_counts[base_name] += 1
            name = f"{base_name}（方向{current_counts[base_name]}）"
        used_names.add(name)
        dimensions.append(
            {
                "name": name,
                "score": extract_score(item),
            }
        )
    return dimensions


def scale_dimensions_to_full_score(dimensions: list[dict], target_total: float) -> list[dict]:
    """把维度分值按比例缩放到目标总分。"""

    current_total = round(sum(item["score"] for item in dimensions), 1)
    if not dimensions or abs(current_total - target_total) < 0.1:
        return dimensions

    scaled = []
    for item in dimensions:
        scaled.append(
            {
                "name": item["name"],
                "score": round(item["score"] * target_total / current_total, 1),
            }
        )

    diff = round(target_total - sum(item["score"] for item in scaled), 1)
    if diff != 0:
        scaled[-1]["score"] = round(max(scaled[-1]["score"] + diff, 0.1), 1)

    return scaled


def effective_length(text: str) -> int:
    """按评分器口径统计有效长度。"""

    return len(re.sub(r"\s+", "", text or ""))


def normalize_reference_answer(text: str) -> str:
    """把高分参考答案整理成便于切句和降级的形态。"""

    normalized = text.replace("\r", "\n")
    normalized = re.sub(r"\n+", "\n", normalized)
    normalized = re.sub(r"(?<!\n)(首先|其次|再次|最后|另外|同时|一是|二是|三是|四是|五是|六是)", r"\n\1", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()


def split_answer_sentences(text: str) -> list[str]:
    """把参考答案切成可重组的句子列表。"""

    normalized = normalize_reference_answer(text)
    raw_sentences = re.split(r"(?<=[。！？；])\s*", normalized)
    sentences: list[str] = []
    for raw_sentence in raw_sentences:
        sentence = raw_sentence.strip()
        if not sentence:
            continue
        if (
            sentence.startswith("（")
            and sentence.endswith("）")
            and any(marker in sentence for marker in ("场景", "背景", "提示"))
        ):
            continue
        if effective_length(sentence) < 10:
            continue
        sentences.append(sentence)
    return sentences


def genericize_keyword(keyword: str) -> str:
    """把题库里的强识别词替换成更泛化的说法，主动拉开分档。"""

    if any(token in keyword for token in ("企业", "商户", "主体", "群众", "农民", "居民", "学生", "旅客", "游客", "老人")):
        return "相关群体"
    if any(token in keyword for token in ("部门", "机关", "税务", "公安", "交警", "监狱", "单位", "政府")):
        return "有关部门"
    if any(token in keyword for token in ("政策", "战略", "要求", "理念", "精神")):
        return "有关要求"
    if any(token in keyword for token in ("平台", "系统", "机制", "链", "模式")):
        return "相关机制"
    if any(token in keyword for token in ("环境", "建设", "治理", "服务", "发展", "执法")):
        return "相关工作"
    return "相关内容"


def keywords_for_sanitization(question_data: dict[str, Any], level: str) -> list[str]:
    """按强度决定要泛化哪些关键词。"""

    if level == "none":
        keywords: list[str] = []
    elif level == "light":
        keywords = question_data["bonusKeywords"] + question_data["weakKeywords"][: max(1, len(question_data["weakKeywords"]) // 2)]
    elif level == "medium":
        keywords = (
            question_data["bonusKeywords"]
            + question_data["weakKeywords"]
            + question_data["strongKeywords"][: max(1, len(question_data["strongKeywords"]) // 2)]
        )
    else:
        keywords = (
            question_data["coreKeywords"]
            + question_data["strongKeywords"]
            + question_data["weakKeywords"]
            + question_data["bonusKeywords"]
        )

    deduplicated = []
    seen = set()
    for keyword in sorted(keywords, key=len, reverse=True):
        if not keyword or keyword in seen:
            continue
        deduplicated.append(keyword)
        seen.add(keyword)
    return deduplicated


def apply_keyword_sanitization(text: str, question_data: dict[str, Any], level: str) -> str:
    """用泛化替换主动削弱关键词命中率。"""

    sanitized = text
    for keyword in keywords_for_sanitization(question_data, level):
        sanitized = sanitized.replace(keyword, genericize_keyword(keyword))
    return sanitized


def soften_low_sample_tone(text: str) -> str:
    """低档样本适度去掉完整结构，让答案更像“方向对但不够成熟”。"""

    softened = text
    softened = softened.replace("首先", "先")
    softened = softened.replace("其次", "再")
    softened = softened.replace("再次", "还有")
    softened = softened.replace("最后", "总的看")
    softened = softened.replace("一是", "一个是")
    softened = softened.replace("二是", "再就是")
    softened = softened.replace("三是", "还有")
    softened = softened.replace("四是", "另外")
    return softened


def clean_generated_sample_text(text: str) -> str:
    """收尾清理，避免替换后出现多余空格和重复标点。"""

    cleaned = text.replace("\u3000", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[，、]{2,}", "，", cleaned)
    cleaned = re.sub(r"[。！？；]{2,}", "。", cleaned)
    cleaned = cleaned.replace(" ，", "，").replace(" 。", "。")
    return cleaned.strip()


def is_measure_sentence(sentence: str) -> bool:
    """识别明显的措施/流程句。"""

    return bool(
        re.search(r"^(首先|其次|再次|最后|一是|二是|三是|四是|五是|六是|另外|同时)", sentence)
        or any(marker in sentence for marker in ("建议", "措施", "做法", "路径", "抓好", "推进", "完善", "建立", "健全", "落实"))
    )


def is_innovation_sentence(sentence: str) -> bool:
    """识别亮点/创新类句子。"""

    return any(marker in sentence for marker in ("创新", "亮点", "特色", "探索", "机制", "开放日", "案例", "参观"))


def is_dialogue_sentence(sentence: str) -> bool:
    """识别人际/现场模拟里更像真实沟通的话术。"""

    return any(marker in sentence for marker in ("爸", "妈", "您好", "你", "您", "担心", "理解", "放心", "支持", "沟通", "解释"))


def is_detail_heavy_sentence(sentence: str) -> bool:
    """识别组织策划题里细节密度过高的句子，低档样本尽量回避。"""

    heading_markers = (
        "活动时间",
        "活动地点",
        "参与对象",
        "人员筹备",
        "物资筹备",
        "场地筹备",
        "宣传筹备",
        "环节一",
        "环节二",
        "环节三",
        "活动主题",
        "活动目的",
        "活动收尾",
        "操作手册",
        "服务微信群",
        "智能手环",
        "定位手表",
        "宣传海报",
        "急救箱",
        "志愿者",
        "PPT",
        "样机",
        "后勤保障",
        "摄影宣传",
        "科普宣讲",
    )
    if any(marker in sentence for marker in heading_markers):
        return True
    if re.search(r"^[一二三四五六七八九十]+[、.]", sentence.strip()):
        return True
    if len(re.findall(r"\d", sentence)) >= 3:
        return True
    if sentence.count("、") >= 5 or sentence.count("：") >= 2:
        return True
    return False


def is_role_conclusion_sentence(sentence: str) -> bool:
    """识别结尾里容易把分数抬高的岗位化/表态化收束句。"""

    stripped = sentence.strip()
    direct_markers = (
        "作为未来的",
        "作为一名",
        "作为报考",
        "在今后的工作中",
        "在后续工作中",
        "未来工作中",
        "我将",
        "我会",
        "我一定",
        "我相信",
        "履职尽责",
        "贡献力量",
        "添砖加瓦",
        "真正落实",
    )
    if any(marker in stripped for marker in direct_markers):
        return True
    return stripped.startswith("总之") and any(
        marker in stripped for marker in ("岗位", "履职", "公职人员", "人民警察", "工作中")
    )


def dilute_confident_phrases(text: str, mode: str) -> str:
    """把高分话术压平，降低 LLM 对文采和定性力度的额外加分。"""

    replacements = {
        "意义重大": "值得重视",
        "立意深远": "有一定意义",
        "精准对接": "需要对接",
        "重大责任": "一定责任",
        "凝聚了干事的强大合力": "有助于形成合力",
        "筑牢了发展的相关内容": "有助于统一认识",
        "精准高效": "更贴近实际",
        "核心地位": "重要位置",
        "责任担当": "工作责任",
        "率先发展、作出示范": "先行探索",
        "贡献力量": "做好本职工作",
        "立足本职、履职尽责": "结合岗位实际",
        "推动": "促进",
        "开花结果": "真正落地",
        "光荣": "值得选择",
        "保驾护航": "提供支持",
    }
    if mode == "low":
        replacements.update(
            {
                "深刻认识": "认识到",
                "必须": "还是要",
                "应当": "可以",
                "切实": "尽量",
                "坚决": "注意",
                "有力": "尽量",
                "关键": "比较重要",
                "辩证统一": "并不完全冲突",
                "看似矛盾，实则": "表面上有差异，但还是要分情况看，",
                "核心是": "主要还是",
                "有以下看法": "有几点想法",
                "切实可行": "相对可行",
                "赋能剂": "帮助",
                "试金石": "一个参考",
                "我设计的两个切实可行的活动方案分别是": "我觉得可以从两个活动来考虑",
            }
        )

    diluted = text
    for source, target in replacements.items():
        diluted = diluted.replace(source, target)
    return diluted


def strip_role_conclusion(text: str, mode: str) -> str:
    """去掉结尾里最像高分模板的总结句。"""

    sentences = split_answer_sentences(text)
    if not sentences:
        return text

    trailing_window = 2 if mode == "low" else 1
    trailing_start = max(0, len(sentences) - trailing_window)
    filtered: list[str] = []
    for index, sentence in enumerate(sentences):
        if index >= trailing_start and is_role_conclusion_sentence(sentence):
            continue
        filtered.append(sentence)
    if len(filtered) < max(2, len(sentences) // 3):
        return text
    return clean_generated_sample_text(" ".join(filtered)) if filtered else text


def build_low_generic_opener(question_data: dict[str, Any]) -> str:
    """给低档样本换一个更像真实临场表达的开头。"""

    family = detect_template_family(question_data)
    question_text = question_data.get("question", "")
    topic = infer_topic_phrase(question_data, generic=False)
    target_group = infer_target_group(question_data, generic=False)
    role_focus = infer_role_focus(question_data)
    if family == "scene" and is_word_expression_scene(question_data):
        terms = extract_word_expression_terms(question_data)
        keyword_text = "、".join(terms[:3]) or "、".join(ordered_keywords(question_data, generic=False)[:2]) or topic
        return f"我会先把{keyword_text}这几个词串成一句完整的话，再往{role_focus}里的基本做法上带。"
    if family == "scene" and is_speech_scene(question_data):
        return f"各位考官，我想围绕{topic}这个主题简单谈几句。"
    if family == "organization" and is_slogan_organization_question(question_data):
        return f"我会先给一句围绕{topic}的宣传口径，再简单补一句为什么这么说。"
    if family == "organization":
        return f"我觉得这项工作可以先围着{target_group}和{topic}把基本安排理顺，再看怎么往后推进。"
    if family == "analysis":
        return f"我觉得{topic}这个事不能只看表面，还是要回到{role_focus}怎么落地来看。"
    if any(marker in question_text for marker in ("活动", "方案", "组织", "社区")):
        return "我觉得这个活动可以先从需求摸排、现场教学和后续答疑几个方面简单考虑。"
    if any(marker in question_text for marker in ("看法", "理解", "怎么看", "谈谈")):
        return "我觉得这个问题不能只看一面，还是要结合实际分开来看。"
    return "我觉得方向还是要结合实际来看，重点是把主要问题和基本做法说清楚。"


def rewrite_low_opening(text: str, question_data: dict[str, Any]) -> str:
    """把低档样本开头里的高分总论句压平。"""

    sentences = split_answer_sentences(text)
    if not sentences:
        return text

    first_sentence = sentences[0].strip()
    markers = ("看似", "实则", "核心是", "有以下看法", "我设计的", "下面我就", "立足", "作为")
    if len(first_sentence) >= 50 or any(marker in first_sentence for marker in markers):
        sentences[0] = build_low_generic_opener(question_data)
    return clean_generated_sample_text(" ".join(sentences))


def desired_length_bounds(reference_length: int, mode: str) -> tuple[int, int]:
    """给中低档样本设置更贴近真实作答的长度目标。"""

    if mode == "mid":
        lower = min(max(520, int(reference_length * 0.42)), 1100)
        target = min(max(720, int(reference_length * 0.58)), 1300)
    else:
        lower = min(max(320, int(reference_length * 0.24)), 700)
        target = min(max(460, int(reference_length * 0.36)), 900)
    return lower, target


def sentence_count_candidates(total_sentences: int, mode: str) -> list[int]:
    """根据答案长度生成候选抽句数量。"""

    if total_sentences <= 1:
        return [1]

    ratios = (
        (0.32, 0.4, 0.5, 0.6)
        if mode == "low"
        else (0.52, 0.62, 0.72, 0.82, 0.92)
    )
    base_counts = [3, 4, 5, 6, 7] if mode == "low" else [6, 7, 8, 9, 10]

    counts = set(base_counts)
    for ratio in ratios:
        counts.add(max(1, round(total_sentences * ratio)))

    return sorted(
        count
        for count in counts
        if 1 <= count < total_sentences
    )


def select_sentence_indices(sentences: list[str], strategy: str, count: int) -> list[int]:
    """按不同策略选取句子索引。"""

    total = len(sentences)
    count = max(1, min(count, total))

    if strategy == "leading":
        return list(range(count))

    if strategy == "front_half":
        upper_bound = max(count, min(total, round(total * 0.7)))
        return list(range(min(count, upper_bound)))

    if strategy == "spread":
        return sorted(
            {
                min(total - 1, round((total - 1) * index / max(count - 1, 1)))
                for index in range(count)
            }
        )

    if strategy == "markers":
        marker_indices = [
            index
            for index, sentence in enumerate(sentences)
            if re.search(r"^(首先|其次|再次|最后|一是|二是|三是|四是|五是|六是|另外|同时)", sentence)
        ]
        indices = {0, total - 1}
        for index in marker_indices:
            indices.add(index)
            if len(indices) >= count:
                break
        if len(indices) < count:
            for index in range(total):
                indices.add(index)
                if len(indices) >= count:
                    break
        return sorted(indices)

    if strategy == "analysis_focus":
        preferred = [
            index
            for index, sentence in enumerate(sentences)
            if not is_measure_sentence(sentence) and not is_innovation_sentence(sentence)
        ]
        preferred = [index for index in preferred if index < max(1, round(total * 0.85))]
        indices = [0]
        for index in preferred:
            if index not in indices:
                indices.append(index)
            if len(indices) >= count:
                break
        if total - 1 not in indices:
            indices.append(total - 1)
        if len(indices) < count:
            for index in range(total):
                if index not in indices:
                    indices.append(index)
                if len(indices) >= count:
                    break
        return sorted(indices[:count])

    if strategy == "dialogue_focus":
        preferred = [
            index
            for index, sentence in enumerate(sentences)
            if is_dialogue_sentence(sentence) or not is_measure_sentence(sentence)
        ]
        indices = [0]
        for index in preferred:
            if index not in indices:
                indices.append(index)
            if len(indices) >= count - 1:
                break
        if total - 1 not in indices:
            indices.append(total - 1)
        if len(indices) < count:
            for index in range(total):
                if index not in indices:
                    indices.append(index)
                if len(indices) >= count:
                    break
        return sorted(indices[:count])

    # hybrid：保留首尾，再穿插几个中间节点，兼顾场景题和综合分析题。
    anchors = {
        0,
        total - 1,
        max(0, total // 4),
        max(0, total // 2),
        max(0, (total * 3) // 4),
    }
    indices = sorted(anchors)
    if len(indices) < count:
        for index in range(total):
            if index not in anchors:
                indices.append(index)
            if len(indices) >= count:
                break
    return sorted(indices[:count])


def is_slogan_organization_question(question_data: dict[str, Any]) -> bool:
    """Whether the organization question is really asking for a slogan or theme line."""

    haystack = build_question_haystack(question_data)
    return any(marker in haystack for marker in ("宣传语", "标语", "口号", "主题句"))


def is_word_expression_scene(question_data: dict[str, Any]) -> bool:
    """Whether the scene question is actually a word-expression / 串词表达 prompt."""

    haystack = build_question_haystack(question_data)
    return any(marker in haystack for marker in ("串词表达", "串词", "词语"))


def is_speech_scene(question_data: dict[str, Any]) -> bool:
    """Whether the scene question is actually a short speech / 演讲表达 prompt."""

    question_text = question_data.get("question", "")
    question_type = question_data.get("type", "")
    return "演讲" in question_type or ("演讲" in question_text and "发表" in question_text)


def generic_bridge_sentences(question_data: dict[str, Any], mode: str) -> list[str]:
    """长度不足时补几句低信息密度的桥接语，但按题型家族区分。"""

    family = detect_template_family(question_data)
    province = question_data.get("province", "当地") or "当地"
    topic = infer_topic_phrase(question_data, generic=False)
    use_generic_target = mode == "low" and family not in {"organization", "interpersonal", "scene"}
    target_group = infer_target_group(question_data, generic=use_generic_target)
    role_focus = infer_role_focus(question_data)
    if family == "organization":
        bridges = [
            f"后面真正落地时，还是要围着{target_group}的接受度来调节节奏，不能只把流程写满。",
            "前期准备、现场推进和后续反馈最好能连成一条线，这样活动才不容易前紧后松。",
            "如果对象感不强、通知发动不到位，现场环节再完整，最后效果也会打折。",
        ]
    elif family == "scene":
        if is_word_expression_scene(question_data):
            terms = extract_word_expression_terms(question_data)
            term_text = "、".join(terms[:2]) if terms else "这些词语"
            bridges = [
                f"这类表达题关键还是要让{term_text}都围着同一个主题转，别变成单纯堆词。",
                f"最后最好再回到{role_focus}怎么做，这样整段话才不至于只停在表态层面。",
                "只要主题顺、表达自然、落点明确，整体效果就会比机械拼接好很多。",
            ]
        elif is_speech_scene(question_data):
            bridges = [
                f"演讲里还是要把{topic}和{province}实际变化连起来，不然容易只剩口号。",
                "哪怕只举一个乡风变化、群众感受或者基层新气象，整段话都会更有画面。",
                f"最后再把态度和{role_focus}里的基本责任收一下，表达会更完整。",
            ]
        else:
            bridges = [
                f"现场沟通时还是要先回应{target_group}最现实的顾虑，再谈怎么配合，不然容易越说越空。",
                "能当场说明白的先说明白，暂时解决不了的也要把后续联系和跟进方式交代出来。",
                "只要对象听得懂、愿意继续配合，这段表达就算真正落到了沟通目的上。",
            ]
    elif family == "interpersonal":
        bridges = [
            "这类沟通不能一上来就压要求，先把关系稳住、把情绪接住更重要。",
            "把对方最关心的点解释清楚以后，再谈后续怎么处理，沟通才有继续推进的空间。",
            "哪怕当场不能完全解决，也要留下持续跟进的口子，别让谈话停在情绪上。",
        ]
    else:
        if mode == "mid":
            bridges = [
                f"整体看，这项工作方向是对的，但真正落地还要结合{province}实际和{role_focus}场景，不能只停留在表态层面。",
                "如果只讲原则、不讲重点，或者只看局部、不看整体，后续执行效果就容易打折扣。",
                "所以作答时既要看到积极意义，也要把问题和短板说透，再把岗位上的落点交代清楚。",
            ]
        else:
            bridges = [
                f"总体看，{topic if topic != '这项工作' else '这件事'}不能只看表态，还是得放到{province}实际里去考虑。",
                f"我觉得方向可以先把握住，但最后还是要回到{role_focus}怎么落地这个问题上。",
                "哪怕答得简单一点，也最好先讲个基本判断，再点一两个问题和基本做法。",
            ]
    return [clean_generated_sample_text(sentence) for sentence in bridges]


def extend_variant_length(text: str, question_data: dict[str, Any], mode: str, minimum_length: int) -> str:
    """如果候选文本过短，就补几句低信息密度的桥接语。"""

    extended = text
    family = detect_template_family(question_data)
    bridges = generic_bridge_sentences(question_data, mode)
    if not bridges:
        return extended

    if family == "scene" and is_word_expression_scene(question_data) and mode == "low":
        max_rounds = 1
    else:
        max_rounds = 2 if mode == "low" else 1
    used_sentences = {
        clean_generated_sample_text(sentence)
        for sentence in split_answer_sentences(extended)
    }
    for index in range(len(bridges) * max_rounds):
        if effective_length(extended) >= minimum_length:
            break
        bridge_sentence = bridges[index % len(bridges)]
        if bridge_sentence in used_sentences:
            continue
        extended = clean_generated_sample_text(f"{extended} {bridge_sentence}")
        used_sentences.add(bridge_sentence)
    return extended


def count_repeated_sentences(text: str) -> int:
    """统计样本中重复句子的数量，避免桥接句循环拼接。"""

    sentences = [clean_generated_sample_text(sentence) for sentence in split_answer_sentences(text)]
    counts = Counter(sentences)
    return sum(count - 1 for count in counts.values() if count > 1)


def count_bridge_sentence_hits(text: str, question_data: dict[str, Any], mode: str) -> int:
    """统计样本里命中的通用桥接句数量。"""

    bridge_set = {
        clean_generated_sample_text(sentence)
        for sentence in generic_bridge_sentences(question_data, mode)
    }
    sentences = {
        clean_generated_sample_text(sentence)
        for sentence in split_answer_sentences(text)
    }
    return sum(1 for sentence in sentences if sentence in bridge_set)


def sample_focus_hits(text: str, question_data: dict[str, Any]) -> int:
    """粗略统计样本是否保留了题目自身的主题、对象或岗位语境。"""

    markers = [
        infer_topic_phrase(question_data, generic=False),
        infer_target_group(question_data, generic=False),
        infer_role_focus(question_data),
    ] + ordered_keywords(question_data, generic=False)[:2]
    hits = 0
    seen = set()
    for marker in markers:
        if not marker or marker in seen or marker in {"这项工作", "参与对象", "具体工作落实"}:
            continue
        seen.add(marker)
        if marker in text:
            hits += 1
    return hits


def placeholder_content_penalty(text: str) -> int:
    """识别“相关内容”“演讲完毕”这类占位式空话。"""

    penalty = max(0, text.count("相关内容") - 1) * 2
    if "演讲的题目是《相关内容" in text:
        penalty += 6
    if "我的演讲完毕，谢谢大家" in text and text.count("相关内容") >= 2:
        penalty += 4
    if "各位考官" in text and "大家好" in text and text.count("相关内容") >= 2:
        penalty += 3
    return penalty


def sample_quality_penalty(text: str, question_data: dict[str, Any], mode: str) -> int:
    """给桥接过重、主题过空的候选样本打惩罚分。"""

    repeated = count_repeated_sentences(text)
    bridge_hits = count_bridge_sentence_hits(text, question_data, mode)
    focus_hits = sample_focus_hits(text, question_data)
    penalty = repeated * 8 + placeholder_content_penalty(text) + bridge_hits * 2
    if bridge_hits >= 2 and focus_hits <= 1:
        penalty += 4
    if mode == "mid" and bridge_hits >= 2:
        penalty += 2
    return penalty


def sample_strategy_penalty(strategy: str, mode: str) -> int:
    """对容易生成空泛样本的策略适度降权。"""

    if strategy.startswith("template_"):
        return 0
    normalized = strategy.removeprefix("fallback_")
    if mode == "low" and normalized in {"leading", "dialogue_focus"}:
        return 3
    if mode == "mid" and normalized == "leading":
        return 2
    return 1


def should_skip_candidate(text: str, question_data: dict[str, Any], mode: str) -> bool:
    """直接拦掉明显坏掉的占位样本或桥接循环样本。"""

    if count_repeated_sentences(text) > 0:
        return True
    if placeholder_content_penalty(text) >= 6:
        return True
    return False


def sample_detail_score(text: str) -> float:
    """粗略估计样本里“具体细节堆砌”的密度。"""

    digit_count = len(re.findall(r"\d", text))
    ordered_marker_count = len(re.findall(r"[一二三四五六七八九十][、是]|首先|其次|再次|最后", text))
    list_marker_count = text.count("、") + text.count("；")
    punctuation_detail = text.count("（") * 2 + text.count("：") + text.count('"')
    example_count = text.count("如") + text.count("例如") * 2 + text.count("比如") * 2
    schedule_count = len(re.findall(r"活动时间|活动地点|人员筹备|物资筹备|场地筹备|宣传筹备|参与对象", text))
    return (
        digit_count * 1.2
        + ordered_marker_count * 1.6
        + list_marker_count * 0.5
        + punctuation_detail
        + example_count * 1.3
        + schedule_count * 2.5
    )


def build_question_haystack(question_data: dict[str, Any]) -> str:
    """把题型识别所需信息拼成统一文本。"""

    return " ".join(
        [
            question_data.get("type", ""),
            question_data.get("question", ""),
            " ".join(question_data.get("tags", [])),
            " ".join(question_data.get("coreKeywords", [])),
            " ".join(question_data.get("strongKeywords", [])),
        ]
    )


def detect_template_family(question_data: dict[str, Any]) -> str | None:
    """识别适合走独立模板生成的题型。"""

    haystack = build_question_haystack(question_data)
    question_text = question_data.get("question", "")
    question_type = question_data.get("type", "")
    primary_type = re.split(r"[·（(]", question_type, maxsplit=1)[0]
    explicit_scene_markers = ("请现场模拟", "请你现场模拟", "请现场处置", "模拟宣讲", "现场宣讲", "发表一段演讲")

    if any(marker in question_text for marker in explicit_scene_markers):
        return "scene"
    if "现场模拟" in question_type and any(
        marker in question_text for marker in ("宣讲", "发言", "怎么说", "如何说", "串成一段话")
    ):
        return "scene"
    if "演讲" in primary_type or ("演讲" in question_text and "发表" in question_text):
        return "scene"

    if (
        "综合分析" in primary_type
        or "价值判断" in primary_type
        or "政策理解" in primary_type
        or "漫画联想" in primary_type
        or "漫画题" in primary_type
    ):
        return "analysis"
    if "计划组织" in primary_type:
        return "organization"
    if "工作落实" in primary_type:
        return "organization"
    if "人际沟通" in primary_type:
        return "interpersonal"
    if "现场模拟" in primary_type or "串词表达" in primary_type:
        return "scene"

    # 先抓“明确要求现场表达”的题，避免和普通沟通/劝说题混淆。
    if any(
        marker in haystack
        for marker in ("现场模拟", "现场处置", "模拟沟通", "宣讲", "串词表达")
    ):
        return "scene"
    if any(
        marker in haystack
        for marker in ("人际沟通", "同事关系", "群众矛盾", "心理疏导", "亲情沟通", "矛盾化解", "沟通劝说")
    ):
        return "interpersonal"
    if any(
        marker in question_text
        for marker in ("怎么劝说", "如何劝说", "怎么劝导", "如何劝导", "怎么沟通", "如何沟通", "怎么说服", "如何说服", "怎么安抚", "如何安抚")
    ):
        return "interpersonal"
    if any(marker in haystack for marker in ("计划组织", "活动设计", "活动方案", "宣传活动", "组织开展", "工作落实", "制度整改", "流程优化", "整改任务")):
        return "organization"
    if any(marker in haystack for marker in ("综合分析", "价值判断", "政策理解", "社会现象", "漫画解读", "漫画联想", "漫画题")):
        return "analysis"
    return None


def ordered_keywords(question_data: dict[str, Any], *, generic: bool = False) -> list[str]:
    """取一组去重后的关键词，供模板拼句使用。"""

    values: list[str] = []
    seen = set()
    for keyword in (
        question_data.get("coreKeywords", [])
        + question_data.get("strongKeywords", [])
        + question_data.get("weakKeywords", [])
    ):
        value = genericize_keyword(keyword) if generic else keyword
        value = value.strip()
        if not value or value in seen:
            continue
        values.append(value)
        seen.add(value)
    return values


def extract_word_expression_terms(question_data: dict[str, Any]) -> list[str]:
    """尽量从串词题题干里提取可直接落笔的原始词语。"""

    question_text = question_data.get("question", "")
    candidates = re.findall(r"[“\"]([^”\"]{2,120})[”\"]", question_text)
    split_pattern = re.compile(r"[、，,；;\s]+")
    noise_markers = ("任意选择", "串成一段话", "下列", "七组词语", "词语")
    for candidate in sorted(candidates, key=len, reverse=True):
        text = re.sub(r"^.*?[：:]", "", candidate).strip()
        pieces: list[str] = []
        seen = set()
        for piece in split_pattern.split(text):
            value = piece.strip("“”\"'()（）[]【】 ")
            if (
                not value
                or value in seen
                or any(marker in value for marker in noise_markers)
                or len(value) > 8
            ):
                continue
            pieces.append(value)
            seen.add(value)
        if len(pieces) >= 3:
            return pieces

    fallback = [
        keyword
        for keyword in ordered_keywords(question_data, generic=False)
        if keyword and keyword != "所选词语" and len(keyword) <= 8
    ]
    return fallback[:3]


def infer_role_focus(question_data: dict[str, Any]) -> str:
    """粗略提炼题目对应的岗位/工作语境。"""

    haystack = build_question_haystack(question_data)
    mappings = (
        ("国家公务员", "公职岗位履职"),
        ("公务员", "公职岗位履职"),
        ("公职", "公职岗位履职"),
        ("税务", "税务工作"),
        ("特警", "特警岗位履职"),
        ("公安", "执法岗位履职"),
        ("监狱", "监狱岗位履职"),
        ("乡镇", "基层工作"),
        ("社区", "基层服务"),
        ("遴选", "机关履职"),
    )
    for marker, label in mappings:
        if marker in haystack:
            return label
    return "具体工作落实"


def infer_target_group(question_data: dict[str, Any], *, generic: bool = False) -> str:
    """提炼组织策划题的服务对象。"""

    question_first_haystack = " ".join(
        [
            question_data.get("question", ""),
            " ".join(question_data.get("coreKeywords", [])),
            " ".join(question_data.get("strongKeywords", [])),
        ]
    )
    haystack = build_question_haystack(question_data)
    mappings = (
        ("餐饮经营者", "餐饮经营者"),
        ("经营者", "经营者"),
        ("老板", "商户和老板"),
        ("同事", "同事"),
        ("同仁", "同事"),
        ("小李", "小李"),
        ("领导", "领导"),
        ("下属", "下属"),
        ("家属", "家属"),
        ("社区", "社区居民"),
        ("服刑人员", "服刑人员"),
        ("罪犯", "服刑人员"),
        ("犯人", "服刑人员"),
        ("老年", "老年人"),
        ("老人", "老年人"),
        ("群众", "群众"),
        ("村民", "村民"),
        ("来访群众", "来访群众"),
        ("信访人", "来访群众"),
        ("居民", "居民"),
        ("学生", "学生"),
        ("游客", "游客"),
        ("企业", "企业和商户"),
        ("商户", "企业和商户"),
        ("干部", "基层干部"),
    )
    for text in (question_first_haystack, haystack):
        for marker, label in mappings:
            if marker in text:
                return genericize_keyword(label) if generic else label
    return "参与对象" if not generic else "相关群体"


def infer_topic_phrase(question_data: dict[str, Any], *, generic: bool = False) -> str:
    """提炼题目的主题词。"""

    noise = {"相关群体", "有关部门", "有关要求", "相关机制", "相关工作", "相关内容"}
    skip_markers = (
        "岗位",
        "履职",
        "适配",
        "组织",
        "工作人员",
        "机关",
        "相关群体",
        "老年",
        "老人",
        "群众",
        "居民",
        "学生",
        "企业",
        "商户",
        "游客",
        "对象",
    )
    question_text = question_data.get("question", "")
    raw_keywords = (
        question_data.get("coreKeywords", [])
        + question_data.get("strongKeywords", [])
        + question_data.get("weakKeywords", [])
    )
    for keyword in raw_keywords:
        if not keyword or keyword not in question_text:
            continue
        if not generic and any(marker in keyword for marker in skip_markers):
            continue
        value = genericize_keyword(keyword) if generic else keyword
        if generic or value not in noise:
            return value
    for keyword in ordered_keywords(question_data, generic=generic):
        if not generic and any(marker in keyword for marker in skip_markers):
            continue
        if generic or keyword not in noise:
            return keyword
    return "相关内容" if generic else "这项工作"


def _extract_dimension_names(question_data: dict[str, Any]) -> list[str]:
    """提取题目维度名，供模板补足场景动作时使用。"""

    dimension_names: list[str] = []
    for item in question_data.get("dimensions", []):
        if isinstance(item, dict):
            name = str(item.get("name", "")).strip()
        else:
            name = str(getattr(item, "name", "")).strip()
        if name:
            dimension_names.append(name)
    return dimension_names


def _build_interpersonal_focus_clauses(question_data: dict[str, Any]) -> list[str]:
    """为人际题补一组更贴场景的中档动作句。"""

    target_group = infer_target_group(question_data, generic=False)
    topic = infer_topic_phrase(question_data, generic=False)
    role_focus = infer_role_focus(question_data)
    haystack = " ".join(
        [
            build_question_haystack(question_data),
            " ".join(_extract_dimension_names(question_data)),
            " ".join(question_data.get("scoringCriteria", [])),
            " ".join(question_data.get("deductionRules", [])),
        ]
    )
    clauses: list[str] = []

    def add_clause(text: str) -> None:
        if text and text not in clauses:
            clauses.append(text)

    if any(marker in haystack for marker in ("失误", "担责", "责任", "认错", "补救", "整改")):
        add_clause("这类情况不能只停在安抚上，该认的责任要认清楚，该澄清的事实也要当面说透。")
        add_clause(
            f"如果问题和{topic}有关，我会把来龙去脉讲明白，再把能马上补上的环节尽快补上，别让{target_group}继续替别人扛着。"
        )

    if any(marker in haystack for marker in ("偏见", "误解", "误会", "信任", "建议", "未采纳", "成长", "培养", "平台")):
        add_clause(
            f"如果对方心里已经有了偏见或误会，我会重点把工作判断、现实条件和为什么暂时没采纳讲清楚，不让{target_group}把事情理解成针对个人。"
        )
        add_clause(
            f"说完原因还不够，我会再给一个后续帮带或跟进安排，让{target_group}看到在{role_focus}里还有成长空间，不是谈完就算。"
        )

    if any(marker in haystack for marker in ("群众", "居民", "村民", "矛盾", "情绪", "安抚", "来访", "信访")):
        add_clause("碰到情绪和矛盾比较重的情况，我会先把情绪接住，再把政策边界、能处理到哪一步和后续推进方式说清楚。")
        add_clause(
            f"能当场协调的就尽量当场推动，暂时解决不了的也会给出跟进节点，避免{target_group}只听到态度、看不到动作。"
        )

    if any(marker in haystack for marker in ("朋友圈", "微信群", "线上", "云调研", "基层", "入户", "一线", "地头", "实地")):
        add_clause(
            f"这道题更关键的是把线上了解和真正下到一线的差别讲透，让{target_group}明白{role_focus}不能只停在表面信息上。"
        )
        add_clause("后面我会把改法说得务实一点，比如跟着一起下去走一走、看一看、听一听，把作风和方法慢慢扭回来。")

    if any(marker in haystack for marker in ("领导", "机关", "同事", "团队", "协作")):
        add_clause(f"沟通里既要顾及关系，也要把组织要求和工作标准摆出来，不能只顾把话说软、不顾{role_focus}真正要落的要求。")

    if not clauses:
        add_clause(
            f"这类题不能只做情绪安抚，我会把{target_group}最在意的问题、{topic}背后的实际情况和后续怎么跟进三件事连起来说。"
        )
        add_clause(f"既把话说软一点，也把{role_focus}里该有的标准讲清楚，这样沟通才不容易发空。")

    return clauses[:5]


def _build_interpersonal_mid_openings(question_data: dict[str, Any]) -> list[str]:
    """给人际题中档样本准备几句不完全同质化的开场。"""

    target_group = infer_target_group(question_data, generic=False)
    haystack = build_question_haystack(question_data)
    if any(marker in haystack for marker in ("失误", "担责", "责任", "认错")):
        return [
            f"如果是我来和{target_group}沟通，我不会先急着替自己找理由，而是先把态度摆正，把事实捋清楚。",
            f"这类题我会先正面回应问题本身，尤其是和{target_group}之间的责任边界，不能让误会一直悬着。",
            f"我会先把话说坦诚一点，让{target_group}感受到我是来解决问题的，不是来把事情糊过去的。",
        ]
    if any(marker in haystack for marker in ("偏见", "误解", "误会", "建议", "成长", "培养")):
        return [
            f"面对{target_group}已经有情绪和心结的情况，我会先把关系稳住，再谈事情本身。",
            f"如果是我来谈，我会先认可{target_group}身上的积极面，避免一开口就把话谈僵。",
            f"这类题我会先让{target_group}把心里的顾虑说出来，再回到工作判断和后续带人的节奏上。",
        ]
    if any(marker in haystack for marker in ("朋友圈", "微信群", "线上", "基层", "入户", "一线")):
        return [
            f"如果是我来和{target_group}聊这件事，我会先肯定积极性，再把问题真正卡在哪里点出来。",
            f"这类题我不会一上来就否定{target_group}，而是先说明为什么这种做法看着忙、实际还不够到位。",
            f"我会先把气氛放缓一点，让{target_group}愿意继续听，再顺着作风和方法把话谈实。",
        ]
    return [
        f"如果是我来和{target_group}沟通，我会先把态度放稳一点，先听清楚对方现在最在意的点。",
        f"我会先把关系稳住，再把事情的来龙去脉和当前卡点讲清楚，避免一开始就只剩下情绪对冲。",
        f"这类题我会先把人稳住、把事讲清，再把后续怎么跟进交代出来。",
    ]


def _build_interpersonal_mid_closing(question_data: dict[str, Any]) -> str:
    """给人际题中档样本补一个更像作答收束的结尾。"""

    haystack = build_question_haystack(question_data)
    role_focus = infer_role_focus(question_data)
    if any(marker in haystack for marker in ("失误", "担责", "责任", "补救")):
        return f"总的来说，既要把话谈开，也要把事情补回来，这样才算把{role_focus}里该有的担当落到位。"
    if any(marker in haystack for marker in ("偏见", "误解", "成长", "培养", "平台")):
        return f"这样既能把心结解开，也能把后面的培养和跟进接上，更符合{role_focus}里带人做事的节奏。"
    if any(marker in haystack for marker in ("朋友圈", "微信群", "线上", "基层", "入户", "一线")):
        return f"这样既不是简单批评，也能把作风和方法慢慢扭到{role_focus}真正需要的方向上。"
    return f"这样既顾到了对方感受，也把{role_focus}里该回应的问题和后续动作交代清楚了。"


def clean_question_type(raw_type: str, header_description: str) -> str:
    """Sanitize polluted type text and fall back to header description when needed."""

    for candidate in (raw_type or "", header_description or ""):
        text = candidate.splitlines()[0].strip()
        text = TYPE_PREFIX_PATTERN.sub("", text)
        text = TYPE_SCORE_PATTERN.sub("", text)
        text = cut_text_before_markers(text, TYPE_NOISE_MARKERS)
        text = TYPE_METADATA_PATTERN.sub("", text)
        text = " ".join(text.split()).strip("；;，,。 ")
        if text and not any(marker in text for marker in TYPE_NOISE_MARKERS):
            return text
    fallback = " ".join((header_description or raw_type or "").split())
    fallback = TYPE_PREFIX_PATTERN.sub("", fallback)
    fallback = TYPE_METADATA_PATTERN.sub("", fallback)
    return fallback.strip("；;，,。 ")


def build_analysis_template_texts(question_data: dict[str, Any], mode: str) -> list[tuple[str, str, bool]]:
    """为综合分析/价值判断题生成中低档模板文本。"""

    topic = infer_topic_phrase(question_data, generic=False)
    topic2 = ordered_keywords(question_data, generic=False)[1:2]
    topic2_text = topic2[0] if topic2 else "现实需求"
    aux_topic = infer_topic_phrase(question_data, generic=False)
    province = question_data.get("province", "当地") or "当地"
    role_focus = infer_role_focus(question_data)
    if mode == "mid":
        return [
            (
                (
                    f"我觉得{topic}这个问题方向上是成立的，它背后既有现实需要，也和{province}当前工作要求有关。 "
                    f"但如果只看到表面的积极意义，忽视{topic2_text}、基层承接能力和执行节奏，后面就容易出现推进变形、群众感受不强的问题。 "
                    f"站在{role_focus}角度，回答时既要把基本判断讲清，也要把风险和短板点出来，最后落到摸清情况、结合岗位推进落实上。"
                ),
                "medium",
                False,
            ),
            (
                (
                    f"这类题我一般会先作一个基本判断，就是{topic}不能简单否定，但也不能只停留在肯定层面。 "
                    f"如果后续落实时对{aux_topic}考虑不够细，对象差异、现实约束和执行重点没有分开讲，工作就容易看着热闹、实际一般。 "
                    f"所以更稳妥的答法，是先亮明态度，再指出问题风险，最后补上{role_focus}中怎么分层推进、怎么把措施落到位。"
                ),
                "medium",
                False,
            ),
            (
                (
                    f"在我看，{topic}不是一句口号题，关键在于既要看到它为什么要做，也要看到做偏了会带来什么问题。 "
                    f"如果只讲意义，不讲{topic2_text}和现实风险，答案会发空；如果只挑毛病，不讲基本方向，也容易失衡。 "
                    f"所以比较合适的结构，就是先作判断，再讲风险，最后回到{role_focus}需要抓住哪些措施落点。"
                ),
                "heavy",
                False,
            ),
        ]

    return [
        (
            (
                f"我觉得{topic}这个事不能只喊口号，关键还是看后面能不能落到{role_focus}里。 "
                f"方向上可以认同，但如果{aux_topic}考虑不细，执行中还是容易出偏差。 "
                "所以我会先把基本判断说出来，再补一句风险，最后简单说说怎么推进。"
            ),
            "medium",
            True,
        ),
        (
            (
                f"我觉得这类题还是要看实际效果，不能只看出发点。 "
                f"有些工作本意是好的，但如果推进太快，{aux_topic}就容易变成表面动作。 "
                f"后面还是要结合{province}实际，把问题和{role_focus}里的基本做法交代清楚。"
            ),
            "medium",
            True,
        ),
        (
            (
                f"在我看，这类题最怕的不是没有态度，而是只讲态度、不讲{role_focus}怎么落。 "
                f"如果前面把{topic}说得很满，后面又不交代风险和措施，答案就会比较空。 "
                "所以还是先讲判断，再讲问题，最后补一个岗位落点会更稳。"
            ),
            "medium",
            True,
        ),
    ]


def build_organization_template_texts(question_data: dict[str, Any], mode: str) -> list[tuple[str, str, bool]]:
    """为计划组织题生成中低档模板文本。"""

    slogan_question = is_slogan_organization_question(question_data)
    target_group = infer_target_group(question_data, generic=False)
    topic = infer_topic_phrase(question_data, generic=False)
    slogan_line = f"比如可以概括成“围绕{topic}，把实事办细、把服务做实”。"
    if slogan_question:
        if mode == "mid":
            return [
                (
                    (
                        f"这类题我不会先铺活动流程，而是先把宣传口径立住。 {slogan_line} "
                        f"这句话至少要让{target_group}一听就知道主题是什么、导向是什么，不是为了凑词。 "
                        f"后面我再补一句它为什么围绕{topic}这样设计，以及这句口径准备服务什么工作场景。 "
                        "立意上再点到以学促干、凝聚团队和服务履职，宣传语才不只是好听。"
                    ),
                    "medium",
                    False,
                ),
                (
                    (
                        f"如果让我现场作答，我会先给一句主题鲜明、比较顺口的宣传语。 {slogan_line} "
                        f"然后简单解释这句话为什么贴着{topic}走、为什么能让{target_group}记得住。 "
                        "立意上我会把它落到以学促干、团队共进和岗位赋能上，出发点就是让读书分享会既有书香味，也能和单位实际工作接上。 "
                        "这样至少保留了主题句、对象感和基本立意，不会答成流程方案。"
                    ),
                    "medium",
                    False,
                ),
                (
                    (
                        f"宣传创意类题关键不是环节多，而是口径准、主题明。 {slogan_line} "
                        f"我会再补一句它对应的工作导向，让{target_group}知道这不是空喊，而是服务实际任务。 "
                        "再把出发点落到读书分享会为什么要为履职增能、为团队聚气上，这句宣传语就更站得住。"
                    ),
                    "heavy",
                    False,
                ),
            ]

        return [
            (
                (
                    f"这类题我会先给一句宣传口径。 {slogan_line} "
                    f"至少先把主题和{target_group}听感对上，再简单解释一句为什么这么说。"
                ),
                "medium",
                True,
            ),
            (
                (
                    f"我觉得宣传语题不用先讲流程，先把话说准更重要。 {slogan_line} "
                    f"后面再补一句它围绕{topic}、服务什么导向，就基本够用了。"
                ),
                "medium",
                True,
            ),
            (
                (
                    f"如果是宣传创意题，我会先亮一句主题句。 {slogan_line} "
                    "先让口径立住，再补一点立意说明。"
                ),
                "medium",
                True,
            ),
        ]

    if mode == "mid":
        return [
            (
                (
                    f"如果让我组织这项工作，我会先把对象、主题和基本时间场地定下来，再围绕{topic}把通知发动、现场推进和后续反馈串起来。 "
                    f"前期重点是摸清{target_group}最关心什么，把人员分工、物资准备和现场节奏先理顺。 "
                    f"中间把核心步骤说清楚，让{target_group}知道先做什么、怎么配合、遇到问题找谁。 "
                    "结束后再把反馈收回来，作为后续优化和跟进的依据。"
                ),
                "medium",
                False,
            ),
            (
                (
                    f"这类计划组织题我不会一上来把流程铺得很满，而是先抓住{target_group}、{topic}和关键步骤。 "
                    "前面做好通知和准备，现场把核心内容讲明白并留出基本互动，后面再接一个简短的跟进反馈。 "
                    f"这样既能保证{target_group}听得懂、跟得上，也不容易把答案答成空泛分析。"
                ),
                "medium",
                False,
            ),
            (
                (
                    f"我的思路会更务实一点，就是先准备、再实施、最后跟进。 "
                    f"准备阶段先把{target_group}的对象感和参与方式说明白，实施阶段围绕{topic}抓住两三个核心动作，最后补一个反馈收集和后续联系。 "
                    "这样方案虽然不算很细，但至少类型是对的、步骤也是顺的。"
                ),
                "heavy",
                False,
            ),
        ]

    return [
        (
                (
                    f"我觉得这项工作可以先按一个基础框架来做。 前面先把{target_group}和基本安排确定好，现场围绕{topic}把主要步骤走顺，结束后留一个反馈和继续联系的口子。 "
                    "先把对象、步骤和跟进交代清楚就可以。"
                ),
                "medium",
                True,
            ),
        (
            (
                f"我觉得这种组织题不用一开始就设计得特别复杂。 可以先做通知和简单准备，再围绕{topic}把核心环节走一遍，最后看看{target_group}还有什么反馈。 "
                "这样至少不是空讲想法，方案也有基本骨架。"
            ),
            "medium",
            True,
        ),
        (
            (
                f"我的想法是先把{target_group}、时间地点和基本分工理顺，再把{topic}相关内容说明白，最后做个简单跟进。 "
                "先把活动办稳、把对象照顾到，后面再慢慢细化。"
            ),
            "medium",
            True,
        ),
    ]


def build_interpersonal_template_texts(question_data: dict[str, Any], mode: str) -> list[tuple[str, str, bool]]:
    """为人际沟通题生成中低档模板文本。"""

    target_group = infer_target_group(question_data, generic=False)
    topic = infer_topic_phrase(question_data, generic=False)
    if mode == "mid":
        openings = _build_interpersonal_mid_openings(question_data)
        focus_clauses = _build_interpersonal_focus_clauses(question_data)
        closing = _build_interpersonal_mid_closing(question_data)

        def build_variant(opening_index: int, clause_indexes: tuple[int, ...]) -> str:
            selected = [
                focus_clauses[index]
                for index in clause_indexes
                if index < len(focus_clauses)
            ]
            if len(selected) < 2:
                selected = focus_clauses[:2]
            parts = [openings[min(opening_index, len(openings) - 1)], *selected, closing]
            return " ".join(part for part in parts if part)

        return [
            (
                build_variant(0, (0, 1)),
                "medium",
                False,
            ),
            (
                build_variant(1, (1, 2)),
                "medium",
                False,
            ),
            (
                build_variant(2, (0, 2)),
                "heavy",
                False,
            ),
        ]

    return [
        (
            (
                f"我觉得先和{target_group}单独谈一谈，把情绪缓一缓比较重要。 "
                f"先听听对方对{topic}最担心什么，再把事情不是一点转机都没有这个意思慢慢解释清楚。 "
                "只要先让对方愿意继续听、继续谈，后面就还有沟通空间。"
            ),
            "heavy",
            True,
        ),
        (
            (
                "这类情况我会先把态度放平，不急着反驳。 "
                "先表示理解，再把这件事能怎么改、后面还能争取什么简单解释一下。 "
                "如果对方还是不太接受，我会继续跟进，不让谈话停在情绪上。"
            ),
            "heavy",
            True,
        ),
        (
            (
                "在我看，人际沟通题先把关系稳住最重要。 "
                "先让对方愿意听，再围绕这件事做一点解释，也让他看到后面不是没人管。 "
                "能继续谈下去，事情就还有办法。"
            ),
            "heavy",
            True,
        ),
    ]


def build_scene_template_texts(question_data: dict[str, Any], mode: str) -> list[tuple[str, str, bool]]:
    """为现场模拟/宣讲表达类题生成中低档模板文本。"""

    target_group = infer_target_group(question_data, generic=False)
    topic = infer_topic_phrase(question_data, generic=False)
    role_focus = infer_role_focus(question_data)
    province = question_data.get("province", "当地") or "当地"
    if is_speech_scene(question_data):
        if mode == "mid":
            return [
                (
                    (
                        f"各位考官，今天我想围绕{topic}这个主题谈一点体会。 "
                        f"在{province}基层发展里，{topic}不是一句空口号，而是群众精神面貌和乡村变化一点点累出来的新气象。 "
                        "如果只把话说得很满，演讲会发空；但只要抓住一两个最直观的变化，比如风气更正、邻里更和、日子更有奔头，主题就能立住。 "
                        f"所以我会先把主题点明，再结合{province}实际说一两个变化，最后把态度和{role_focus}里的责任收住。"
                    ),
                    "medium",
                    False,
                ),
                (
                    (
                        f"各位考官，我理解这类演讲题关键还是把{topic}讲出画面感。 "
                        f"可以先说{province}乡村这些年最直观的变化，再把这种变化为什么值得珍惜、为什么需要继续培育讲清楚。 "
                        f"哪怕内容不铺得很满，只要主题稳、情感真，最后再回到{role_focus}该怎么做，整段演讲就能站住。"
                    ),
                    "medium",
                    False,
                ),
                (
                    (
                        f"如果让我现场演讲，我会先把{topic}这个主题亮出来。 "
                        f"然后围着{province}乡村这些年看得见的变化讲一两层意思，不空喊，也不堆太多例子。 "
                        f"最后再把态度收回到{role_focus}上，这样演讲会更完整一些。"
                    ),
                    "medium",
                    False,
                ),
            ]

        return [
            (
                (
                    f"各位考官，我想围绕{topic}这个主题简单谈几句。 "
                    f"这类演讲题不用一开始铺得太满，先把{province}乡村这些年最直观的变化讲出来就够了。 "
                    "比如风气更文明了、邻里更和气了、大家日子更有奔头了，这样会比空喊口号顺一些。 "
                    f"后面再把态度和{role_focus}里的基本责任收一下，整段话就不会散。"
                ),
                "medium",
                True,
            ),
            (
                (
                    f"各位考官，关于{topic}，我先谈一个总体感受。 "
                    f"就是{province}乡村现在不只是环境在变，人的精神面貌和做事风气也在慢慢变。 "
                    "哪怕只抓住一两个变化来说，再把自己想做的事简单收一下，演讲就比单纯表态更自然。"
                ),
                "medium",
                True,
            ),
            (
                (
                    f"各位考官，我觉得这类题可以先从{topic}带来的实际变化说起。 "
                    "先让听的人知道变化在哪、感受在哪，后面再补一句自己的理解和态度，整段表达就能基本立住。"
                ),
                "medium",
                True,
            ),
        ]
    if is_word_expression_scene(question_data):
        terms = extract_word_expression_terms(question_data)
        term_text = "、".join(terms[:3]) if terms else ""
        keyword_text = "、".join(ordered_keywords(question_data, generic=False)[:2]) or "岗位价值"
        if mode == "mid":
            return [
                (
                    (
                        f"这类串词表达题我不会把词语硬拼在一起，而是先围绕{topic}作一个基本判断。 "
                        f"后面再把{keyword_text}这些价值导向、岗位认识和{role_focus}里的具体行动连起来，让几个词自然落到一段完整表达里。 "
                        "这样至少能保证不是空喊口号，也不会只剩下词语堆砌。"
                    ),
                    "medium",
                    False,
                ),
                (
                    (
                        f"我会先把主题拎出来，再把几个词语往同一个方向上串。 "
                        f"先说清它为什么和{role_focus}有关，再补一句实际行动怎么落，这样整段话围着{topic}走，会更顺一些。"
                    ),
                    "medium",
                    False,
                ),
                (
                    (
                        f"在我看，串词题的关键不是把词都塞进去，而是让词语最后都服务同一个主题。 "
                        f"所以我会先点明{topic}的价值导向，再落到{role_focus}该怎么做，最后用自然一点的表达把整段收住。"
                    ),
                    "heavy",
                    False,
                ),
            ]

        return [
            (
                (
                    f"这类串词题我会先从{term_text or keyword_text}里挑几个能接上的词，把意思顺着连起来。 "
                    f"哪怕只是先把词和{province}发展、{role_focus}里的一个做法接上，也比单纯堆词强一点。"
                ),
                "medium",
                True,
            ),
            (
                (
                    f"我觉得串词表达不用一上来就讲很大，先把{term_text or keyword_text}放到一条线上更重要。 "
                    f"先说清这几个词为什么能放在一起，再顺手带到{role_focus}里的基本做法，整段话就会顺一点。"
                ),
                "medium",
                True,
            ),
            (
                (
                    f"我的想法是先从{term_text or keyword_text}里挑三个能接上的词，简单串成一段话。 "
                    f"先讲一层价值方向，再补一句{role_focus}怎么做，至少这段表达不会散掉。"
                ),
                "medium",
                True,
            ),
        ]
    if mode == "mid":
        return [
            (
                (
                    f"各位{target_group}，大家好。今天我主要想就{topic}和大家做一个简单说明。 "
                    "我知道大家最关心的，往往不是口号，而是这件事会不会增加负担、影响原来的安排，所以我先把核心意思讲清楚，再把顾虑和基本做法说明白。 "
                    "能先试着推进的，我们就从容易操作的环节先做，不要求一下子铺得太满。 "
                    "如果现场还有没听明白的地方，我们后面也可以继续沟通。"
                ),
                "medium",
                False,
            ),
            (
                (
                    f"各位{target_group}，关于{topic}这件事，我先和大家交流几点。 "
                    f"先把为什么要做、大家先怎么配合、遇到问题找谁说清楚。 "
                    f"像{topic}这类现场说明，至少要把核心风险、基本做法和后续联系讲明白，大家才更容易听进去。 "
                    "先把这些关键点听明白，比一开始记很多细节更重要，也比一上来担心成本和麻烦更重要。 "
                    "我会尽量用直白一点的话说，让大家先听懂主要内容。"
                ),
                "medium",
                False,
            ),
            (
                (
                    f"大家好，今天借这个机会，我想围绕{topic}和大家做个沟通。 "
                    "重点不是把话说得多满，而是先把为什么做、怎么试、出了问题怎么办讲清楚。 "
                    "大家先把基本意思对上，先从能接受、能配合的地方开始，后面需要补的再继续补。 "
                    "后面如果大家还有顾虑，我们再继续解释和完善。"
                ),
                "heavy",
                False,
            ),
        ]

    return [
        (
                (
                    f"大家好，今天我想简单说一下{topic}这件事。 "
                    "我知道大家可能会担心麻烦、成本或者效果，所以这次先把大致方向和基本配合方式说清楚。 "
                    "大家先有个大概印象，能先试着配合的先配合。 "
                    "后面有疑问我们再继续沟通。"
                ),
                "medium",
                True,
            ),
        (
                (
                    f"大家好，关于{topic}这件事，我先和{target_group}做个简单交流。 "
                    "主要就是把为什么做、大家先怎么配合、遇到问题找谁大概说一下。 "
                    f"像这种现场说明，先把{role_focus}这边能做什么、大家要注意什么讲清楚就可以。 "
                    "有些细节今天先不展开，也不要求一步到位。 "
                    "如果后面还有问题，我们再继续沟通。"
                ),
                "medium",
                True,
            ),
        (
                (
                    f"今天我就{topic}这个提醒和大家说明一下。 "
                    f"内容我尽量说得简单一点，先让{target_group}知道这件事为什么要重视、基本要怎么配合。 "
                    "先把风险提醒、配合方式和后续联系讲明白，整段话就不至于太空。 "
                    "后面需要补充的地方，我们再接着说。"
                ),
                "medium",
                True,
            ),
    ]


def build_template_candidates(
    question_data: dict[str, Any],
    question: QuestionDefinition,
    mode: str,
) -> list[GeneratedSample]:
    """按题型走独立模板生成中低档样本。"""

    family = detect_template_family(question_data)
    if family == "analysis":
        specs = build_analysis_template_texts(question_data, mode)
    elif family == "organization":
        specs = build_organization_template_texts(question_data, mode)
    elif family == "interpersonal":
        specs = build_interpersonal_template_texts(question_data, mode)
    elif family == "scene":
        specs = build_scene_template_texts(question_data, mode)
    else:
        return []

    minimum_length, _ = desired_length_bounds(effective_length(question_data["referenceAnswer"]), mode)
    if family == "interpersonal" and mode == "low":
        minimum_length = 0
    elif family == "interpersonal" and mode == "mid":
        minimum_length = 0
    elif family == "scene" and is_word_expression_scene(question_data) and mode == "low":
        minimum_length = max(120, minimum_length - 220)
    elif family == "scene" and is_word_expression_scene(question_data) and mode == "mid":
        minimum_length = max(220, minimum_length - 220)
    elif family == "scene" and mode == "low":
        minimum_length = max(180, minimum_length - 160)
    elif family == "scene" and mode == "mid":
        minimum_length = max(260, minimum_length - 180)
    elif family == "organization" and mode == "low":
        minimum_length = max(220, minimum_length - 120)
    elif mode == "low":
        minimum_length = max(260, minimum_length - 40)

    variants: list[GeneratedSample] = []
    seen_texts = set()
    for index, (raw_text, sanitization, oral) in enumerate(specs, start=1):
        text = clean_generated_sample_text(raw_text)
        text = apply_keyword_sanitization(text, question_data, sanitization)
        text = dilute_confident_phrases(text, mode)
        if mode == "low":
            text = soften_low_sample_tone(text)
            text = rewrite_low_opening(text, question_data)
        text = strip_role_conclusion(text, mode)
        if minimum_length > 0:
            text = extend_variant_length(text, question_data, mode, minimum_length)
        if oral and not text.startswith(("我觉得", "我想", "在我看", "大家好", "各位")):
            text = "我觉得" + text
        text = clean_generated_sample_text(text)
        if not text or text in seen_texts or should_skip_candidate(text, question_data, mode):
            continue
        seen_texts.add(text)
        variants.append(
            GeneratedSample(
                label="",
                filename="",
                text=text,
                score=score_sample_deterministically(question, text),
                strategy=f"template_{family}_{mode}_{index}",
                count=len(split_answer_sentences(text)),
                trim_chars=None,
                sanitization=sanitization,
                oral=oral,
            )
        )

    return variants


def truncate_sentence(sentence: str, trim_chars: int | None) -> str:
    """把超长句子压缩成主干信息，降低相似度但保留可读性。"""

    if trim_chars is None or len(sentence) <= trim_chars:
        return sentence.strip()

    parts = re.split(r"[，；：]", sentence)
    trimmed = ""
    for raw_part in parts:
        part = raw_part.strip("，；： ")
        if not part:
            continue
        candidate = part if not trimmed else f"{trimmed}，{part}"
        if len(candidate) > trim_chars:
            break
        trimmed = candidate

    text = (trimmed or sentence[:trim_chars]).rstrip("，；： ")
    if text and text[-1] not in "。！？；":
        text += "。"
    return text


def build_answer_variant(
    question_data: dict[str, Any],
    mode: str,
    *,
    strategy: str,
    count: int,
    trim_chars: int | None,
    sanitization: str,
    oral: bool = False,
) -> str:
    """基于高分答案构造一个降档版本。"""

    sentences = split_answer_sentences(question_data["referenceAnswer"])
    if len(sentences) <= 1:
        return clean_generated_sample_text(question_data["referenceAnswer"])

    indices = select_sentence_indices(sentences, strategy, count)
    chosen_sentences = []
    for index in indices:
        sentence = truncate_sentence(sentences[index], trim_chars)
        if mode == "low" and is_innovation_sentence(sentence):
            continue
        if mode == "low" and is_role_conclusion_sentence(sentence):
            continue
        if mode == "low" and is_detail_heavy_sentence(sentence):
            continue
        chosen_sentences.append(sentence)
    if not chosen_sentences:
        chosen_sentences = [
            truncate_sentence(sentences[index], trim_chars)
            for index in indices[: max(1, min(3, len(indices)))]
        ]
    variant = " ".join(chosen_sentences).strip()
    variant = apply_keyword_sanitization(variant, question_data, sanitization)
    variant = dilute_confident_phrases(variant, mode)
    if mode == "low":
        variant = soften_low_sample_tone(variant)
        variant = rewrite_low_opening(variant, question_data)
    variant = strip_role_conclusion(variant, mode)
    minimum_length, _ = desired_length_bounds(
        effective_length(question_data["referenceAnswer"]),
        mode,
    )
    variant = extend_variant_length(variant, question_data, mode, minimum_length)
    if oral and not variant.startswith(("我觉得", "我想", "在我看")):
        variant = "我觉得" + variant
    return clean_generated_sample_text(variant)


def build_fallback_candidates(
    question_data: dict[str, Any],
    question: QuestionDefinition,
    mode: str,
) -> list[GeneratedSample]:
    """当常规枚举被过滤空时，补一组更稳妥的兜底候选。"""

    sentences = split_answer_sentences(question_data["referenceAnswer"])
    if len(sentences) <= 1:
        return []

    total = len(sentences)
    if mode == "low":
        specs = [
            ("leading", max(4, round(total * 0.42)), 220, "heavy", True),
            ("analysis_focus", max(4, round(total * 0.45)), None, "heavy", True),
            ("hybrid", max(5, round(total * 0.5)), 220, "heavy", True),
        ]
        minimum_length = 260
    else:
        specs = [
            ("front_half", max(7, round(total * 0.6)), 320, "medium", False),
            ("spread", max(8, round(total * 0.65)), None, "medium", False),
            ("hybrid", max(8, round(total * 0.68)), 320, "light", False),
        ]
        minimum_length = 460

    variants: list[GeneratedSample] = []
    seen_texts = set()
    for strategy, count, trim_chars, sanitization, oral in specs:
        text = build_answer_variant(
            question_data,
            mode,
            strategy=strategy,
            count=count,
            trim_chars=trim_chars,
            sanitization=sanitization,
            oral=oral,
        )
        if not text or text in seen_texts or should_skip_candidate(text, question_data, mode):
            continue
        if effective_length(text) < minimum_length:
            text = extend_variant_length(text, question_data, mode, minimum_length)
        if text in seen_texts or should_skip_candidate(text, question_data, mode):
            continue
        seen_texts.add(text)
        variants.append(
            GeneratedSample(
                label="",
                filename="",
                text=text,
                score=score_sample_deterministically(question, text),
                strategy=f"fallback_{strategy}",
                count=count,
                trim_chars=trim_chars,
                sanitization=sanitization,
                oral=oral,
            )
        )
    return variants


def score_sample_deterministically(question: QuestionDefinition, transcript: str) -> float:
    """直接复用后端确定性评分链路给样本打分。"""

    evidence_packet, evidence_notes = prepare_evidence_packet(
        raw_llm_result={},
        transcript=transcript,
        question=question,
    )
    stage_two_payload = build_deterministic_stage_two_payload(
        transcript=transcript,
        question=question,
        evidence_packet=evidence_packet,
    )
    result = apply_post_processing(
        raw_llm_result=stage_two_payload,
        transcript=transcript,
        question=question,
        evidence_packet=evidence_packet,
        extra_validation_notes=evidence_notes,
    )
    return float(result.total_score)


def collect_generated_candidates(
    question_data: dict[str, Any],
    question: QuestionDefinition,
    mode: str,
    *,
    relaxed_length_floor: int | None = None,
) -> list[GeneratedSample]:
    """枚举候选文本并计算确定性分数。"""

    sentences = split_answer_sentences(question_data["referenceAnswer"])
    if len(sentences) <= 1:
        return []

    counts = sentence_count_candidates(len(sentences), mode)
    trim_candidates = [90, 120, 160, 220, None] if mode == "low" else [160, 220, 320, None]
    sanitizations = ("medium", "heavy") if mode == "low" else ("none", "light", "medium")
    oral_options = (False, True) if mode == "low" else (False,)
    strategies = (
        ("leading", "front_half", "analysis_focus", "dialogue_focus", "spread", "markers", "hybrid")
        if mode == "low"
        else ("leading", "front_half", "spread", "markers", "hybrid")
    )

    variants: list[GeneratedSample] = []
    seen_texts = set()
    length_floor = relaxed_length_floor if relaxed_length_floor is not None else (220 if mode == "low" else 420)
    for strategy in strategies:
        for count in counts:
            for trim_chars in trim_candidates:
                for sanitization in sanitizations:
                    for oral in oral_options:
                        text = build_answer_variant(
                            question_data,
                            mode,
                            strategy=strategy,
                            count=count,
                            trim_chars=trim_chars,
                            sanitization=sanitization,
                            oral=oral,
                        )
                        if (
                            not text
                            or text == clean_generated_sample_text(question_data["referenceAnswer"])
                            or text in seen_texts
                            or effective_length(text) < length_floor
                            or should_skip_candidate(text, question_data, mode)
                        ):
                            continue
                        seen_texts.add(text)
                        variants.append(
                            GeneratedSample(
                                label="",
                                filename="",
                                text=text,
                                score=score_sample_deterministically(question, text),
                                strategy=strategy,
                                count=count,
                                trim_chars=trim_chars,
                                sanitization=sanitization,
                                oral=oral,
                            )
                        )
    return variants


def choose_low_sample(
    candidates: list[GeneratedSample],
    high_score: float,
    full_score: float,
    reference_length: int,
    *,
    family: str | None = None,
    question_data: dict[str, Any] | None = None,
) -> GeneratedSample:
    """优先挑一个稳定落在中低位的样本。"""

    target_ratio = 0.18 if family in {"organization", "interpersonal", "scene"} else 0.2
    target = round(full_score * target_ratio, 1)
    minimum_length, target_length = desired_length_bounds(reference_length, "low")
    eligible = [
        candidate
        for candidate in candidates
        if candidate.score <= min(high_score - max(9.0, full_score * 0.22), full_score * 0.55)
    ] or list(candidates)

    return min(
        eligible,
        key=lambda candidate: (
            abs(candidate.score - target),
            sample_quality_penalty(candidate.text, question_data, "low") if question_data else 0,
            sample_strategy_penalty(candidate.strategy, "low"),
            0 if candidate.oral else 1,
            0 if candidate.sanitization == "heavy" else 1,
            sample_detail_score(candidate.text) * (1.3 if family in {"organization", "interpersonal", "scene"} else 1.0),
            max(0, minimum_length - effective_length(candidate.text)) / 45,
            abs(effective_length(candidate.text) - target_length) / 140,
            candidate.score,
            -effective_length(candidate.text),
        ),
    )


def choose_mid_sample(
    candidates: list[GeneratedSample],
    *,
    low_score: float,
    high_score: float,
    full_score: float,
    reference_length: int,
    family: str | None = None,
    question_data: dict[str, Any] | None = None,
) -> GeneratedSample:
    """挑选介于高分与低分之间、且和低档拉开差距的样本。"""

    target_ratio = 0.48 if family in {"organization", "interpersonal", "scene"} else 0.52
    target = round(full_score * target_ratio, 1)
    desired_gap = max(4.0, round(full_score * 0.1, 1))
    minimum_length, target_length = desired_length_bounds(reference_length, "mid")

    separated = [
        candidate
        for candidate in candidates
        if candidate.score >= low_score + desired_gap and candidate.score <= high_score - 3.0
    ]
    if separated:
        return min(
            separated,
            key=lambda candidate: (
                abs(candidate.score - target),
                sample_quality_penalty(candidate.text, question_data, "mid") if question_data else 0,
                sample_strategy_penalty(candidate.strategy, "mid"),
                max(0, minimum_length - effective_length(candidate.text)) / 70,
                sample_detail_score(candidate.text) * (1.25 if family in {"organization", "interpersonal", "scene"} else 1.0),
                0 if candidate.sanitization == "heavy" else (1 if candidate.sanitization == "medium" else 2),
                abs(effective_length(candidate.text) - target_length) / 180,
                -candidate.score,
                effective_length(candidate.text) * -0.01,
            ),
        )

    fallback = [
        candidate
        for candidate in candidates
        if candidate.score <= high_score - 3.0
    ]
    if fallback:
        return min(
            fallback,
            key=lambda candidate: (
                abs(candidate.score - target),
                sample_quality_penalty(candidate.text, question_data, "mid") if question_data else 0,
                sample_strategy_penalty(candidate.strategy, "mid"),
                max(0, minimum_length - effective_length(candidate.text)) / 70,
                sample_detail_score(candidate.text) * (1.25 if family in {"organization", "interpersonal", "scene"} else 1.0),
                0 if candidate.sanitization == "heavy" else (1 if candidate.sanitization == "medium" else 2),
                abs(effective_length(candidate.text) - target_length) / 180,
                -candidate.score,
            ),
        )

    return max(
        candidates,
        key=lambda candidate: (
            candidate.score,
            effective_length(candidate.text),
        ),
    )


def ensure_mid_low_gap(
    mid_sample: GeneratedSample,
    low_sample: GeneratedSample,
    mid_candidates: list[GeneratedSample],
    low_candidates: list[GeneratedSample],
    full_score: float,
) -> tuple[GeneratedSample, GeneratedSample]:
    """如果中低档差距太小，优先拉开分档距离。"""

    desired_gap = max(3.0, round(full_score * 0.08, 1))
    if mid_sample.score >= low_sample.score + desired_gap:
        return mid_sample, low_sample

    lower_candidates = [
        candidate
        for candidate in low_candidates
        if candidate.score <= mid_sample.score - desired_gap
    ]
    if lower_candidates:
        low_sample = min(
            lower_candidates,
            key=lambda candidate: (
                abs(candidate.score - full_score * 0.42),
                candidate.score,
            ),
        )
        if mid_sample.score >= low_sample.score + desired_gap:
            return mid_sample, low_sample

    higher_candidates = [
        candidate
        for candidate in mid_candidates
        if candidate.score >= low_sample.score + desired_gap
    ]
    if higher_candidates:
        mid_sample = min(
            higher_candidates,
            key=lambda candidate: (
                abs(candidate.score - full_score * 0.66),
                -candidate.score,
            ),
        )

    return mid_sample, low_sample


def build_reference_samples(question_data: dict[str, Any]) -> tuple[dict[str, GeneratedSample], dict[str, dict[str, Any]]]:
    """为单道题构造高/中/低三档参考样本，并记录打分元数据。"""

    question_payload = dict(question_data)
    question_payload["regressionCases"] = []
    question = QuestionDefinition.model_validate(question_payload)

    high_text = clean_generated_sample_text(question.referenceAnswer)
    high_sample = GeneratedSample(
        label="文档高分基准答案",
        filename="reference_high.txt",
        text=high_text,
        score=score_sample_deterministically(question, high_text),
        strategy="document",
        count=len(split_answer_sentences(high_text)),
        trim_chars=None,
        sanitization="none",
        oral=False,
    )

    template_family = detect_template_family(question_data)
    if template_family in {"analysis", "organization"}:
        low_candidates = build_template_candidates(question_data, question, "low")
        mid_candidates = build_template_candidates(question_data, question, "mid")
    elif template_family in {"interpersonal", "scene"}:
        low_candidates = build_template_candidates(question_data, question, "low")
        mid_candidates = build_template_candidates(question_data, question, "mid")
    else:
        low_candidates = []
        mid_candidates = []

    if not low_candidates:
        low_candidates = collect_generated_candidates(question_data, question, "low")
    if not mid_candidates:
        mid_candidates = collect_generated_candidates(question_data, question, "mid")
    if not low_candidates:
        low_candidates = collect_generated_candidates(question_data, question, "low", relaxed_length_floor=140)
    if not mid_candidates:
        mid_candidates = collect_generated_candidates(question_data, question, "mid", relaxed_length_floor=320)
    if not low_candidates:
        low_candidates = build_fallback_candidates(question_data, question, "low")
    if not mid_candidates:
        mid_candidates = build_fallback_candidates(question_data, question, "mid")
    if not low_candidates or not mid_candidates:
        raise ValueError(f"{question.id} 未能生成足够的中低档候选样本")

    reference_length = effective_length(question.referenceAnswer)
    low_sample = choose_low_sample(
        low_candidates,
        high_sample.score,
        question.fullScore,
        reference_length,
        family=template_family,
        question_data=question_data,
    )
    mid_sample = choose_mid_sample(
        mid_candidates,
        low_score=low_sample.score,
        high_score=high_sample.score,
        full_score=question.fullScore,
        reference_length=reference_length,
        family=template_family,
        question_data=question_data,
    )
    mid_sample, low_sample = ensure_mid_low_gap(
        mid_sample,
        low_sample,
        mid_candidates,
        low_candidates,
        question.fullScore,
    )

    labeled_mid = GeneratedSample(
        label="程序化中档参考答案",
        filename="reference_mid.txt",
        text=mid_sample.text,
        score=mid_sample.score,
        strategy=mid_sample.strategy,
        count=mid_sample.count,
        trim_chars=mid_sample.trim_chars,
        sanitization=mid_sample.sanitization,
        oral=mid_sample.oral,
    )
    labeled_low = GeneratedSample(
        label="程序化低档参考答案",
        filename="reference_low.txt",
        text=low_sample.text,
        score=low_sample.score,
        strategy=low_sample.strategy,
        count=low_sample.count,
        trim_chars=low_sample.trim_chars,
        sanitization=low_sample.sanitization,
        oral=low_sample.oral,
    )

    samples = {
        "high": high_sample,
        "mid": labeled_mid,
        "low": labeled_low,
    }
    sample_meta = {
        level: {
            "score": sample.score,
            "strategy": sample.strategy,
            "count": sample.count,
            "trim_chars": sample.trim_chars,
            "sanitization": sample.sanitization,
            "oral": sample.oral,
            "effective_length": effective_length(sample.text),
        }
        for level, sample in samples.items()
    }
    return samples, sample_meta


def build_score_bands(full_score: float) -> list[dict]:
    """按统一比例生成分档。"""

    low_max = round(full_score * 0.55, 1)
    pass_max = round(full_score * 0.7, 1)
    good_max = round(full_score * 0.85, 1)
    return [
        {
            "label": "低分/偏弱",
            "min_score": 0,
            "max_score": low_max,
            "description": "核心要点覆盖不足，结构或岗位适配明显欠缺。",
        },
        {
            "label": "基本合格",
            "min_score": round(low_max + 0.1, 1),
            "max_score": pass_max,
            "description": "能覆盖主要要求，但深度、结构或本土化仍有短板。",
        },
        {
            "label": "中高档",
            "min_score": round(pass_max + 0.1, 1),
            "max_score": good_max,
            "description": "内容较完整，逻辑较清晰，接近高分答案。",
        },
        {
            "label": "高分标杆",
            "min_score": round(good_max + 0.1, 1),
            "max_score": full_score,
            "description": "高分参考答案区间，用于回归验证。",
        },
    ]


def bounded_expected_range(
    score: float,
    *,
    margin: float,
    lower_bound: float,
    upper_bound: float,
) -> tuple[float, float]:
    """给程序化样本构造一个稳定且尽量不重叠的预期分数区间。"""

    lower_bound = round(max(0.0, lower_bound), 1)
    upper_bound = round(max(0.0, upper_bound), 1)
    if upper_bound < lower_bound:
        upper_bound = lower_bound

    lower = round(max(lower_bound, score - margin), 1)
    upper = round(min(upper_bound, score + margin), 1)
    if upper < lower:
        center = round(min(max(score, lower_bound), upper_bound), 1)
        lower = round(max(lower_bound, center - 1.0), 1)
        upper = round(min(upper_bound, center + 1.0), 1)
        if upper < lower:
            lower = upper = center
    return lower, upper


def build_initial_llm_expected_range(
    level: str,
    *,
    deterministic_min: float,
    deterministic_max: float,
    full_score: float,
    lower_bound: float,
    upper_bound: float,
    family: str | None = None,
) -> tuple[float, float]:
    """给 LLM 回归先写一组初始区间，后续可被正式标定脚本回写。"""

    if level == "high":
        return round(deterministic_min, 1), round(min(full_score, deterministic_max), 1)

    if level == "mid":
        uplift = max(0.5, full_score * 0.02)
        margin = 3.0
        if family in {"interpersonal", "scene"}:
            uplift = max(0.2, uplift - 0.4)
            margin = 3.2
    else:
        uplift = max(0.8, full_score * 0.03)
        margin = 3.6
        if family in {"interpersonal", "scene"}:
            uplift = max(0.2, full_score * 0.015)
            margin = 3.8
    center = (deterministic_min + deterministic_max) / 2 + uplift
    llm_min, llm_max = bounded_expected_range(
        center,
        margin=margin,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
    )
    return round(llm_min, 1), round(llm_max, 1)


def build_regression_cases(
    question_id: str,
    full_score: float,
    samples: dict[str, GeneratedSample],
    *,
    family: str | None = None,
) -> list[dict]:
    """为每道题挂载高 / 中 / 低三档回归样本。"""

    high_sample = samples["high"]
    mid_sample = samples["mid"]
    low_sample = samples["low"]

    high_expected_min = round(max(full_score - 3.0, full_score * 0.85), 1)
    mid_min, mid_max = bounded_expected_range(
        mid_sample.score,
        margin=2.5,
        lower_bound=round(low_sample.score + 0.5, 1),
        upper_bound=round(high_expected_min - 0.5, 1),
    )
    low_min, low_max = bounded_expected_range(
        low_sample.score,
        margin=2.5,
        lower_bound=0.0,
        upper_bound=round(mid_sample.score - 0.5, 1),
    )
    high_llm_min, high_llm_max = build_initial_llm_expected_range(
        "high",
        deterministic_min=high_expected_min,
        deterministic_max=full_score,
        full_score=full_score,
        lower_bound=high_expected_min,
        upper_bound=full_score,
        family=family,
    )
    mid_llm_min, mid_llm_max = build_initial_llm_expected_range(
        "mid",
        deterministic_min=mid_min,
        deterministic_max=mid_max,
        full_score=full_score,
        lower_bound=round(low_max + 0.5, 1),
        upper_bound=round(high_llm_min - 0.5, 1),
        family=family,
    )
    low_llm_min, low_llm_max = build_initial_llm_expected_range(
        "low",
        deterministic_min=low_min,
        deterministic_max=low_max,
        full_score=full_score,
        lower_bound=0.0,
        upper_bound=round(mid_llm_min - 0.5, 1),
        family=family,
    )

    base_path = f"{REGRESSION_SAMPLE_BASE_PATH}/{question_id}"
    return [
        {
            "label": high_sample.label,
            "sample_path": f"{base_path}/{high_sample.filename}",
            "expected_min": high_expected_min,
            "expected_max": full_score,
            "llmExpectedMin": high_llm_min,
            "llmExpectedMax": high_llm_max,
            "notes": "来自原始题库文档的核心采分基准答案。",
        },
        {
            "label": mid_sample.label,
            "sample_path": f"{base_path}/{mid_sample.filename}",
            "expected_min": mid_min,
            "expected_max": mid_max,
            "llmExpectedMin": mid_llm_min,
            "llmExpectedMax": mid_llm_max,
            "notes": (
                "基于高分答案程序化压缩生成；"
                f"策略={mid_sample.strategy}，句数={mid_sample.count}，"
                f"截断={mid_sample.trim_chars or 'none'}，关键词削弱={mid_sample.sanitization}。"
            ),
        },
        {
            "label": low_sample.label,
            "sample_path": f"{base_path}/{low_sample.filename}",
            "expected_min": low_min,
            "expected_max": low_max,
            "llmExpectedMin": low_llm_min,
            "llmExpectedMax": low_llm_max,
            "notes": (
                "基于高分答案程序化降档生成；"
                f"策略={low_sample.strategy}，句数={low_sample.count}，"
                f"截断={low_sample.trim_chars or 'none'}，关键词削弱={low_sample.sanitization}，"
                f"口语化={'是' if low_sample.oral else '否'}。"
            ),
        },
    ]


def parse_question_block(block: str, source_path: Path) -> ParsedQuestion:
    """把单个题目块解析成 QuestionDefinition 所需的字典。"""

    header_match = HEADER_PATTERN.search(block)
    if not header_match:
        raise ValueError(f"无法解析题目头部: {source_path.name}")

    question_id = normalize_question_id(header_match.group(1))
    header_description = (header_match.group(2) or "").strip()
    sections = extract_sections(block)

    question_text = sections.get("题干", "").strip()
    reference_answer = sections.get("核心采分基准答案", "").strip()
    scoring_criteria = parse_scored_items(sections.get("得分标准", ""))
    deduction_rules = parse_deduction_items(sections.get("扣分标准", ""))
    ai_text = sections.get("AI评分结构化数据", "")

    if not question_text:
        raise ValueError(f"{question_id} 缺少题干")
    if not reference_answer:
        raise ValueError(f"{question_id} 缺少核心采分基准答案")
    if not scoring_criteria:
        raise ValueError(f"{question_id} 缺少得分标准")

    dimensions = build_dimensions(scoring_criteria)
    full_score = resolve_full_score(
        question_text=question_text,
        header_description=header_description,
        scoring_section_text=sections.get("得分标准", ""),
        ai_text=ai_text,
        dimensions=dimensions,
    )
    dimensions = scale_dimensions_to_full_score(dimensions, full_score)

    source_document = infer_source_document(source_path)
    province = extract_field(ai_text, FIELD_PATTERNS["province"]) or DEFAULT_PROVINCE
    question_type = clean_question_type(
        extract_field(ai_text, FIELD_PATTERNS["type"]) or sections.get("题型定位", ""),
        header_description,
    )
    core_keywords = split_list(extract_field(ai_text, FIELD_PATTERNS["core_keywords"]))
    strong_keywords = split_list(extract_field(ai_text, FIELD_PATTERNS["strong_keywords"]))
    weak_keywords = split_list(extract_field(ai_text, FIELD_PATTERNS["weak_keywords"]))
    bonus_keywords = split_list(extract_field(ai_text, FIELD_PATTERNS["bonus_keywords"]))
    penalty_keywords = split_list(extract_field(ai_text, FIELD_PATTERNS["penalty_keywords"]))

    data = {
        "id": question_id,
        "type": question_type.strip(),
        "province": province.strip(),
        "fullScore": full_score,
        "question": question_text,
        "dimensions": dimensions,
        "coreKeywords": core_keywords,
        "strongKeywords": strong_keywords,
        "weakKeywords": weak_keywords,
        "bonusKeywords": bonus_keywords,
        "penaltyKeywords": penalty_keywords,
        "scoringCriteria": scoring_criteria,
        "deductionRules": deduction_rules,
        "sourceDocument": source_document,
        "referenceAnswer": reference_answer,
        "tags": build_tags(
            sections.get("检索标签", ""),
            question_type=question_type,
            keyword_groups=[core_keywords, strong_keywords],
        ),
        "scoreBands": build_score_bands(full_score),
        "regressionCases": [],
        "_meta": {
            "headerDescription": header_description,
            "sourceText": source_path.name,
        },
    }
    return ParsedQuestion(data=data, source_path=source_path, block_length=len(block))


def should_replace(existing: ParsedQuestion, candidate: ParsedQuestion) -> bool:
    """重复题号时，优先保留更高优先级或信息更完整的版本。"""

    existing_priority = SOURCE_PRIORITY.get(existing.source_path.name, 0)
    candidate_priority = SOURCE_PRIORITY.get(candidate.source_path.name, 0)
    if candidate_priority != existing_priority:
        return candidate_priority > existing_priority
    return candidate.block_length > existing.block_length


def prepare_output_dirs() -> None:
    """清理自动生成目录，避免旧文件残留。"""

    QUESTION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for json_file in QUESTION_OUTPUT_DIR.glob("*.json"):
        json_file.unlink()
    for sample_file in SAMPLE_OUTPUT_DIR.rglob("*.txt"):
        sample_file.unlink()
    for directory in sorted(SAMPLE_OUTPUT_DIR.glob("*"), reverse=True):
        if directory.is_dir():
            directory.rmdir()


def write_question_files(parsed_questions: dict[str, ParsedQuestion]) -> dict[str, dict[str, Any]]:
    """把导入结果落成 JSON 与高/中/低参考答案样本。"""

    sample_generation_summary: dict[str, dict[str, Any]] = {}

    for question_id, parsed in sorted(parsed_questions.items()):
        question_dir = SAMPLE_OUTPUT_DIR / question_id
        question_dir.mkdir(parents=True, exist_ok=True)

        json_payload = dict(parsed.data)
        samples, sample_meta = build_reference_samples(json_payload)
        for sample in samples.values():
            (question_dir / sample.filename).write_text(sample.text, encoding="utf-8")

        json_payload["referenceAnswer"] = samples["high"].text
        json_payload["regressionCases"] = build_regression_cases(
            question_id=question_id,
            full_score=float(json_payload["fullScore"]),
            samples=samples,
            family=detect_template_family(json_payload),
        )
        json_payload.pop("_meta", None)
        (QUESTION_OUTPUT_DIR / f"{question_id}.json").write_text(
            json.dumps(json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        sample_generation_summary[question_id] = sample_meta

    return sample_generation_summary


def write_summary(
    parsed_questions: dict[str, ParsedQuestion],
    duplicates: list[dict],
    sample_generation_summary: dict[str, dict[str, Any]],
) -> None:
    """输出导入摘要，便于核对。"""

    summary = {
        "profile": ACTIVE_PROFILE.name,
        "province": DEFAULT_PROVINCE,
        "source_files": [path.name for path in SOURCE_FILES],
        "generated_question_count": len(parsed_questions),
        "generated_question_ids": sorted(parsed_questions),
        "duplicates": duplicates,
        "sample_generation": sample_generation_summary,
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_profile_import(profile_name: str | ImportProfile) -> int:
    """执行指定 profile 的题库导入。"""

    activate_profile(profile_name)
    prepare_output_dirs()

    parsed_questions: dict[str, ParsedQuestion] = {}
    duplicates: list[dict] = []

    for source_path in SOURCE_FILES:
        if not source_path.exists():
            raise FileNotFoundError(f"未找到源文件: {source_path}")

        normalized_text = normalize_source_text(
            source_path.read_text(encoding="utf-8", errors="ignore"),
            source_path.name,
        )
        for block in iter_question_blocks(normalized_text):
            parsed = parse_question_block(block, source_path)
            question_id = parsed.data["id"]
            existing = parsed_questions.get(question_id)
            if existing is None:
                parsed_questions[question_id] = parsed
                continue

            replace = should_replace(existing, parsed)
            duplicates.append(
                {
                    "question_id": question_id,
                    "kept": parsed.source_path.name if replace else existing.source_path.name,
                    "discarded": existing.source_path.name if replace else parsed.source_path.name,
                }
            )
            if replace:
                parsed_questions[question_id] = parsed

    sample_generation_summary = write_question_files(parsed_questions)
    write_summary(parsed_questions, duplicates, sample_generation_summary)

    print(f"[{ACTIVE_PROFILE.name}] 导入完成，共生成 {len(parsed_questions)} 道题。")
    print(f"题库 JSON 目录: {QUESTION_OUTPUT_DIR}")
    print(f"高/中/低样本目录: {SAMPLE_OUTPUT_DIR}")
    print(f"导入摘要: {SUMMARY_PATH}")
    return 0


def render_builtin_profiles() -> str:
    """把当前内置 profile 列表渲染成终端可读文本。"""

    lines = ["当前内置 profile："]
    for name, profile in sorted(IMPORT_PROFILES.items()):
        lines.append(
            f"- {name}: 默认省份={profile.default_province}，"
            f"源文件数={len(profile.source_files)}，"
            f"输出目录={profile.question_output_dir.name}"
        )
    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""

    parser = argparse.ArgumentParser(description="导入 profile 化题库文本。")
    parser.add_argument(
        "--profile",
        choices=sorted(IMPORT_PROFILES),
        help="选择内置题库 profile。默认 hunan。",
    )
    parser.add_argument(
        "--profile-name",
        help="创建临时自定义 profile 名称，例如 guangdong。会输出到 generated_<profile-name>/。",
    )
    parser.add_argument(
        "--province",
        help="自定义 profile 的默认省份名称，例如 广东。",
    )
    parser.add_argument(
        "--source-file",
        action="append",
        dest="source_files",
        help="自定义 profile 的 .extracted.txt 源文件路径，可重复传入多个。",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="只打印当前内置 profile 列表，不执行导入。",
    )
    return parser


def resolve_profile_from_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str | ImportProfile:
    """把 CLI 参数转换成内置 profile 或临时 profile。"""

    custom_mode = bool(args.profile_name or args.province or args.source_files)
    if custom_mode:
        if args.profile:
            parser.error("自定义地区导入模式下不要同时传 --profile，请改用 --profile-name/--province/--source-file。")
        if not args.profile_name:
            parser.error("自定义地区导入模式下必须提供 --profile-name，例如 guangdong。")
        if not args.province:
            parser.error("自定义地区导入模式下必须提供 --province，例如 广东。")
        if not args.source_files:
            parser.error("自定义地区导入模式下至少需要一个 --source-file。")
        return build_runtime_profile(args.profile_name, args.province, args.source_files)
    return args.profile or "hunan"


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""

    parser = build_argument_parser()
    args = parser.parse_args(argv)
    if args.list_profiles:
        print(render_builtin_profiles())
        return 0
    return run_profile_import(resolve_profile_from_args(args, parser))


if __name__ == "__main__":
    raise SystemExit(main())
