"""定向考试目录及展示范围；预留方向不代表题库已有真题。"""

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
            _region("medical_shandong", "山东省", "shandong", "事业单位考试", "山东省", directions=[
                _direction(
                    f"medical_shandong_{code}",
                    name,
                    "shandong",
                    "medical",
                    "事业单位考试",
                    "山东省",
                    portalTag="医疗卫生面试",
                    displayPortal="医疗卫生面试",
                    positionType=name,
                    interviewFormat="医疗卫生结构化面试",
                )
                for code, name in MEDICAL_JOB_DIRECTIONS
            ]),
            _region("medical_general", "通用医疗卫生题库", "national", "事业单位考试", "通用医疗卫生题库", directions=[
                _direction(
                    f"medical_general_{code}",
                    name,
                    "national",
                    "medical",
                    "事业单位考试",
                    "通用医疗卫生题库",
                    portalTag="医疗卫生面试",
                    displayPortal="医疗卫生面试",
                    positionType=name,
                    interviewFormat="医疗卫生结构化面试",
                )
                for code, name in MEDICAL_JOB_DIRECTIONS
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


def _apply_exam_units():
    for category in TARGETED_POSITION_TREE:
        track = {"institution": "institution", "medical_portal": "medical"}.get(category["id"])
        if not track:
            continue
        category["examTrack"] = track
        if track == "medical":
            category["name"] = "医疗系统考试"
            category["portalTag"] = "医疗卫生面试"
        for region in category.get("children", []):
            region["examTrack"] = track
            for direction in region.get("directions", []):
                direction["examTrack"] = track
                if direction.get("id", "").startswith("js_sydw_"):
                    if direction["id"] == "js_sydw_provincial":
                        direction["areaLevel"] = "provincial"
                    else:
                        direction["city"] = direction["name"].split(" / ")[0].removesuffix("市")
                        if direction.get("subcategory2"):
                            direction["district"] = direction.pop("subcategory2")
                    for field in ("position", "positionType", "subcategory"):
                        direction.pop(field, None)
                elif direction.get("city"):
                    for field in ("position", "positionType", "subcategory"):
                        direction.pop(field, None)
                if track == "medical":
                    direction["portalTag"] = "医疗卫生面试"


_apply_exam_units()
