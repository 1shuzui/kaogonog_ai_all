"""纯题目范围匹配；列表、定向抽题与个人表现分析共用同一口径。

只读取传入题目的字段，不访问数据库、题库同步、评分配置或模型。
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.services.question_labels import PROVINCE_NAMES
from app.services.question_scope import matches_scope

if TYPE_CHECKING:
    from app.models.entities import Question

POSITION_ALIASES = {
    "tax": ("税务", "税费", "纳税", "税收"),
    "customs": ("海关",),
    "police": ("公安", "特警", "交警", "民警", "警民"),
    "court": ("法院", "法官"),
    "procurate": ("检察", "检察院"),
    "market": ("市场监管", "市监"),
    "general": ("综合管理", "综合岗", "通用岗", "遴选"),
    "township": ("乡镇", "基层", "村", "社区"),
    "finance": ("银保监", "金融监管"),
    "diplomacy": ("外交",),
    "prison": ("监狱", "狱警"),
    "jiangsu_a": ("A类", "A 类"),
    "jiangsu_b": ("B类", "B 类"),
    "jiangsu_c": ("C类", "C 类"),
    "jiangsu_d": ("D类", "D 类"),
    "jiangsu_e": ("E类", "E 类"),
    "jiangsu_worker": ("工勤技能岗", "工勤", "技能保障", "服务规范"),
    "bank": ("银行", "农商行", "城商行", "柜面", "客户经理"),
    "medical": ("医疗", "卫生", "医师", "护理", "药师", "医技"),
}



def question_meta(keywords: dict | None) -> dict:
    if not isinstance(keywords, dict):
        return {}
    meta = keywords.get('_meta')
    return meta if isinstance(meta, dict) else {}



def normalize_year_values(value) -> list[str]:
    if isinstance(value, list):
        candidates = value
    elif isinstance(value, str):
        candidates = re.split('[、，,；;/\\s]+', value)
    elif value in (None, ''):
        candidates = []
    else:
        candidates = [value]
    years: list[str] = []
    for item in candidates:
        match = re.search('(?:19|20)\\d{2}', str(item or ''))
        if match and match.group(0) not in years:
            years.append(match.group(0))
    return years



def infer_year_values(*values) -> list[str]:
    years: list[str] = []
    for value in values:
        for year in normalize_year_values(value):
            if year not in years:
                years.append(year)
    return years



def question_years(meta: dict | None) -> list[str]:
    if not isinstance(meta, dict):
        return []
    date_years = normalize_year_values(meta.get('examDate'))
    if date_years:
        return date_years
    explicit_years = normalize_year_values(meta.get('year'))
    if explicit_years:
        return explicit_years
    for group in ((meta.get('examDate'),), (meta.get('suiteName'), meta.get('sourceTitleRaw')), (meta.get('sourceQuestionId'),), (meta.get('sourceDocument'), meta.get('originFile'))):
        inferred_years = infer_year_values(*group)
        if inferred_years:
            return inferred_years
    return []



PROVINCE_CODE_BY_NAME = {name: code for code, name in PROVINCE_NAMES.items()}



PROVINCE_ALIASES = {
    "national": "national",
    "全国": "national",
    "通用": "national",
    "全国通用": "national",
    "全国省": "national",
    "国家": "national",
    "国家公务员考试": "national",
    "国考": "national",
    "beijing": "beijing",
    "北京": "beijing",
    "guangdong": "guangdong",
    "广东": "guangdong",
    "zhejiang": "zhejiang",
    "浙江": "zhejiang",
    "sichuan": "sichuan",
    "四川": "sichuan",
    "jiangsu": "jiangsu",
    "江苏": "jiangsu",
    "anhui": "anhui",
    "安徽": "anhui",
    "安徽消防": "anhui",
    "henan": "henan",
    "河南": "henan",
    "shandong": "shandong",
    "山东": "shandong",
    "hubei": "hubei",
    "湖北": "hubei",
    "hunan": "hunan",
    "湖南": "hunan",
    "liaoning": "liaoning",
    "辽宁": "liaoning",
    "shanxi": "shanxi",
    "陕西": "shanxi",
}



def normalize_province(value: str | None) -> str:
    normalized = str(value or '').strip()
    if not normalized:
        return 'national'
    if normalized in PROVINCE_CODE_BY_NAME:
        return PROVINCE_CODE_BY_NAME[normalized]
    lowered = normalized.lower()
    return PROVINCE_ALIASES.get(lowered, PROVINCE_ALIASES.get(normalized, lowered or 'national'))



def question_matches_position(question: Question, position: str) -> bool:
    if not position:
        return True
    meta = question_meta(question.keywords)
    position_tags = meta.get('positionTags') if isinstance(meta.get('positionTags'), list) else []
    portal_tags = meta.get('portalTags') if isinstance(meta.get('portalTags'), list) else []
    display_portals = meta.get('displayPortals') if isinstance(meta.get('displayPortals'), list) else []
    if position in position_tags:
        return True
    exam_category = str(meta.get('examCategory') or '')
    if position == 'medical' and ('medical' in position_tags or '医疗卫生面试' in portal_tags or '医疗卫生面试' in display_portals or ('医疗卫生面试' in exam_category)):
        return True
    if position == 'bank' and '银行招考面试' in exam_category:
        return True
    if position in {'court', 'procurate'} and '法检书记员面试' in exam_category:
        return True
    if position.startswith('jiangsu_') and any((str(tag).startswith('jiangsu_') for tag in position_tags)):
        return False
    if position.startswith('jiangsu_'):
        return False
    haystack = ' '.join([question.stem, meta.get('sourceDocument', ''), meta.get('suiteName', ''), meta.get('examCategory', ''), meta.get('examSubcategory', ''), meta.get('subcategory', ''), meta.get('subcategory2', ''), meta.get('jobLevel', ''), ' '.join(meta.get('tags', []) if isinstance(meta.get('tags'), list) else []), meta.get('questionType', ''), meta.get('questionTypeCategory', '')])
    return any((alias in haystack for alias in POSITION_ALIASES.get(position, ())))



def question_matches_target_filters(question: Question, target_filters: dict | None=None) -> bool:
    if not target_filters:
        return True
    meta = question_meta(question.keywords)

    def clean(value) -> str:
        return str(value or '').strip()

    def values_match(a: str, b: str) -> bool:
        """Loose match: exact equality or one contains the other for category aliases."""
        if not a or not b:
            return True
        if a == b:
            return True
        return a in b or b in a
    for field in ('examCategory', 'examSubcategory', 'subcategory', 'subcategory2'):
        expected = clean(target_filters.get(field))
        actual = clean(meta.get(field))
        if expected and actual and (not values_match(expected, actual)):
            return False
    portal_expected = clean(target_filters.get('portalTag') or target_filters.get('displayPortal'))
    if portal_expected:
        portal_values = [*(meta.get('portalTags') if isinstance(meta.get('portalTags'), list) else []), *(meta.get('displayPortals') if isinstance(meta.get('displayPortals'), list) else [])]
        if not any((values_match(portal_expected, clean(value)) for value in portal_values)):
            return False
    position_expected_values: list[str] = []
    for key in ('positionType', 'positionTag', 'positionTags'):
        raw_value = target_filters.get(key)
        if isinstance(raw_value, list):
            position_expected_values.extend((clean(value) for value in raw_value))
        elif raw_value:
            position_expected_values.extend((clean(value) for value in re.split('[、，,；;/\\s]+', clean(raw_value))))
    position_expected_values = [value for value in position_expected_values if value]
    if position_expected_values:
        position_values = [clean(meta.get('positionType')), *(meta.get('positionTags') if isinstance(meta.get('positionTags'), list) else []), clean(meta.get('position'))]
        if not any((values_match(expected, clean(value)) for expected in position_expected_values for value in position_values if value)):
            return False
    year_filter = target_filters.get('year')
    if year_filter:
        year_values = set((str(y).strip() for y in (year_filter if isinstance(year_filter, list) else [year_filter]) if str(y).strip()))
        if year_values:
            meta_years = set(question_years(meta))
            if meta_years and (not year_values & meta_years):
                return False
    return True



def apply_target_filters(questions: list[Question], target_filters: dict | None=None) -> list[Question]:
    if not target_filters:
        return questions
    return [question for question in questions if question_matches_target_filters(question, target_filters)]



def apply_position_filter(questions: list[Question], position: str) -> list[Question]:
    if not position:
        return questions
    return [question for question in questions if question_matches_position(question, position)]



def filter_bank_rows(rows, *, position='', subcategory='', subcategory2='', examCategory='', year='', **scope):
    """列表与随机练习共用同一套元数据过滤，不能无题时放宽条件。"""
    rows = [q for q in rows if matches_scope(question_meta(q.keywords), scope)]
    if position:
        rows = apply_position_filter(rows, position)
    for key, value in (('subcategory', subcategory), ('subcategory2', subcategory2), ('examCategory', examCategory)):
        if value:
            rows = [q for q in rows if question_meta(q.keywords).get(key) == value]
    if year:
        years = set(normalize_year_values(year))
        rows = [q for q in rows if years & set(question_years(question_meta(q.keywords)))]
    return rows
