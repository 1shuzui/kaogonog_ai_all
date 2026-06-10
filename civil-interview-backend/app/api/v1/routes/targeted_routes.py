"""
定向备面路由，提供多层级分类树、真实题库重点分析、管理员发布重点和定向/专项训练抽题。

这里承载了题库分类重构后的核心口径：真实考试体系、地区来源、岗位方向、系统单位、面试形式和题型维度必须分开；
银行、医疗、法检可以是展示入口，但不能抢掉题目的真实来源。重点分析只能来自真实题库统计或管理员发布内容，
没有匹配题库时返回明确空态，不能用其他地区或通用模板伪装。

@param: FastAPI 注入定向选择参数、管理员配置请求、当前用户和数据库 Session。
@return: 返回分类树、重点分析、管理员配置、训练题或生成题结果。
@raises HTTPException: 未登录、非管理员、参数缺失、题库不足或目标配置不存在时返回 HTTP 错误。
"""
import re
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.access import ensure_admin_access, ensure_paid_access
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.entities import Question, TargetedFocusConfig
from app.schemas.common import AuthUser, FocusAnalysisRequest, GenerateQuestionsRequest, TrainingGenerateRequest
from app.core.ai import PROVINCE_NAMES, POSITION_NAMES, DIMENSION_NAMES
from app.services.question_service import (
    _apply_target_filters,
    _question_matches_position,
    _question_meta_from_keywords,
    generate_questions_by_position,
    generate_training_questions,
    sync_curated_question_assets,
)

router = APIRouter(tags=["targeted_training"])

POSITIONS = [
    {"id": "tax", "name": "税务系统"},
    {"id": "customs", "name": "海关系统"},
    {"id": "police", "name": "公安系统"},
    {"id": "court", "name": "法院系统"},
    {"id": "procurate", "name": "检察系统"},
    {"id": "market", "name": "市场监管"},
    {"id": "general", "name": "综合管理"},
    {"id": "township", "name": "乡镇基层"},
    {"id": "finance", "name": "银保监会"},
    {"id": "diplomacy", "name": "外交系统"},
    {"id": "prison", "name": "监狱系统"},
    {"id": "bank", "name": "银行招考"},
    {"id": "medical", "name": "医疗卫生"},
    {"id": "jiangsu_a", "name": "江苏综合管理岗"},
    {"id": "jiangsu_b", "name": "江苏社会科学专技岗"},
    {"id": "jiangsu_c", "name": "江苏自然科学专技岗"},
    {"id": "jiangsu_d", "name": "江苏中小学教师岗"},
    {"id": "jiangsu_e", "name": "江苏医疗卫生岗"},
    {"id": "jiangsu_worker", "name": "江苏工勤技能岗"},
]

TARGETED_PROVINCES = [
    ("beijing", "北京"),
    ("shanghai", "上海"),
    ("guangdong", "广东"),
    ("jiangsu", "江苏"),
    ("zhejiang", "浙江"),
    ("shandong", "山东"),
    ("sichuan", "四川"),
    ("hubei", "湖北"),
    ("hunan", "湖南"),
    ("henan", "河南"),
    ("hebei", "河北"),
    ("fujian", "福建"),
    ("anhui", "安徽"),
    ("liaoning", "辽宁"),
    ("shanxi", "陕西"),
]

JIANGSU_SIDW_CITY_DIRECTIONS = [
    ("nanjing", "南京"),
    ("wuxi", "无锡"),
    ("changzhou", "常州"),
    ("tongzhou", "通州"),
    ("yangzhou", "扬州"),
    ("zhenjiang", "镇江"),
    ("taizhou", "泰州"),
    ("huaian", "淮安"),
    ("xuzhou", "徐州"),
    ("suqian", "宿迁"),
    ("lianyungang", "连云港"),
]

BANK_SYSTEM_DIRECTIONS = [
    ("state_owned", "国有银行"),
    ("joint_stock", "股份制银行"),
    ("city_commercial", "城市商业银行"),
    ("rural_commercial", "农村商业银行"),
]

MEDICAL_JOB_DIRECTIONS = [
    ("doctor", "医师岗"),
    ("nurse", "护理岗"),
    ("technician", "医技岗"),
    ("pharmacist", "药师岗"),
    ("admin", "行政岗"),
]

ANHUI_SIDW_CITY_DIRECTIONS = [
    "合肥", "芜湖", "蚌埠", "淮南", "马鞍山", "淮北", "铜陵", "安庆",
    "黄山", "滁州", "阜阳", "宿州", "六安", "亳州", "池州", "宣城",
]

SHANDONG_SIDW_STANDARD_CITIES = [
    "淄博", "潍坊", "济宁", "泰安", "德州", "聊城", "滨州", "菏泽", "东营", "枣庄",
]

CLERK_SOURCE_PROVINCES = [
    ("hubei", "湖北"),
    ("hunan", "湖南"),
    ("anhui", "安徽"),
    ("shandong", "山东"),
    ("zhejiang", "浙江"),
]

CLERK_STRUCTURED_PROVINCES = [
    ("beijing", "北京"),
    ("shanghai", "上海"),
    ("guangdong", "广东"),
    ("jiangsu", "江苏"),
    ("zhejiang", "浙江"),
    ("shandong", "山东"),
    ("sichuan", "四川"),
    ("hubei", "湖北"),
    ("hunan", "湖南"),
    ("anhui", "安徽"),
    ("fujian", "福建"),
    ("jiangxi", "江西"),
    ("henan", "河南"),
    ("hebei", "河北"),
    ("liaoning", "辽宁"),
    ("heilongjiang", "黑龙江"),
    ("jilin", "吉林"),
    ("shanxi", "陕西"),
    ("guizhou", "贵州"),
    ("yunnan", "云南"),
    ("guangxi", "广西"),
    ("hainan", "海南"),
    ("neimenggu", "内蒙古"),
    ("xinjiang", "新疆"),
    ("ningxia", "宁夏"),
    ("gansu", "甘肃"),
    ("qinghai", "青海"),
]


def _province_region_id(prefix: str, code: str) -> str:
    return f"{prefix}_{code}"


def _province_direction_id(prefix: str, code: str) -> str:
    return f"{prefix}_{code}_all"


def _reserved_admin_hint(label: str) -> str:
    return f"{label}方向已保留；如需开放练习，请在题库管理中补充并确认真实题目。"


def _direction(
    id_: str,
    name: str,
    province: str,
    position: str = "",
    exam_category: str = "",
    exam_subcategory: str = "",
    subcategory: str = "",
    subcategory2: str = "",
    year: str | list = "",
    **meta,
) -> dict:
    payload = {
        "id": id_,
        "name": name,
        "province": province,
        "position": position,
    }
    if exam_category:
        payload["examCategory"] = exam_category
    if exam_subcategory:
        payload["examSubcategory"] = exam_subcategory
    if subcategory:
        payload["subcategory"] = subcategory
    if subcategory2:
        payload["subcategory2"] = subcategory2
    if year:
        payload["year"] = year if isinstance(year, list) else [year]
    payload.update({key: value for key, value in meta.items() if value not in (None, "")})
    return payload


def _region(
    id_: str,
    name: str,
    province: str,
    exam_category: str = "",
    exam_subcategory: str = "",
    directions: list[dict] | None = None,
    subcategory: str = "",
    subcategory2: str = "",
    year: str | list = "",
    **meta,
) -> dict:
    payload = {
        "id": id_,
        "name": name,
        "province": province,
        "directions": directions or [],
    }
    if exam_category:
        payload["examCategory"] = exam_category
    if exam_subcategory:
        payload["examSubcategory"] = exam_subcategory
    if subcategory:
        payload["subcategory"] = subcategory
    if subcategory2:
        payload["subcategory2"] = subcategory2
    if year:
        payload["year"] = year if isinstance(year, list) else [year]
    payload.update({key: value for key, value in meta.items() if value not in (None, "")})
    return payload


TARGETED_POSITION_TREE = [
    {
        "id": "institution",
        "name": "事业单位考试面试",
        "desc": "按真实事业单位套题、地区和岗位方向统计。",
        "children": [
            _region("institution_jiangsu", "江苏省", "jiangsu", "事业单位考试", "江苏省", [
                _direction("js_sydw_provincial", "省属", "jiangsu", "general", "事业单位考试", "江苏省", positionType="省属事业单位", interviewFormat="8+12/15分钟包干", questionCount=3, timingMode="8+12或15分钟包干", questionTypeScope="综合分析/组织/人际/应急/情景模拟/漫画"),
                *[
                    _direction(
                        f"js_sydw_city_{code}",
                        city,
                        "jiangsu",
                        "general",
                        "事业单位考试",
                        "江苏省",
                        subcategory=city,
                        positionType=f"{city}事业单位",
                        interviewFormat="8+12",
                        questionCount=3,
                        prepTime=480,
                        answerTime=720,
                        timingMode="8分钟读题+12分钟答题",
                    )
                    for code, city in JIANGSU_SIDW_CITY_DIRECTIONS
                ],
                _direction("js_sydw_suzhou", "苏州", "jiangsu", "general", "事业单位考试", "江苏省", positionType="苏州事业单位", interviewFormat="15分钟包干/7+8", questionCount=3, timingMode="15分钟包干或7分钟读题+8分钟答题"),
                _direction("js_sydw_yancheng_city", "盐城市 / 市属", "jiangsu", "general", "事业单位考试", "江苏省", positionType="盐城市属事业单位", subcategory="盐城市", interviewFormat="8+12", questionCount=3, prepTime=480, answerTime=720, timingMode="8分钟读题+12分钟答题"),
                _direction("js_sydw_yancheng_dongtai", "盐城市 / 东台", "jiangsu", "general", "事业单位考试", "江苏省", positionType="东台事业单位", subcategory="盐城市", subcategory2="东台", interviewFormat="10+12", questionCount=4, prepTime=600, answerTime=720, timingMode="10分钟读题+12分钟答题"),
                _direction("js_sydw_yancheng_yandu_sheyang", "盐城市 / 盐都、射阳", "jiangsu", "general", "事业单位考试", "江苏省", positionType="盐都/射阳事业单位", subcategory="盐城市", subcategory2="盐都/射阳", interviewFormat="8+12", questionCount=3, prepTime=480, answerTime=720, timingMode="8分钟读题+12分钟答题"),
                _direction("js_sydw_yancheng_xiangshui_binhai", "盐城市 / 响水、滨海", "jiangsu", "general", "事业单位考试", "江苏省", positionType="响水/滨海事业单位", subcategory="盐城市", subcategory2="响水/滨海", interviewFormat="8+8", questionCount=3, prepTime=480, answerTime=480, timingMode="8分钟读题+8分钟答题"),
                _direction("js_sydw_yancheng_funinng_jianhu", "盐城市 / 阜宁、建湖", "jiangsu", "general", "事业单位考试", "江苏省", positionType="阜宁/建湖事业单位", subcategory="盐城市", subcategory2="阜宁/建湖", interviewFormat="15分钟包干", questionCount=3, timingMode="15分钟包干"),
            ]),
            _region("institution_anhui", "安徽省", "anhui", "事业单位考试", "安徽省", [
                _direction("ah_sydw_provincial", "省直", "anhui", "general", "事业单位考试", "安徽省", positionType="省直事业单位", interviewFormat="15-20分钟包干", questionCount="3-4", timingMode="15-20分钟包干", questionTypeScope="综合分析/组织/应急/人际/岗位匹配", notes="各厅局单独命题"),
                *[
                    _direction(
                        f"ah_sydw_city_{index}",
                        city,
                        "anhui",
                        "general",
                        "事业单位考试",
                        "安徽省",
                        subcategory=city,
                        positionType=f"{city}事业单位",
                        interviewFormat="15分钟包干",
                        questionCount=3,
                        timingMode="15分钟包干",
                    )
                    for index, city in enumerate(ANHUI_SIDW_CITY_DIRECTIONS, start=1)
                ],
            ]),
            _region("institution_shandong", "山东省", "shandong", "事业单位考试", "山东省", [
                _direction("sd_sydw_provincial", "省属", "shandong", "general", "事业单位考试", "山东省", positionType="省属事业单位", interviewFormat="15分钟包干", questionCount=3, timingMode="15分钟包干", questionTypeScope="综合分析必考/应急/人际/组织", notes="聚焦山东本土"),
                _direction("sd_sydw_jinan", "济南", "shandong", "general", "事业单位考试", "山东省", subcategory="济南", interviewFormat="7+7", questionCount="2-3", prepTime=420, answerTime=420, timingMode="7分钟读题+7分钟答题"),
                _direction("sd_sydw_qingdao", "青岛", "shandong", "general", "事业单位考试", "山东省", subcategory="青岛", interviewFormat="5+5/15分钟包干", questionCount="2-3", timingMode="5+5或15分钟包干"),
                _direction("sd_sydw_yantai", "烟台", "shandong", "general", "事业单位考试", "山东省", subcategory="烟台", interviewFormat="6+6", questionCount=2, prepTime=360, answerTime=360, timingMode="6分钟读题+6分钟答题"),
                _direction("sd_sydw_weihai", "威海", "shandong", "general", "事业单位考试", "山东省", subcategory="威海", interviewFormat="6+6", questionCount=2, prepTime=360, answerTime=360, timingMode="6分钟读题+6分钟答题"),
                _direction("sd_sydw_linyi", "临沂", "shandong", "general", "事业单位考试", "山东省", subcategory="临沂", interviewFormat="10分钟包干无纸笔", questionCount=2, timingMode="10分钟包干无纸笔"),
                *[
                    _direction(
                        f"sd_sydw_city_{index}",
                        city,
                        "shandong",
                        "general",
                        "事业单位考试",
                        "山东省",
                        subcategory=city,
                        positionType=f"{city}事业单位",
                        interviewFormat="15分钟包干",
                        questionCount=3,
                        timingMode="15分钟包干",
                    )
                    for index, city in enumerate(SHANDONG_SIDW_STANDARD_CITIES, start=1)
                ],
            ]),
        ],
    },
    {
        "id": "provincial_civil",
        "name": "省级公务员考试面试",
        "desc": "按省级公务员考试体系、地区和岗位方向统计。",
        "children": [
            _region("provincial_jiangsu", "江苏省", "jiangsu", "省级公务员考试", "江苏省", positionType="A、B、C三类分别命题", questionCount=4, interviewFormat="A、B、C三类分别命题；10+15模式或20分钟包干", prepTime=600, answerTime=900, timingMode="10分钟读题+15分钟答题或20分钟包干"),
            _region("provincial_guangdong", "广东省", "guangdong", "省级公务员考试", "广东省", positionType="综合类、执法类", questionCount=3, interviewFormat="综合类、执法类一材三题；10+10模式", prepTime=600, answerTime=600, timingMode="10分钟读题+10分钟答题"),
            _region("provincial_shandong", "山东省", "shandong", "省级公务员考试", "山东省", questionCount=3, interviewFormat="统一考试；省直15分钟包干，济南7+7，烟台6+6", timingMode="按地区套题规则切换"),
            _region("provincial_anhui", "安徽省", "anhui", "省级公务员考试", "安徽省", positionType="综合管理类", questionCount=3, interviewFormat="综合管理类；15分钟包干", timingMode="15分钟包干"),
            _region("provincial_henan", "河南省", "henan", "省级公务员考试", "河南省", position="township", positionType="县乡、省直分类", questionCount=4, interviewFormat="县乡、省直分类；20分钟包干", timingMode="20分钟包干"),
            _region("provincial_hubei", "湖北省", "hubei", "省级公务员考试", "湖北省", position="township", positionType="县以上、乡镇、公安三类", questionCount=3, interviewFormat="县以上、乡镇、公安三类；县乡15分钟，省直18分钟", timingMode="县乡15分钟包干或省直18分钟包干"),
            _region("provincial_hebei", "河北省", "hebei", "省级公务员考试", "河北省", questionCount=3, interviewFormat="统一考试，含演讲、漫画特色；10分钟包干", timingMode="10分钟包干", questionTypeScope="结构化、演讲、漫画"),
            _region("provincial_hunan", "湖南省", "hunan", "省级公务员考试", "湖南省", positionType="通用岗、乡镇岗、监狱系统、税务系统补录", interviewFormat="按湖南省考真实套题规则组织"),
        ],
    },
    {
        "id": "national_civil",
        "name": "国家公务员考试",
        "desc": "按国考系统和直属机构方向统计。",
        "children": [
            _region("national_party", "中央党群机关", "national", "国家公务员考试", "中央党群机关", [
                _direction("gk_zhongban", "中央办公厅", "national", "", "国家公务员考试", "中央党群机关"),
                _direction("gk_xuanchuan", "中央宣传部", "national", "", "国家公务员考试", "中央党群机关"),
                _direction("gk_wangxin", "中央网信办", "national", "", "国家公务员考试", "中央党群机关"),
                _direction("gk_zhengfa", "中央政法委", "national", "", "国家公务员考试", "中央党群机关"),
                _direction("gk_zhongjiwei", "中纪委", "national", "", "国家公务员考试", "中央党群机关", questionCount=3),
            ]),
            _region("national_administration", "中央国家行政机关", "national", "国家公务员考试", "中央国家行政机关", [
                _direction("gk_waijiao", "外交部", "national", "diplomacy", "国家公务员考试", "中央国家行政机关", subcategory="外交部", interviewFormat="结构化+追问"),
                _direction("gk_fagai", "国家发改委", "national", "", "国家公务员考试", "中央国家行政机关", subcategory="国家发改委", questionCount=5),
                _direction("gk_jiaoyu", "教育部", "national", "", "国家公务员考试", "中央国家行政机关", subcategory="教育部"),
                _direction("gk_gongan", "公安部", "national", "police", "国家公务员考试", "中央国家行政机关", subcategory="公安部"),
                _direction("gk_caizheng", "财政部", "national", "", "国家公务员考试", "中央国家行政机关", subcategory="财政部"),
                _direction("gk_shenji", "审计署", "national", "", "国家公务员考试", "中央国家行政机关", subcategory="审计署", questionCount=3),
                _direction("gk_keji", "科技部", "national", "", "国家公务员考试", "中央国家行政机关", subcategory="科技部", interviewFormat="含面谈"),
            ]),
            _region("national_direct", "省级以下直属机构", "national", "国家公务员考试", "省级以下直属机构", [
                _direction("gk_tax", "税务系统", "national", "tax", "国家公务员考试", "省级以下直属机构", subcategory="税务系统", interviewFormat="结构化小组"),
                _direction("gk_customs", "海关系统", "national", "customs", "国家公务员考试", "省级以下直属机构", subcategory="海关系统", interviewFormat="结构化小组"),
                _direction("gk_maritime", "海事局", "national", "", "国家公务员考试", "省级以下直属机构", subcategory="海事局", interviewFormat="结构化"),
                _direction("gk_railway_police", "铁路公安", "national", "police", "国家公务员考试", "省级以下直属机构", subcategory="铁路公安", interviewFormat="结构化+视频"),
                _direction("gk_statistics", "统计系统", "national", "", "国家公务员考试", "省级以下直属机构", subcategory="统计系统", interviewFormat="结构化"),
                _direction("gk_financial_regulation", "金融监管系统", "national", "finance", "国家公务员考试", "省级以下直属机构", subcategory="金融监管系统", interviewFormat="含专业题"),
                _direction("gk_meteorology", "气象局", "national", "", "国家公务员考试", "省级以下直属机构", subcategory="气象局", interviewFormat="结构化"),
            ]),
            _region("national_public_institution", "参公事业单位", "national", "国家公务员考试", "参公事业单位", [
                _direction("gk_nbs", "国家统计局", "national", "", "国家公务员考试", "参公事业单位", subcategory="国家统计局", interviewFormat="结构化"),
                _direction("gk_cma", "中国气象局", "national", "", "国家公务员考试", "参公事业单位", subcategory="中国气象局", interviewFormat="结构化"),
                _direction("gk_csrc", "证监会", "national", "finance", "国家公务员考试", "参公事业单位", subcategory="证监会", interviewFormat="含专业题"),
                _direction("gk_cbirc", "银保监会", "national", "finance", "国家公务员考试", "参公事业单位", subcategory="银保监会", interviewFormat="含专业题"),
                _direction("gk_cnipa", "国家知识产权局", "national", "", "国家公务员考试", "参公事业单位", subcategory="国家知识产权局"),
            ]),
            _region("national_common", "通用试题类", "national", "国家公务员考试", "通用试题类", [
                _direction("gk_common_public", "参公事业单位", "national", "", "国家公务员考试", "通用试题类", positionType="参公事业单位"),
                _direction("gk_common_unified", "使用全国统一命制题本", "national", "", "国家公务员考试", "通用试题类", interviewFormat="全国统一命制题本"),
                _direction("gk_common_daily_sets", "每天2套题 每套5道题", "national", "", "国家公务员考试", "通用试题类", questionCount=5, suiteCountPerDay=2),
                _direction("gk_common_25min", "总时间25分钟", "national", "", "国家公务员考试", "通用试题类", answerTime=1500, timingMode="25分钟包干"),
            ]),
        ],
    },
    {
        "id": "medical_portal",
        "name": "医疗卫生面试",
        "desc": "按已确认题源展示，题目真实主分类仍保留原考试体系。",
        "children": [
            _region("medical_beijing", "北京市", "beijing", directions=[
                _direction("medical_bj_doctor", "医师岗", "beijing", "medical", positionType="医师岗", interviewFormat="结构化+专业答辩+病例分析"),
                _direction("medical_bj_nurse", "护理岗", "beijing", "medical", positionType="护理岗", interviewFormat="结构化+实操考核"),
                _direction("medical_bj_technician", "医技岗", "beijing", "medical", positionType="医技岗", interviewFormat="结构化+设备操作"),
                _direction("medical_bj_pharmacist", "药师岗", "beijing", "medical", positionType="药师岗", interviewFormat="结构化+药学知识"),
                _direction("medical_bj_admin", "行政岗", "beijing", "medical", positionType="行政岗", interviewFormat="结构化面试"),
            ]),
            *[
                _region(f"medical_{code}", province, code, directions=[
                    _direction(f"medical_{code}_doctor", "医师岗", code, "medical", positionType="医师岗"),
                    _direction(f"medical_{code}_nurse", "护理岗", code, "medical", positionType="护理岗"),
                    _direction(f"medical_{code}_technician", "医技岗", code, "medical", positionType="医技岗"),
                    _direction(f"medical_{code}_pharmacist", "药师岗", code, "medical", positionType="药师岗"),
                    _direction(f"medical_{code}_admin", "行政岗", code, "medical", positionType="行政岗"),
                ])
                for code, province in [("shanghai", "上海市"), ("guangdong", "广东省"), ("jiangsu", "江苏省"), ("sichuan", "四川省")]
            ],
            _region("medical_sichuan_partial", "四川省 / 部分地区", "sichuan", directions=[
                *[
                    _direction(f"medical_sc_partial_{code}", name, "sichuan", "medical", positionType=name, interviewFormat="医疗背景结构化")
                    for code, name in MEDICAL_JOB_DIRECTIONS
                ],
            ]),
            _region("medical_e_class", "E类联考省份", "all", directions=[
                *[
                    _direction(f"medical_e_class_{code}", name, "all", "medical", positionType=name, interviewFormat="E类联考分岗考核")
                    for code, name in MEDICAL_JOB_DIRECTIONS
                ],
            ]),
        ],
    },
    {
        "id": "bank_portal",
        "name": "银行招考面试",
        "desc": "按银行招考面试方向统计。",
        "children": [
            *[
                _region(f"bank_{code}", province, code, directions=[
                    *[
                        _direction(
                            f"bank_{code}_{system_code}",
                            system_name,
                            code,
                            "bank",
                            subcategory=system_name,
                        )
                        for system_code, system_name in BANK_SYSTEM_DIRECTIONS
                    ]
                ], adminHint=_reserved_admin_hint(f"{province}银行招考"))
                for code, province in [
                    ("beijing", "北京市"), ("shanghai", "上海市"), ("guangdong", "广东省"), ("jiangsu", "江苏省"),
                    ("zhejiang", "浙江省"), ("shandong", "山东省"), ("henan", "河南省"), ("sichuan", "四川省"),
                    ("anhui", "安徽省"), ("fujian", "福建省"), ("gansu", "甘肃省"),
                    ("guangxi", "广西壮族自治区"), ("guizhou", "贵州省"), ("hainan", "海南省"),
                    ("hebei", "河北省"), ("heilongjiang", "黑龙江省"), ("hubei", "湖北省"),
                    ("hunan", "湖南省"), ("jilin", "吉林省"), ("jiangxi", "江西省"),
                    ("liaoning", "辽宁省"), ("neimenggu", "内蒙古自治区"), ("ningxia", "宁夏回族自治区"),
                    ("qinghai", "青海省"), ("shaanxi", "陕西省"), ("shanxi", "山西省"),
                    ("tianjin", "天津市"), ("xinjiang", "新疆维吾尔自治区"), ("xizang", "西藏自治区"),
                    ("yunnan", "云南省"), ("chongqing", "重庆市"),
                ]
            ],
        ],
    },
    {
        "id": "clerk_portal",
        "name": "法检书记员面试",
        "desc": "按已确认题源展示，监狱/税务等系统不会归入此类。",
        "levelLabels": {"region": "岗位方向", "direction": "地区/来源"},
        "children": [
            *[
                _region(
                    f"clerk_{role_code}",
                    role_name,
                    "all",
                    directions=[
                        *[
                            _direction(
                                f"clerk_{role_code}_{province_code}_professional",
                                province_name,
                                province_code,
                                position,
                                positionType=role_name,
                                interviewFormat="结构化+专业知识",
                                timingMode="15分钟包干",
                                prepTime=0,
                                answerTime=900,
                                questionCount="2-3",
                            )
                            for province_code, province_name in CLERK_SOURCE_PROVINCES
                        ],
                        *[
                            _direction(
                                f"clerk_{role_code}_{province_code}_structured",
                                province_name,
                                province_code,
                                position,
                                positionType=role_name,
                                interviewFormat="结构化面试",
                                timingMode="15分钟包干",
                                prepTime=0,
                                answerTime=900,
                                questionCount="2-3",
                            )
                            for province_code, province_name in CLERK_STRUCTURED_PROVINCES
                            if province_code not in {item[0] for item in CLERK_SOURCE_PROVINCES}
                        ],
                    ],
                    adminHint=_reserved_admin_hint(role_name),
                )
                for role_code, role_name, position in [
                    ("court", "法院书记员", "court"),
                    ("procurate", "检察院书记员", "procurate"),
                ]
            ],
        ],
    },
]


def _ensure_reserved_province_entries() -> None:
    institution = next((item for item in TARGETED_POSITION_TREE if item.get("id") == "institution"), None)
    provincial = next((item for item in TARGETED_POSITION_TREE if item.get("id") == "provincial_civil"), None)
    if not institution or not provincial:
        return

    institution_children = institution.setdefault("children", [])
    provincial_children = provincial.setdefault("children", [])
    existing_institution = {item.get("province") for item in institution_children}
    existing_provincial = {item.get("province") for item in provincial_children}

    for code, short_name in TARGETED_PROVINCES:
        province_name = f"{short_name}省" if short_name not in {"北京", "上海"} else f"{short_name}市"
        if code not in existing_institution:
            institution_children.append({
                "id": _province_region_id("institution", code),
                "name": province_name,
                "province": code,
                "examCategory": "事业单位考试",
                "examSubcategory": province_name,
                "adminHint": _reserved_admin_hint(f"{province_name}事业单位"),
                "directions": [
                    {
                        "id": _province_direction_id("sydw", code),
                        "name": f"{short_name}事业单位",
                        "province": code,
                        "position": "",
                        "examCategory": "事业单位考试",
                        "examSubcategory": province_name,
                    }
                ],
            })
        if code not in existing_provincial:
            provincial_children.append({
                "id": _province_region_id("provincial", code),
                "name": province_name,
                "province": code,
                "examCategory": "省级公务员考试",
                "examSubcategory": province_name,
                "adminHint": _reserved_admin_hint(f"{province_name}省考"),
                "directions": [],
            })


_ensure_reserved_province_entries()

FOCUS_MIN_QUESTION_COUNT = 1
ABILITY_DIMENSION_LABELS = {
    "analysis": "综合分析",
    "practical": "实务落地",
    "emergency": "应急应变",
    "legal": "行政思维",
    "logic": "逻辑结构",
    "expression": "语言表达",
}
ABILITY_DIMENSION_KEYS_BY_LABEL = {label: key for key, label in ABILITY_DIMENSION_LABELS.items()}
ABILITY_DIMENSION_ALIASES = {
    "法治思维": "行政思维",
    "职业认知": "行政思维",
    "岗位认知": "行政思维",
    "组织管理": "实务落地",
    "人际沟通": "逻辑结构",
    "人际关系": "逻辑结构",
    "情景模拟": "语言表达",
    "现场模拟": "语言表达",
}
QUESTION_TYPE_LABELS = {"综合分析", "组织管理", "应急应变", "人际沟通", "情景模拟", "岗位认知"}
QUESTION_TYPE_ALIASES = {
    "analysis": "综合分析",
    "practical": "组织管理",
    "organization": "组织管理",
    "emergency": "应急应变",
    "adaptability": "应急应变",
    "logic": "人际沟通",
    "interpersonal": "人际沟通",
    "expression": "情景模拟",
    "simulation": "情景模拟",
    "legal": "岗位认知",
    "career": "岗位认知",
    "实务落地": "组织管理",
    "逻辑结构": "人际沟通",
    "语言表达": "情景模拟",
    "现场模拟": "情景模拟",
    "行政思维": "岗位认知",
    "法治思维": "岗位认知",
    "职业认知": "岗位认知",
    "人际关系": "人际沟通",
}
QUESTION_TYPE_KEYWORDS = (
    ("组织管理", ("组织", "计划", "调研", "宣传", "活动", "接待", "推进", "落实", "协调")),
    ("应急应变", ("应急", "突发", "危机", "舆情", "处置", "投诉", "冲突")),
    ("人际沟通", ("人际", "沟通", "劝导", "同事", "领导", "群众", "关系")),
    ("情景模拟", ("情景模拟", "现场模拟", "模拟", "演讲", "发言", "串词", "宣讲")),
    ("岗位认知", ("职业认知", "岗位认知", "自我认知", "报考动机", "价值观", "岗位匹配")),
    ("综合分析", ("综合分析", "社会现象", "政策理解", "观点", "漫画", "寓言", "名言", "现象", "分析")),
)
FOCUS_TARGET_FIELDS = (
    "targetCode",
    "province",
    "position",
    "examCategory",
    "examSubcategory",
    "subcategory",
    "subcategory2",
    "year",
    "targetName",
    "interviewFormat",
    "timingMode",
    "questionCount",
    "prepTime",
    "answerTime",
)


def parse_timing_format(text: str) -> tuple[int | None, int | None]:
    """
    解析真实套题时间模式。

    定向分类里会出现“8+12”“15分钟包干”“5+5/15分钟包干”等中文时间表达；这里把可确定的读题/答题时间转为秒，原文不明确时保持兜底，避免端侧自行猜。

    @param timing: 原始时间模式文本。
    @return: (prepTime, answerTime) 秒数元组；无法拆分时返回包干或默认值。
    @raises: 不主动抛业务异常；无法识别时按兜底规则返回。
    """
    if not text:
        return None, None
    text = text.strip()
    # "8+12" → prep=480s, answer=720s
    m = re.fullmatch(r"(\d+)\+(\d+)", text)
    if m:
        return int(m.group(1)) * 60, int(m.group(2)) * 60
    # "15分钟包干" / "20分钟作答" → prep=0, answer=N*60
    m = re.search(r"(\d+)\s*分钟\s*(?:包干|作答|答题)", text)
    if m:
        return 0, int(m.group(1)) * 60
    return None, None


def _dimension_label(code: str) -> str:
    return ABILITY_DIMENSION_LABELS.get(code, code or "综合分析")


def _normalize_ability_dimension(value: str | None) -> tuple[str, str]:
    text = str(value or "").strip()
    if not text:
        return "analysis", "综合分析"
    if text in ABILITY_DIMENSION_LABELS:
        return text, ABILITY_DIMENSION_LABELS[text]
    normalized = ABILITY_DIMENSION_ALIASES.get(text, text)
    if normalized in ABILITY_DIMENSION_KEYS_BY_LABEL:
        return ABILITY_DIMENSION_KEYS_BY_LABEL[normalized], normalized
    return "analysis", "综合分析"


def _normalize_question_type_label(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return "综合分析"
    text = text.split("·", 1)[0].strip()
    return QUESTION_TYPE_ALIASES.get(text, text if text in QUESTION_TYPE_LABELS else "综合分析")


def _infer_question_type_label(text: str) -> str:
    haystack = str(text or "")
    for label, keywords in QUESTION_TYPE_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return label
    return "综合分析"


def _priority_by_rank(index: int) -> str:
    return "high" if index == 0 else "medium" if index <= 2 else "low"


def _frequency_by_rank(index: int, count: int) -> str:
    if index == 0 or count >= 5:
        return "高"
    if count >= 2:
        return "中"
    return "低"


def _meta_list(meta: dict, key: str) -> list[str]:
    value = meta.get(key)
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.replace("，", "、").replace(",", "、").split("、") if item.strip()]
    return []


def _question_type_label(question: Question, meta: dict) -> str:
    raw_label = (
        str(meta.get("questionTypeCategory") or "").strip()
        or str(meta.get("questionType") or "").split("·", 1)[0].strip()
    )
    return _normalize_question_type_label(raw_label) if raw_label else _infer_question_type_label(question.stem)


def _target_filters_from_request(data: FocusAnalysisRequest | GenerateQuestionsRequest) -> dict:
    filters = {}
    for key in ("examCategory", "examSubcategory", "subcategory", "subcategory2"):
        value = str(getattr(data, key, "") or "").strip()
        if value:
            filters[key] = value
    # 兼容小程序端 city/system → subcategory 映射
    if not filters.get("subcategory"):
        for alt in ("system", "city"):
            value = str(getattr(data, alt, "") or "").strip()
            if value:
                filters["subcategory"] = value
                break
    year = getattr(data, "year", "")
    if year:
        if isinstance(year, list):
            year = [str(y).strip() for y in year if str(y).strip()]
        elif isinstance(year, str):
            year = [y.strip() for y in year.replace(",", "、").replace("，", ",").split(",") if y.strip()]
        if year:
            filters["year"] = year
    return filters


def _target_name(data: FocusAnalysisRequest | GenerateQuestionsRequest) -> str:
    return str(getattr(data, "targetName", "") or "").strip() or POSITION_NAMES.get(data.position, data.position)


def _focus_request_payload(data: FocusAnalysisRequest | dict) -> dict:
    if isinstance(data, dict):
        source = data
        get_value = source.get
    else:
        get_value = lambda key, default="": getattr(data, key, default)

    payload = {}
    for field in FOCUS_TARGET_FIELDS:
        value = get_value(field, "")
        if value is None:
            continue
        text = str(value).strip()
        if text:
            payload[field] = text
    payload["province"] = payload.get("province") or "national"
    payload["position"] = payload.get("position") or ""

    # Auto-fill prepTime/answerTime from timingMode/interviewFormat if not explicitly set
    prep_time = int(payload.get("prepTime", 0) or 0)
    answer_time = int(payload.get("answerTime", 0) or 0)
    if prep_time == 0 and answer_time == 0:
        for field in ("timingMode", "interviewFormat"):
            parsed_prep, parsed_answer = parse_timing_format(payload.get(field, ""))
            if parsed_prep is not None and parsed_answer is not None:
                payload["prepTime"] = str(parsed_prep)
                payload["answerTime"] = str(parsed_answer)
                break
    return payload


def _focus_target_key(data: FocusAnalysisRequest | dict) -> str:
    payload = _focus_request_payload(data)
    target_code = payload.get("targetCode")
    if target_code:
        return f"code:{target_code}"
    parts = [
        payload.get("province", ""),
        payload.get("position", ""),
        payload.get("examCategory", ""),
        payload.get("examSubcategory", ""),
        payload.get("subcategory", ""),
        payload.get("subcategory2", ""),
    ]
    return "fields:" + "|".join(str(item).strip() for item in parts)


def _focus_data_from_payload(payload: dict) -> FocusAnalysisRequest:
    return FocusAnalysisRequest(**_focus_request_payload(payload))


def _clamp_int(value, default: int = 0, min_value: int = 0, max_value: int = 100) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    return max(min_value, min(max_value, number))


def _string_list(value) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        raw_items = value.replace("，", "\n").replace(",", "\n").splitlines()
    else:
        raw_items = []
    return [str(item).strip() for item in raw_items if str(item).strip()]


def _sanitize_focus_payload(raw: dict | None) -> dict:
    raw = raw if isinstance(raw, dict) else {}

    core_focus = []
    for item in raw.get("coreFocus") or []:
        if not isinstance(item, dict):
            continue
        dimension_key, name = _normalize_ability_dimension(item.get("dimensionKey") or item.get("name"))
        if not name:
            continue
        core_focus.append({
            "dimensionKey": dimension_key,
            "name": name,
            "weight": _clamp_int(item.get("weight"), default=20, min_value=0, max_value=100),
            "desc": str(item.get("desc") or "").strip(),
            "questionCount": _clamp_int(item.get("questionCount"), default=0, min_value=0, max_value=100000),
        })

    high_freq_types = []
    for item in raw.get("highFreqTypes") or []:
        if not isinstance(item, dict):
            continue
        type_name = _normalize_question_type_label(item.get("questionTypeKey") or item.get("type"))
        if not type_name:
            continue
        high_freq_types.append({
            "questionTypeKey": type_name,
            "type": type_name,
            "frequency": str(item.get("frequency") or "中").strip(),
            "example": str(item.get("example") or "").strip(),
            "questionCount": _clamp_int(item.get("questionCount"), default=0, min_value=0, max_value=100000),
        })

    focus_areas = []
    for index, item in enumerate(core_focus):
        focus_areas.append({
            "type": item.get("dimensionKey") or item["name"],
            "dimensionKey": item.get("dimensionKey", ""),
            "label": item["name"],
            "description": item["desc"],
            "priority": _priority_by_rank(index),
            "questionCount": item.get("questionCount", 0),
        })

    question_count = _clamp_int(raw.get("questionCount"), default=0, min_value=0, max_value=1000000)
    return {
        "focusAreas": focus_areas,
        "coreFocus": core_focus,
        "highFreqTypes": high_freq_types,
        "hotTopics": _string_list(raw.get("hotTopics")),
        "strategy": _string_list(raw.get("strategy")),
        "questionCount": question_count,
        "dataSource": "admin_config",
        "isFallback": False,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


def _merge_focus_config_response(data: FocusAnalysisRequest, config: TargetedFocusConfig) -> dict:
    payload = deepcopy(config.payload if isinstance(config.payload, dict) else {})
    payload.update({
        "province": data.province,
        "provinceName": PROVINCE_NAMES.get(data.province, data.province),
        "position": data.position,
        "positionName": _target_name(data),
        "targetCode": str(getattr(data, "targetCode", "") or config.target_code or "").strip(),
        "targetName": str(getattr(data, "targetName", "") or config.target_name or _target_name(data)).strip(),
        "dataSource": "admin_config",
        "isFallback": False,
        "updatedAt": config.updated_at.isoformat() if config.updated_at else payload.get("updatedAt"),
    })
    return payload


def _serialize_focus_config(config: TargetedFocusConfig | None) -> dict | None:
    if not config:
        return None
    return {
        "id": config.id,
        "targetKey": config.target_key,
        "targetCode": config.target_code,
        "targetName": config.target_name,
        "province": config.province,
        "position": config.position,
        "payload": config.payload or {},
        "enabled": bool(config.enabled),
        "updatedBy": config.updated_by,
        "createdAt": config.created_at.isoformat() if config.created_at else "",
        "updatedAt": config.updated_at.isoformat() if config.updated_at else "",
    }


def _load_focus_config(db: Session, data: FocusAnalysisRequest | dict) -> TargetedFocusConfig | None:
    return db.query(TargetedFocusConfig).filter(TargetedFocusConfig.target_key == _focus_target_key(data)).first()


def _collect_focus_questions(db: Session, data: FocusAnalysisRequest) -> list[Question]:
    sync_curated_question_assets(db)
    normalized_province = str(data.province or "").strip()
    query = db.query(Question)
    if normalized_province and normalized_province not in {"all", "national"}:
        query = query.filter(Question.province == normalized_province)
    elif normalized_province == "national":
        query = query.filter(Question.province == "national")
    rows = query.limit(1500).all()
    if data.position:
        rows = [question for question in rows if _question_matches_position(question, data.position)]
    rows = _apply_target_filters(rows, _target_filters_from_request(data))
    return rows


def _build_empty_focus_response(data: FocusAnalysisRequest) -> dict:
    province_name = PROVINCE_NAMES.get(data.province, data.province)
    position_name = _target_name(data)
    message = "暂无足够题库数据，请选择已有真实题库的考试方向后再试。"
    return {
        "province": data.province,
        "provinceName": province_name,
        "position": data.position,
        "positionName": position_name,
        "focusAreas": [],
        "coreFocus": [],
        "highFreqTypes": [],
        "hotTopics": [],
        "strategy": [message],
        "questionCount": 0,
        "dataSource": "question_bank",
        "isFallback": True,
        "emptyMessage": message,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


def _build_real_focus_response(data: FocusAnalysisRequest, questions: list[Question]) -> dict:
    province_name = PROVINCE_NAMES.get(data.province, data.province)
    position_name = _target_name(data)
    dimension_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    topic_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()

    for question in questions:
        meta = _question_meta_from_keywords(question.keywords)
        dimension_key, _ = _normalize_ability_dimension(question.dimension or "analysis")
        dimension_counter[dimension_key] += 1
        type_counter[_question_type_label(question, meta)] += 1
        source = str(meta.get("sourceDocument") or meta.get("sourceLabel") or "").strip()
        if source:
            source_counter[source] += 1
        for key in ("tags", "coreKeywords", "strongKeywords"):
            for term in _meta_list(meta, key):
                if len(term) <= 2 or term in {province_name, position_name, "全真模拟", "事业单位", "省考"}:
                    continue
                topic_counter[term] += 1

    total = max(1, len(questions))
    core_focus = []
    for index, (dimension, count) in enumerate(dimension_counter.most_common(4)):
        weight = max(10, round(count / total * 100))
        name = _dimension_label(dimension)
        core_focus.append({
            "dimensionKey": dimension,
            "name": name,
            "weight": weight,
            "desc": f"基于当前题库中 {count} 道匹配题统计，{province_name}{position_name}方向较常考{name}能力。",
            "questionCount": count,
        })

    high_freq_types = []
    for index, (type_name, count) in enumerate(type_counter.most_common(5)):
        high_freq_types.append({
            "questionTypeKey": type_name,
            "type": type_name,
            "frequency": _frequency_by_rank(index, count),
            "example": f"当前匹配题库中出现 {count} 次，建议结合真实套题反复练习。",
            "questionCount": count,
        })

    hot_topics = [topic for topic, _ in topic_counter.most_common(10)]
    if not hot_topics:
        hot_topics = [name for name, _ in type_counter.most_common(5)]

    focus_areas = [
        {
            "type": dimension,
            "dimensionKey": dimension,
            "label": _dimension_label(dimension),
            "description": item["desc"],
            "priority": _priority_by_rank(index),
            "questionCount": item["questionCount"],
        }
        for index, (dimension, item) in enumerate(zip([key for key, _ in dimension_counter.most_common(4)], core_focus))
    ]

    top_dimension = core_focus[0]["name"] if core_focus else "综合分析"
    top_type = high_freq_types[0]["type"] if high_freq_types else "真实套题"
    strategy = [
        f"优先复盘{province_name}{position_name}方向的{top_type}题，先按真实套题题序训练，再按题型拆解。",
        f"围绕{top_dimension}建立答题框架，作答时区分考试体系、岗位场景和题型维度。",
        "练习后对照采分点检查关键词、岗位贴合度和举措落地性，避免只背通用模板。",
    ]
    if source_counter:
        strategy.append(f"当前分析主要来自 {len(source_counter)} 个题库来源；新增真题后可刷新分析。")

    return {
        "province": data.province,
        "provinceName": province_name,
        "position": data.position,
        "positionName": position_name,
        "focusAreas": focus_areas,
        "coreFocus": core_focus,
        "highFreqTypes": high_freq_types,
        "hotTopics": hot_topics,
        "strategy": strategy,
        "questionCount": len(questions),
        "dataSource": "question_bank",
        "isFallback": False,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/positions")
def get_positions():
    """
    返回定向备面分类树。

    分类树体现真实考试体系和特色入口的展示关系，PC、小程序和管理员页都应复用这里，避免各端出现不同层级。

    @param: 无；分类树由后端静态结构和题库元数据共同维护。
    @return: 考试体系、动态层级标签、地区/来源、方向和时间模式信息。
    @raises: 不主动抛业务异常。
    """
    return {
        "tree": TARGETED_POSITION_TREE,
        "legacy": POSITIONS,
    }


@router.post("/targeted/focus")
async def get_focus(data: FocusAnalysisRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    生成或读取定向备面重点分析。

    普通用户优先看到管理员已发布内容；没有发布内容时只使用真实题库统计，题库不足则返回空态，不能套用其他地区模板。

    @param body: 考试体系、地区/来源、方向和可选时间模式。
    @param db: 请求级数据库会话。
    @return: 重点分析结构，包含能力重点、题型高频、热点和策略。
    @raises HTTPException: 请求体非法或服务端分析失败时抛出。
    """
    ensure_paid_access(current_user, detail="定向备考需付费开通后使用")
    config = _load_focus_config(db, data)
    if config and config.enabled:
        return _merge_focus_config_response(data, config)
    questions = _collect_focus_questions(db, data)
    if len(questions) < FOCUS_MIN_QUESTION_COUNT:
        return _build_empty_focus_response(data)
    return _build_real_focus_response(data, questions)


@router.get("/targeted/focus/admin")
async def get_focus_admin_config(
    targetCode: str = "",
    province: str = "national",
    position: str = "",
    examCategory: str = "",
    examSubcategory: str = "",
    subcategory: str = "",
    subcategory2: str = "",
    year: str = "",
    targetName: str = "",
    interviewFormat: str = "",
    timingMode: str = "",
    questionCount: str = "",
    prepTime: int | None = None,
    answerTime: int | None = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    管理员读取重点分析配置的路由。

    管理员页面需要同时看到自动分析、已发布内容和可编辑字段，因此这里按目标 key 聚合配置，而不是让前端自己拼。

    @param targetCode: 可选目标编码。
    @param current_user: 当前管理员用户。
    @param db: 请求级数据库会话。
    @return: 当前目标的自动分析、发布状态和编辑内容。
    @raises HTTPException: 非管理员访问时抛出 403。
    """
    ensure_admin_access(current_user)
    target_payload = {
        "targetCode": targetCode,
        "province": province,
        "position": position,
        "examCategory": examCategory,
        "examSubcategory": examSubcategory,
        "subcategory": subcategory,
        "subcategory2": subcategory2,
        "year": year,
        "targetName": targetName,
        "interviewFormat": interviewFormat,
        "timingMode": timingMode,
        "questionCount": questionCount,
        "prepTime": prepTime,
        "answerTime": answerTime,
    }
    data = _focus_data_from_payload(target_payload)
    config = _load_focus_config(db, target_payload)
    questions = _collect_focus_questions(db, data)
    auto_payload = (
        _build_real_focus_response(data, questions)
        if len(questions) >= FOCUS_MIN_QUESTION_COUNT
        else _build_empty_focus_response(data)
    )
    current_payload = _merge_focus_config_response(data, config) if config and config.enabled else auto_payload
    return {
        "targetKey": _focus_target_key(target_payload),
        "target": _focus_request_payload(target_payload),
        "config": _serialize_focus_config(config),
        "auto": auto_payload,
        "current": current_payload,
    }


@router.put("/targeted/focus/admin")
async def save_focus_admin_config(
    body: dict,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    管理员保存并可发布重点分析配置。

    发布内容会优先覆盖自动统计，适合题库不足或需要人工修正文案的场景；保存时仍保留目标分类字段，方便停用后回到自动分析。

    @param body: 管理员编辑后的重点分析内容和发布状态。
    @param current_user: 当前管理员用户。
    @param db: 请求级数据库会话。
    @return: 保存后的配置。
    @raises HTTPException: 非管理员、字段非法或数据库写入失败时抛出。
    """
    ensure_admin_access(current_user)
    target_payload = body.get("target") if isinstance(body.get("target"), dict) else body
    target_payload = _focus_request_payload(target_payload if isinstance(target_payload, dict) else {})
    if not target_payload.get("targetCode") and not target_payload.get("examCategory") and not target_payload.get("portalTag"):
        raise HTTPException(status_code=400, detail="缺少定向入口信息")

    payload = _sanitize_focus_payload(body.get("payload") if isinstance(body.get("payload"), dict) else body.get("focus"))
    target_key = _focus_target_key(target_payload)
    config = db.query(TargetedFocusConfig).filter(TargetedFocusConfig.target_key == target_key).first()
    if not config:
        config = TargetedFocusConfig(target_key=target_key)
        db.add(config)

    config.target_code = target_payload.get("targetCode", "")
    config.target_name = target_payload.get("targetName", "")
    config.province = target_payload.get("province", "")
    config.position = target_payload.get("position", "")
    config.payload = payload
    config.enabled = bool(body.get("enabled", True))
    config.updated_by = current_user.username
    db.commit()
    db.refresh(config)
    return {
        "targetKey": target_key,
        "config": _serialize_focus_config(config),
        "current": _merge_focus_config_response(_focus_data_from_payload(target_payload), config),
    }


@router.post("/targeted/focus/admin/disable")
async def disable_focus_admin_config(
    body: dict,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    管理员停用已发布重点分析配置。

    停用不会删除历史配置，只让普通用户重新走自动统计或空态，便于管理员回滚误发布。

    @param body: 目标分类定位字段。
    @param current_user: 当前管理员用户。
    @param db: 请求级数据库会话。
    @return: 停用结果。
    @raises HTTPException: 非管理员或目标不存在时抛出。
    """
    ensure_admin_access(current_user)
    target_payload = body.get("target") if isinstance(body.get("target"), dict) else body
    target_payload = _focus_request_payload(target_payload if isinstance(target_payload, dict) else {})
    config = _load_focus_config(db, target_payload)
    if not config:
        return {"targetKey": _focus_target_key(target_payload), "config": None, "disabled": True}
    config.enabled = False
    config.updated_by = current_user.username
    db.commit()
    db.refresh(config)
    return {"targetKey": config.target_key, "config": _serialize_focus_config(config), "disabled": True}


@router.post("/targeted/generate")
async def targeted_generate(data: GenerateQuestionsRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    定向备面生成题目路由。

    生成逻辑应按真实分类筛选题库；方向为“不限”时放宽到考试体系和地区/来源，不能跨省或套用其他考试体系。

    @param body: 定向生成条件。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 生成的练习题目和考试上下文。
    @raises HTTPException: 未登录、权益不足或无可用题目时抛出。
    """
    ensure_paid_access(current_user, detail="定向备考需付费开通后使用")
    questions = await generate_questions_by_position(
        db,
        data.province,
        data.position,
        data.count,
        "local",
        _target_filters_from_request(data),
    )
    return {
        "questions": questions,
        "province": data.province,
        "position": data.position,
        "sourceMode": data.sourceMode,
    }


@router.post("/training/generate")
async def training_generate(data: TrainingGenerateRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    专项训练生成题目路由。

    专项训练使用题型分类，不能和考生能力维度混用；路由层只转发参数，筛题和兜底由生成逻辑处理。

    @param body: 题型、地区和数量等训练条件。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 生成的专项训练题目。
    @raises HTTPException: 未登录、权益不足或无可用题目时抛出。
    """
    ensure_paid_access(current_user, detail="专项训练需付费开通后使用")
    target_filters = _target_filters_from_request(data)
    questions = await generate_training_questions(
        db,
        data.dimension,
        data.count,
        data.sourceMode,
        province=data.province or "national",
        target_filters=target_filters if target_filters else None,
    )
    return {
        "questions": questions,
        "dimension": data.dimension,
        "dimensionName": DIMENSION_NAMES.get(data.dimension, data.dimension),
        "sourceMode": data.sourceMode,
    }
