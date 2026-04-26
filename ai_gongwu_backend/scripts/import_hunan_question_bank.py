#!/usr/bin/env python3
"""把湖南题库文档导入为后端可读取的结构化 JSON。

这个脚本做的事情比较多，但目的很单一：
1. 读取仓库根目录下的 4 份湖南题库提取文本
2. 清洗不同文档之间不一致的格式
3. 把每道题解析成后端当前 schema 能直接加载的 JSON
4. 为每道题生成高 / 中 / 低三档参考答案样本，接入 regressionCases
5. 输出一份导入摘要，方便核查重复题号和导入数量

脚本设计成“可重复执行”：
- 生成目录固定在 assets/questions/generated_hunan
- 每次执行都会覆盖该目录下旧的自动生成文件
- 现有手写题库不会被改动
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
QUESTION_OUTPUT_DIR = BACKEND_ROOT / "assets" / "questions" / "generated_hunan"
SAMPLE_OUTPUT_DIR = BACKEND_ROOT / "assets" / "regression_samples" / "generated_hunan"
SUMMARY_PATH = QUESTION_OUTPUT_DIR / "import_summary.txt"

SOURCE_FILES = [
    REPO_ROOT / "湖南-2020-乡镇岗、遴选岗全.extracted.txt",
    REPO_ROOT / "湖南-监狱-2020.extracted.txt",
    REPO_ROOT / "湖南-税务系统补录-2020-816.extracted.txt",
    REPO_ROOT / "湖南-2020-通用岗.extracted.txt",
]
SOURCE_PRIORITY = {
    "湖南-2020-乡镇岗、遴选岗全.extracted.txt": 100,
    "湖南-监狱-2020.extracted.txt": 90,
    "湖南-税务系统补录-2020-816.extracted.txt": 80,
    "湖南-2020-通用岗.extracted.txt": 70,
}

SECTION_HEADERS = (
    "题干",
    "题型定位",
    "核心观点（多维）",
    "核心采分基准答案",
    "多角度同义表述库",
    "加分点（创新思维）",
    "得分标准",
    "扣分标准",
    "AI评分使用的结构化数据",
    "AI评分结构化数据",
    "全局统一表达仪态分",
    "本题总分计算规则",
    "检索标签",
)
SECTION_PATTERN = re.compile(
    r"(?:^|\n)\s*(\d{1,2})[.、 ]\s*"
    r"(题干|题型定位|核心观点(?:（多维）)?|核心采分基准答案|多角度同义表述库|"
    r"加分点(?:（创新思维）)?|得分标准|扣分标准|AI评分(?:使用的)?结构化数据|"
    r"全局统一表达仪态分|本题总分计算规则|检索标签)"
)
QUESTION_ID_PATTERN = re.compile(r"题号：\s*([A-Z]{2,}(?:-[A-Z0-9]{2,})+)")
HEADER_PATTERN = re.compile(r"题号：\s*([A-Z]{2,}(?:-[A-Z0-9]{2,})+)（([^）]+)）")
FIELD_PATTERNS = {
    "type": [
        r"题型[:：]\s*([^；。\n]+)",
        r"题型定位\s*([^。\n]+)",
    ],
    "province": [
        r"适用省份[:：]\s*([^，；。\n]+)",
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

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.schemas import QuestionDefinition
from app.services.scoring.calculator import (
    apply_post_processing,
    build_deterministic_stage_two_payload,
    prepare_evidence_packet,
)


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

    # 有些文档把 “1 + 换行 + 题干” 拆开了，这里统一修成 “1. 题干”。
    for header in SECTION_HEADERS:
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
    if raw_name.startswith("加分点"):
        return "加分点（创新思维）"
    if raw_name.startswith("AI评分"):
        return "AI评分结构化数据"
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
        value = item.strip()
        if not value or value in seen:
            continue
        values.append(value)
        seen.add(value)
    return values


def build_tags(text: str) -> list[str]:
    """标签单独清洗，去掉跨块残留的“面试题库”尾巴。"""

    tags = split_list(text, include_whitespace=True)
    return [tag for tag in tags if tag and "面试题库" not in tag]


def parse_scored_items(section_text: str) -> list[str]:
    """从“得分标准”中提取每条评分项。"""

    normalized = " ".join(section_text.split())
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


def infer_dimension_name(criterion_text: str, used_names: set[str]) -> str:
    """给评分项生成一个尽量短、可读的维度名。"""

    text = criterion_text

    if "创新" in text or "创意" in text or "亮点" in text:
        base_name = "创新思维"
    elif "契合" in text or "完整逻辑" in text:
        base_name = "整体契合度"
    elif "宣传语" in text:
        base_name = "宣传语创意"
    elif "立意" in text:
        base_name = "立意深度"
    elif "出发点" in text:
        base_name = "出发点适配"
    elif "词语" in text:
        base_name = "词语运用"
    elif "价值导向" in text or ("价值" in text and "担当" in text):
        base_name = "价值导向"
    elif "适老化" in text:
        base_name = "适老化设计"
    elif "安全保障" in text or ("保障" in text and "安全" in text):
        base_name = "安全保障"
    elif "沟通" in text or "人际" in text:
        base_name = "沟通化解"
    elif "统筹" in text or "交接" in text:
        base_name = "工作统筹"
    elif "语言" in text or "表达" in text or "感染力" in text:
        base_name = "语言表达"
    elif "措施" in text or "举措" in text or "路径" in text or "建议" in text:
        base_name = "对策措施"
    elif any(marker in text for marker in ("分析", "解读", "内涵", "危害", "根源", "理解", "题干")):
        base_name = "分析理解"
    elif "案例选取" in text or text.startswith("案例"):
        base_name = "案例适配"
    elif "场景" in text or "现场模拟" in text or "宣讲" in text:
        base_name = "场景适配"
    elif "流程" in text or "实施" in text or "筹备" in text:
        base_name = "流程执行"
    elif "方案" in text or "活动" in text:
        base_name = "方案设计"
    elif "岗位" in text or "适配" in text or "省情" in text:
        base_name = "岗位适配"
    else:
        base_name = text.split("，", 1)[0].split("（", 1)[0].strip()[:12] or "评分维度"

    candidate = base_name
    suffix = 2
    while candidate in used_names:
        candidate = f"{base_name}{suffix}"
        suffix += 1
    used_names.add(candidate)
    return candidate


def build_dimensions(scoring_criteria: list[str]) -> list[dict]:
    """从评分标准构造 schema 里的 dimensions 字段。"""

    used_names: set[str] = set()
    dimensions = []
    for item in scoring_criteria:
        dimensions.append(
            {
                "name": infer_dimension_name(item, used_names),
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

    question_text = question_data.get("question", "")
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


def generic_bridge_sentences(question_data: dict[str, Any], mode: str) -> list[str]:
    """长度不足时补几句泛化过的桥接语，让样本更像真实答题文本。"""

    province = question_data.get("province", "当地") or "当地"
    if mode == "mid":
        bridges = [
            f"整体看，这项工作方向是对的，但真正落地还要结合{province}实际，不能只停留在表态层面。",
            "如果只讲原则、不讲重点，或者只看局部、不看整体，后续执行效果就容易打折扣。",
            "所以作答时既要看到积极意义，也要把问题和短板说透，再把改进方向交代清楚。",
            "另外还要把原则判断和具体做法区分开，避免前后都在重复同一个意思。",
            "如果只是材料罗列得多，但没有把重点拎出来，整体表达也还是会显得发散。",
            "从答题思路看，关键还是先把主判断说清，再补充原因和大方向上的措施。",
        ]
    else:
        bridges = [
            "总体看，这件事不能只看表面，还是得放到实际工作里去考虑。",
            "我觉得方向要把握住，但推进的时候也不能太着急，不然容易顾此失彼。",
            "如果前面考虑得不细，后续执行起来还可能冒出新的问题。",
            "另外就是回答时不能什么都想说，不然重点反而容易散掉。",
            "有些内容看着很具体，但真正落到执行层面，还得再结合实际条件慢慢细化。",
            "所以我觉得先把基本判断说稳，再补几条主要想法，会比一上来堆很多细节更合适。",
        ]
    return [clean_generated_sample_text(sentence) for sentence in bridges]


def extend_variant_length(text: str, question_data: dict[str, Any], mode: str, minimum_length: int) -> str:
    """如果候选文本过短，就补几句低信息密度的桥接语。"""

    extended = text
    bridges = generic_bridge_sentences(question_data, mode)
    if not bridges:
        return extended

    max_rounds = 2 if mode == "low" else 1
    for index in range(len(bridges) * max_rounds):
        if effective_length(extended) >= minimum_length:
            break
        bridge_sentence = bridges[index % len(bridges)]
        extended = clean_generated_sample_text(f"{extended} {bridge_sentence}")
    return extended


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
    if any(marker in haystack for marker in ("计划组织", "活动设计", "活动方案", "宣传活动", "组织开展")):
        return "organization"
    if any(marker in haystack for marker in ("综合分析", "价值判断", "政策理解", "社会现象", "漫画解读")):
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


def infer_role_focus(question_data: dict[str, Any]) -> str:
    """粗略提炼题目对应的岗位/工作语境。"""

    haystack = build_question_haystack(question_data)
    mappings = (
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
        ("服刑人员", "服刑人员"),
        ("罪犯", "服刑人员"),
        ("犯人", "服刑人员"),
        ("老年", "老年人"),
        ("老人", "老年人"),
        ("群众", "群众"),
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


def build_analysis_template_texts(question_data: dict[str, Any], mode: str) -> list[tuple[str, str, bool]]:
    """为综合分析/价值判断题生成中低档模板文本。"""

    topic = infer_topic_phrase(question_data, generic=False)
    topic2 = ordered_keywords(question_data, generic=False)[1:2]
    topic2_text = topic2[0] if topic2 else "现实需求"
    aux_topic = infer_topic_phrase(question_data, generic=mode == "low")
    if mode == "mid":
        return [
            (
                (
                    f"我认为这类题不能只讲一个态度，还是要把基本判断和现实问题一起说。 "
                    f"从正面看，{topic}和{topic2_text}说明相关工作确实有一定现实背景。 "
                    f"但如果推进时考虑不够细，{aux_topic}也可能出现表面化、简单化的问题，最后影响效果。 "
                    "所以回答时至少要把方向、问题和大致改进思路说明白，不能只停留在空泛表态上。 "
                    "后面更重要的是先把情况摸清，再针对主要问题做一些调整，避免一上来铺得太开。"
                ),
                "medium",
                False,
            ),
            (
                (
                    f"我觉得这个问题既不能全盘否定，也不能简单肯定。 "
                    f"{topic}本身未必有问题，关键还是要看后面怎么落。 "
                    f"如果前期判断太满、后面推进太快，{aux_topic}就容易流于形式，最后看起来做了不少，实际效果一般。 "
                    "所以后面还是要把问题摸准，再把重点环节理顺，至少别让工作停在口号层面。"
                ),
                "medium",
                False,
            ),
            (
                (
                    f"这类题我会先看它为什么做，再看它容易出什么问题。 "
                    f"如果只讲{topic}的积极意义，回答会偏空；如果只讲问题，不讲基本方向，也不够完整。 "
                    f"所以更稳妥的说法，是先承认{topic}有现实考虑，再指出{aux_topic}在落实中可能会有偏差，最后补一句原则性的改进思路。"
                ),
                "heavy",
                False,
            ),
        ]

    return [
        (
            (
                "我觉得这个问题不能只看一面，还是要结合实际分开来看。 "
                f"方向上未必有问题，但真正难的是后面能不能把{aux_topic}落到实处。 "
                f"如果前面考虑得不够细，执行中就可能出现偏差，最后让工作效果打折。 "
                "所以后续可以先把基本情况摸一摸，再看怎么往前推。 "
                "总的看，我会先把主要问题和大方向说清楚。"
            ),
            "heavy",
            True,
        ),
        (
            (
                "我觉得这件事还是要看实际效果。 "
                f"有些工作从出发点看是好的，但如果推进得太急，{aux_topic}就容易变成表面动作。 "
                "所以更重要的还是结合具体情况一步一步来，把重点问题先拎出来。 "
                "回答时把判断、问题和基本做法说清楚就行。"
            ),
            "heavy",
            True,
        ),
        (
            (
                "在我看，这类问题最怕的不是方向有偏差，而是说得很多、落得不够。 "
                f"如果只讲态度、不讲条件，{aux_topic}最后就可能没有真正起作用。 "
                "后面还是要把情况摸清，再看怎么处理。 "
                "我觉得这样回答会更稳一些。"
            ),
            "heavy",
            True,
        ),
    ]


def build_organization_template_texts(question_data: dict[str, Any], mode: str) -> list[tuple[str, str, bool]]:
    """为计划组织题生成中低档模板文本。"""

    target_group = infer_target_group(question_data, generic=mode == "low")
    topic = infer_topic_phrase(question_data, generic=mode == "low")
    if mode == "mid":
        return [
            (
                (
                    "如果让我来做这项工作，我会先把基本安排理顺，再把现场环节抓起来，最后补一个简单跟进。 "
                    f"前面先看看{target_group}比较关心什么，把通知、时间和人员分工先定下来。 "
                    f"中间围绕{topic}把重点内容讲清楚，再留一点互动和答疑，确保大家能听懂。 "
                    "结束后把反馈收一收，看看还有哪些问题需要后面继续补。 "
                    "整体上不追求铺得很大，但流程不能乱。"
                ),
                "medium",
                False,
            ),
            (
                (
                    f"这类活动我会先把对象、场地和时间这些基础项定下来。 "
                    f"现场主要围绕{topic}做说明和互动，不会一开始安排太多环节。 "
                    f"只要让{target_group}知道活动在讲什么、后面遇到问题怎么继续问，基本目的就算达到了。 "
                    "活动结束后再把现场反馈做个整理，作为后面调整的依据。"
                ),
                "medium",
                False,
            ),
            (
                (
                    "我会把这个方案想得简单一点。 "
                    f"前面先做通知和基本准备，中间把{topic}讲清楚，后面留一个反馈和继续跟进的口子。 "
                    f"这样既能照顾到{target_group}的接受程度，也能避免活动设计得太满。"
                ),
                "heavy",
                False,
            ),
        ]

    return [
        (
            (
                "我觉得这个活动可以先按一个基础框架来做。 "
                f"前面先把{target_group}和大致安排确定好。 "
                f"现场主要把{topic}的基本内容讲一讲，让大家先有个了解。 "
                "活动结束后再看反馈，后面有需要再补。 "
                "整体上先把活动办起来就行。"
            ),
            "heavy",
            True,
        ),
        (
            (
                "我觉得这项工作不用一开始就设计得特别复杂。 "
                f"可以先做通知和简单准备，再围绕{topic}做现场说明，最后留一个后续联系的口子。 "
                f"这样既能让{target_group}知道活动在干什么，也方便后面再慢慢调整。 "
                "对我来说，先把基本框架搭起来更重要。"
            ),
            "heavy",
            True,
        ),
        (
            (
                "这个活动我会先按一个基础骨架来想。 "
                "前面把对象、时间和基本安排先理顺，中间把核心内容说明白，后面再做简单反馈。 "
                f"只要{target_group}能跟上节奏，现场不乱，这个活动就能先运转起来。 "
                "后续如果效果一般，再边做边调也来得及。"
            ),
            "heavy",
            True,
        ),
    ]


def build_interpersonal_template_texts(question_data: dict[str, Any], mode: str) -> list[tuple[str, str, bool]]:
    """为人际沟通题生成中低档模板文本。"""

    target_group = infer_target_group(question_data, generic=False)
    topic = infer_topic_phrase(question_data, generic=False)
    if mode == "mid":
        return [
            (
                (
                    f"如果是我来沟通，我会先把态度放缓一点，先听听{target_group}真正担心什么。 "
                    f"然后再把和{topic}有关的情况解释清楚，至少让对方知道这件事为什么要做、现在卡在哪里。 "
                    "沟通的时候我不会一上来就强调要求，而是先把情绪稳住，再把能协调的地方说清楚。 "
                    "最后我会留一个继续联系的口子，避免一次谈完就结束。"
                ),
                "medium",
                False,
            ),
            (
                (
                    "我觉得这类题关键还是先把关系稳住。 "
                    f"面对{target_group}，我会先表示理解，再把事情的来龙去脉和基本想法讲清楚。 "
                    f"如果对方对{topic}还有顾虑，我会先回应最核心的问题，不急着一次把所有内容都讲满。 "
                    "后面再看对方反应，边沟通边调整。"
                ),
                "medium",
                False,
            ),
            (
                (
                    "这类沟通题我会先重态度、再重解释。 "
                    f"先让{target_group}感受到我是在解决问题，不是在和他争。 "
                    f"然后再围绕{topic}把基本情况说明白，能当场解决的先处理，不能马上解决的后面继续跟。"
                ),
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
                    "第一是为什么要做，第二是大家先怎么配合更合适，第三是后面遇到问题怎么边做边调。 "
                    "先把核心内容听明白，比一开始记很多细节更重要，也比一上来担心成本和麻烦更重要。 "
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
                "heavy",
                True,
            ),
        (
                (
                    "大家好，关于这个事情，我先和大家做个简单交流。 "
                    "主要就是把为什么做、先从哪里做大概说一下。 "
                    "有些细节今天先不展开，也不要求一步到位。 "
                    "如果后面还有问题，我们再继续沟通。"
                ),
                "heavy",
                True,
            ),
        (
                (
                    "今天我就这个安排和大家说明一下。 "
                    "内容我尽量说得简单一点，先让大家有个基本了解。 "
                    "大家先知道大概怎么回事、后面大概要怎么配合就可以。 "
                    "后面需要补充的地方，我们再接着说。"
                ),
                "heavy",
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
    if family in {"interpersonal", "scene"} and mode == "low":
        minimum_length = 0
    elif family in {"interpersonal", "scene"} and mode == "mid":
        minimum_length = 0
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
        if oral and not text.startswith(("我觉得", "我想", "在我看")):
            text = "我觉得" + text
        text = clean_generated_sample_text(text)
        if not text or text in seen_texts:
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
        if not text or text in seen_texts:
            continue
        if effective_length(text) < minimum_length:
            text = extend_variant_length(text, question_data, mode, minimum_length)
        if text in seen_texts:
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
                            or effective_length(text) < (220 if mode == "low" else 420)
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
    )
    mid_sample = choose_mid_sample(
        mid_candidates,
        low_score=low_sample.score,
        high_score=high_sample.score,
        full_score=question.fullScore,
        reference_length=reference_length,
        family=template_family,
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

    base_path = f"assets/regression_samples/generated_hunan/{question_id}"
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

    question_id = header_match.group(1).strip()
    header_description = header_match.group(2).strip()
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
    full_score = sum(item["score"] for item in dimensions)

    configured_full_score = extract_field(ai_text, FIELD_PATTERNS["full_score"])
    if configured_full_score:
        full_score = float(configured_full_score)
        dimensions = scale_dimensions_to_full_score(dimensions, full_score)

    source_document = infer_source_document(source_path)
    province = extract_field(ai_text, FIELD_PATTERNS["province"]) or "湖南"
    question_type = extract_field(ai_text, FIELD_PATTERNS["type"]) or sections.get("题型定位", "")

    data = {
        "id": question_id,
        "type": question_type.strip(),
        "province": province.strip(),
        "fullScore": full_score,
        "question": question_text,
        "dimensions": dimensions,
        "coreKeywords": split_list(extract_field(ai_text, FIELD_PATTERNS["core_keywords"])),
        "strongKeywords": split_list(extract_field(ai_text, FIELD_PATTERNS["strong_keywords"])),
        "weakKeywords": split_list(extract_field(ai_text, FIELD_PATTERNS["weak_keywords"])),
        "bonusKeywords": split_list(extract_field(ai_text, FIELD_PATTERNS["bonus_keywords"])),
        "penaltyKeywords": split_list(extract_field(ai_text, FIELD_PATTERNS["penalty_keywords"])),
        "scoringCriteria": scoring_criteria,
        "deductionRules": deduction_rules,
        "sourceDocument": source_document,
        "referenceAnswer": reference_answer,
        "tags": build_tags(sections.get("检索标签", "")),
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


def main() -> int:
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

    print(f"导入完成，共生成 {len(parsed_questions)} 道题。")
    print(f"题库 JSON 目录: {QUESTION_OUTPUT_DIR}")
    print(f"高/中/低样本目录: {SAMPLE_OUTPUT_DIR}")
    print(f"导入摘要: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
