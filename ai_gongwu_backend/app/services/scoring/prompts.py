"""评分与违规前置检测 Prompt 构造模块。"""

import json

from app.models.schemas import EvidenceExtractionPayload, QuestionDefinition

VIOLATION_CHECK_SYSTEM_MESSAGE = (
    "你是一个严格但重视上下文的违规内容检测引擎。"
    "你的任务是先判断考生作答是否包含需要直接终止评分的违规表达。"
    "你必须结合整句、整段和表达立场判断，不能因为单个词面命中就直接判违规。"
    "只输出合法 JSON。"
)

EVIDENCE_EXTRACTION_SYSTEM_MESSAGE = (
    "你是一个严格的证据抽取引擎。"
    "你的任务只是抽取可核验的证据，不负责打分。"
    "只输出合法 JSON。"
)

EVIDENCE_SCORING_SYSTEM_MESSAGE = (
    "你是一个严格的结构化评分引擎。"
    "你只能基于给定证据包打分，不能自行补充证据。"
    "只输出合法 JSON。"
)


def _format_score(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"


def _build_local_focus_text(question: QuestionDefinition) -> tuple[str, str]:
    """按当前题目动态生成“本土化/岗位化”提示，避免河南模板污染其他题。"""

    province_text = f"{question.province}本土化表达" if question.province else "本土化表达"
    haystack = " ".join(
        [
            question.type,
            question.question,
            *question.tags,
            *question.scoringCriteria,
            *question.deductionRules,
        ]
    )
    if "省直机关" in haystack:
        fit_text = "省直机关岗位适配度"
    elif any(marker in haystack for marker in ("岗位", "履职", "税务", "监狱", "公安", "遴选")):
        fit_text = "岗位适配度"
    elif any(marker in haystack for marker in ("活动", "组织", "社区", "沟通", "现场模拟")):
        fit_text = "场景适配度"
    else:
        fit_text = "题目要求适配度"
    return province_text, fit_text


def _is_interpersonal_question(question: QuestionDefinition) -> bool:
    """判断当前题目是否属于需要单独加判档提醒的人际题。"""

    haystack = " ".join(
        [
            question.type,
            question.question,
            *question.tags,
            *question.scoringCriteria,
            *question.deductionRules,
        ]
    )
    return any(
        marker in haystack
        for marker in (
            "人际沟通",
            "同事关系",
            "群众矛盾",
            "心理疏导",
            "亲情沟通",
            "矛盾化解",
            "沟通劝说",
            "怎么劝说",
            "如何劝说",
            "怎么劝导",
            "如何劝导",
            "怎么沟通",
            "如何沟通",
            "怎么说服",
            "如何说服",
            "怎么安抚",
            "如何安抚",
        )
    )


def _build_interpersonal_scoring_guardrail(
    question: QuestionDefinition,
    fit_focus: str,
) -> str:
    """给人际题补一层“基本合格”判档锚点，避免中档样本被直接打零。"""

    if not _is_interpersonal_question(question):
        return ""

    return f"""
# 人际题额外判档提醒
1. 如果原文已经做到“态度得体、愿意先听或先稳情绪”“把矛盾点、事实原因或误会来源讲清楚”“给出后续处理、帮带或跟进动作”中的大部分，即使表达不够出彩，也应至少判入“基本合格”附近，而不是直接打成 0 分。
2. 这类题缺少亮点、本土化或政策化表达时，可以从 {fit_focus} 或语言维度降档，但不要把已经完成的沟通主线整题清零。
3. 只有当答案明显跑题、只剩空泛安慰、没有解释矛盾点、也没有任何处理动作时，才考虑压到极低分。
""".strip()


def _build_score_band_anchors(question: QuestionDefinition) -> str:
    """优先使用题库 scoreBands 渲染分档锚点，避免提示词和题目配置脱节。"""

    if question.scoreBands:
        lines = []
        for index, band in enumerate(question.scoreBands, start=1):
            lines.append(
                f"{index}. {_format_score(band.min_score)}-{_format_score(band.max_score)} 分："
                f"{band.label}。{band.description or '按该档特征综合判断。'}"
            )
        return "\n".join(lines)

    full_score = question.fullScore
    return "\n".join(
        [
            f"1. {_format_score(full_score * 0.8)}-{_format_score(full_score)} 分：高分档。内容完整、结构清楚、贴题度高。",
            f"2. {_format_score(full_score * 0.65)}-{_format_score(full_score * 0.8 - 0.1)} 分：中高档。主要内容较完整，但深度或适配度略弱。",
            f"3. {_format_score(full_score * 0.45)}-{_format_score(full_score * 0.65 - 0.1)} 分：基本合格。能答到主干，但结构、细节或表达存在明显短板。",
            f"4. 0-{_format_score(full_score * 0.45 - 0.1)} 分：明显偏弱。内容单薄、逻辑松散或有效措施较少。",
        ]
    )


def build_violation_check_prompt(
    question: QuestionDefinition,
    answer_text: str,
    visual_observation: str | None = None,
) -> str:
    """评分前的违规检测提示词。"""

    visual_block = visual_observation or "未提供视频流，请不要把视觉观察作为单独触发违规拦截的依据。"

    prompt = f"""
# 角色
你现在是“评分前违规专项审查员”，不是评分官。
你的唯一任务是判断【考生作答原文】里是否存在需要直接终止评分的明确违规表达。

# 审查原则
1. 必须结合整句、整段和上下文语义判断，不能因为单个高风险词面命中就直接判违规。
2. 只有当考生原文明确表达、明确主张、明显 endorse 违规内容时，才判定为违规。
3. 批判问题、转述错误观点、举反例说明风险、讲解答题套路、复盘教学语言，都不等于考生本人在支持违规内容。
4. visual_observation 只能作为辅助背景，不能单独作为终止评分的唯一依据。

# 需要终止评分的情形
只要明确命中下面任一类，is_violation 就返回 true，后续不再评分：
1. 明确辱骂、侮辱、恶意攻击、人身攻击。
2. 明确政治红线表达、极端不当政治表态。
3. 明确鼓吹行贿受贿、走后门、权钱交易等廉政红线内容。
4. 其他非常明显、足以直接终止评分的不当内容。

# 不要误判
下面这些默认不算违规，除非上下文另有明确恶意或明确 endorse：
1. 正常表达中的负面词，例如“废物利用”“反对废物式管理”等，不算违规。
2. 否定性廉政表达，例如“不能行贿受贿”“不能走后门”，不算违规。
3. 教学分析、答题复盘、示范讲解语言，例如“这类演讲题不用一开始铺得太满”，不算违规。
4. 批判错误观点或举反例，例如“有人觉得塞红包更快，但这种想法必须坚决反对”，不算违规。
5. 正常批评工作问题、表达压力、指出管理短板，不算违规。

# 题目信息
题目 ID: {question.id}
题目类型: {question.type}
题干: {question.question}

# 视觉观察
{visual_block}

# 考生作答原文
===== 开始 =====
{answer_text}
===== 结束 =====

# 输出要求
1. 只输出 JSON。
2. 如果不违规，matched_terms 返回空数组，reason 使用类似“未发现需要终止评分的明确违规表达”。
3. 如果违规，matched_terms 只保留原文中最能证明违规的 1-5 个短语或短句片段，不要只返回单个高风险字词。
4. category 只能使用：abuse / political_red_line / integrity_red_line / other。

# JSON Schema
{{
  "is_violation": false,
  "category": "",
  "matched_terms": [],
  "reason": "未发现需要终止评分的明确违规表达"
}}
"""
    return prompt.strip()


def build_evidence_extraction_prompt(
    question: QuestionDefinition,
    answer_text: str,
    visual_observation: str | None = None,
) -> str:
    """第一阶段：从原文中抽取可核验的证据。"""

    dimensions = [{item.name: item.score} for item in question.dimensions]
    visual_block = visual_observation or "未提供视频流，无法评估仪态信息。"

    prompt = f"""
# 角色
你现在不是评分官，而是“证据抽取员”。你只能从考生原文中抽取逐字可核验的证据。

# 任务规则
1. 只能抽取在【考生作答原文】中逐字存在的内容。
2. 不要给分，不要写抽象结论，不要写“未结合本地省情/岗位要求”这类缺失型判断。
3. 证据文本 evidence_text 必须是原文中的直接片段。
4. claim 只描述这条证据说明了什么，但不能脱离 evidence_text 自由发挥。
5. 如果是明显口语表达，也可以抽取为语言类证据。
6. 视觉观察不是内容评分证据来源，不得作为 evidence_text。

# 题目信息
题目 ID: {question.id}
题目类型: {question.type}
题干: {question.question}
评分维度:
{json.dumps(dimensions, ensure_ascii=False, indent=2)}

# 视觉观察
{visual_block}

# 考生作答原文
===== 开始 =====
{answer_text}
===== 结束 =====

# 输出要求
1. 只输出 JSON。
2. evidence_items 最多输出 10 条，优先保留最关键的内容和语言证据。
3. dimension_hint 必须从已有评分维度中选择，拿不准时可填空字符串。
4. stance 只能是 positive / negative / language / neutral。
5. evidence_type 固定为 quote。

# JSON Schema
{{
  "evidence_items": [
    {{
      "id": "",
      "dimension_hint": "现象解读",
      "claim": "考生指出该做法存在一刀切问题",
      "evidence_text": "最关键的就是“一刀切”太不合理了",
      "evidence_type": "quote",
      "stance": "negative"
    }}
  ],
  "coverage_notes": ["证据覆盖到积极面、问题面、措施面"],
  "summary": "原文中主要证据概览"
}}
"""
    return prompt.strip()


def build_evidence_scoring_prompt(
    question: QuestionDefinition,
    evidence_packet: EvidenceExtractionPayload,
) -> str:
    """第二阶段：只基于证据包打分。"""

    dimensions = [{item.name: item.score} for item in question.dimensions]
    province_focus, fit_focus = _build_local_focus_text(question)
    band_anchors = _build_score_band_anchors(question)
    interpersonal_guardrail = _build_interpersonal_scoring_guardrail(question, fit_focus)
    local_reason_example = (
        f"未结合{question.province}本地实际展开分析" if question.province else "未体现题目要求的本地实际"
    )

    prompt = f"""
# 角色
你现在是“证据约束评分官”。你只能基于给定证据包打分。

# 核心规则
1. 禁止引用证据包以外的新事实。
2. deduction_items 和 bonus_items 的每一条都必须绑定 evidence_ids，且 evidence_ids 不能为空。
3. 若某项扣分来自“缺失”，也必须引用证据包中的 absence 类证据。
4. 不允许输出 deduction_details / bonus_details 自由文本，只输出结构化 items。
5. total_score 必须等于 dimension_scores 之和。

# 评分顺序
1. 先看“通用内容质量”，判断考生是否识别积极意义、问题本质、危害根源、改进措施。
2. 再看“{province_focus} + {fit_focus}”，判断是否体现本土化、岗位化、政策化表达。
3. 如果答案通用分析完整，但缺少{province_focus}或{fit_focus}，应判为“中上档降档”，不能直接打入低分区。
4. 语言口语化会拉低“语言逻辑与岗位适配”，但不能吞掉已经被证据支持的分析分和措施分。

{interpersonal_guardrail}

# 分档锚点
{band_anchors}

# 题目信息
题目 ID: {question.id}
题目类型: {question.type}
题干: {question.question}
满分: {question.fullScore}
评分维度:
{json.dumps(dimensions, ensure_ascii=False, indent=2)}
评分细则:
{json.dumps(question.scoringCriteria, ensure_ascii=False, indent=2)}
扣分规则:
{json.dumps(question.deductionRules, ensure_ascii=False, indent=2)}

# 证据包
{json.dumps(evidence_packet.model_dump(mode="json"), ensure_ascii=False, indent=2)}

# 输出要求
1. 只输出 JSON。
2. dimension_scores 的维度名称必须与题库完全一致。
3. 若证据不足，宁可保守给分，不要脑补。
4. 抽象理由必须绑定 evidence_ids。

# JSON Schema
{{
  "dimension_scores": {{
    "维度名称": 0
  }},
  "deduction_items": [
    {{
      "reason": "{local_reason_example}",
      "dimension": "现象解读",
      "evidence_ids": ["A1"]
    }}
  ],
  "bonus_items": [
    {{
      "reason": "准确识别形式主义和一刀切风险",
      "dimension": "危害根源分析",
      "evidence_ids": ["E2"]
    }}
  ],
  "rationale": "整体评分理由",
  "total_score": 0
}}
"""
    return prompt.strip()
