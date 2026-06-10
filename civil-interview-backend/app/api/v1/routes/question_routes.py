"""
题库路由，提供题目列表、随机题、详情、后台增删改、Excel/Word 导入和题库管理入口。

这里的重点是把访问权限和题库服务分开：普通用户只能读取可练习内容，管理员才能新增、编辑、删除和导入。
分类字段由服务层维护，路由层不要用省份、岗位名或题型关键词临时拼规则，否则 PC、小程序和管理员页面会出现不同口径。

@param: FastAPI 注入查询筛选、请求体、上传文件、当前用户和数据库 Session。
@return: 返回题目列表、随机题集合、单题详情、导入结果或后台编辑结果。
@raises HTTPException: 未登录、无权益、非管理员、题目不存在或导入解析失败时返回 HTTP 错误。
"""
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.access import (
    ensure_admin_access,
    ensure_paid_access,
    ensure_question_read_access,
    ensure_random_question_access,
)
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, QuestionCreate, QuestionUpdate
from app.services.question_service import (
    list_questions, get_random_questions, get_question,
    create_question, update_question, delete_question,
    import_questions, import_from_docx, generate_training_questions,
)

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("")
def list_qs(
    keyword: str = "", dimension: str = "", province: str = "", position: str = "",
    subcategory: str = "", subcategory2: str = "", examCategory: str = "", year: str = "",
    current: int = 1, pageSize: int = 10,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    查询题库列表，并在路由层先确认用户具备扩展题库访问权。

    题库筛选字段历史上经历过“省份/岗位/题型”到“考试体系/真实来源/题型维度”的迁移，
    这里保持旧查询参数兼容，把真正的分类解释交给服务层，避免前端和小程序各写一套临时规则。

    @param keyword: 题干、标签或来源的搜索词。
    @param dimension: 旧版题型筛选参数，服务层会兼容到当前题型维度。
    @param province: 地区筛选值，只表示地域。
    @param position: 岗位或方向筛选值，空值表示不限。
    @param subcategory: 旧版二级分类筛选。
    @param subcategory2: 旧版三级分类筛选。
    @param examCategory: 真实考试体系筛选。
    @param year: 年份筛选。
    @param current: 页码。
    @param pageSize: 每页条数。
    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @return: 分页题目列表。
    @raises HTTPException: 未登录、权益不足或服务层查询失败时抛出。
    """
    ensure_paid_access(current_user, detail="开通后可查看推荐题目与扩展题目")
    return list_questions(
        db, keyword=keyword, dimension=dimension, province=province,
        position=position, subcategory=subcategory, subcategory2=subcategory2,
        examCategory=examCategory, year=year,
        current=current, page_size=pageSize,
    )


@router.get("/random")
def random_qs(
    province: str = "national", count: int = 5, dimension: str = "", position: str = "",
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    按筛选条件抽取随机练习题。

    随机题会直接消耗用户可练习能力，所以路由层先按题量做权益校验；服务层只负责抽题，
    不需要理解试用、套餐或审核期访问策略。

    @param province: 地区筛选值，只表示地域。
    @param count: 请求抽取题量。
    @param dimension: 题型维度筛选。
    @param position: 岗位或方向筛选值，空值表示不限。
    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @return: 随机题集合。
    @raises HTTPException: 权益不足、题量越界或服务层无题时抛出。
    """
    ensure_random_question_access(current_user, count)
    return get_random_questions(db, province=province, count=count, dimension=dimension, position=position)


@router.get("/{question_id}")
def get_q(question_id: str, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    """
    返回单题详情。

    单题详情会被收藏、错题、评分复盘和后台编辑共用，所以先用统一访问策略判断是否可读，
    再让服务层返回完整题目结构。

    @param question_id: 题目唯一标识，用于追溯真实题源。
    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @return: 单题详情。
    @raises HTTPException: 用户无权读取或题目不存在时抛出。
    """
    ensure_question_read_access(current_user, question_id)
    return get_question(db, question_id)


@router.post("")
def create_q(data: QuestionCreate, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    """
    管理员新增题目。

    后台新增会影响真实题库统计、全真模拟和评分采分点稳定性，因此只在路由层开放给管理员；
    具体字段归一化、采分点提示和分类纠偏由题库服务承担。

    @param data: 题目创建请求。
    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @return: 新建后的题目详情。
    @raises HTTPException: 非管理员、字段不合法或保存失败时抛出。
    """
    ensure_admin_access(current_user)
    return create_question(db, data)


@router.put("/{question_id}")
def update_q(question_id: str, data: QuestionUpdate, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    """
    管理员编辑题目。

    题目元数据已经被多端筛选和重点分析依赖，路由层只做管理员鉴权，不在这里临时修分类，
    以免绕过服务层的导入纠偏和低置信度标记。

    @param question_id: 需要编辑的题目 ID。
    @param data: 题目更新请求。
    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @return: 更新后的题目详情。
    @raises HTTPException: 非管理员、题目不存在或字段不合法时抛出。
    """
    ensure_admin_access(current_user)
    return update_question(db, question_id, data)


@router.delete("/{question_id}")
def delete_q(question_id: str, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    """
    管理员删除题目。

    删除题目会让历史答题仍指向旧题号，因此此处仅保留后台能力入口；是否后续改为软删除，
    应在题库服务和历史复盘策略里统一处理。

    @param question_id: 需要删除的题目 ID。
    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @return: 删除结果。
    @raises HTTPException: 非管理员、题目不存在或删除失败时抛出。
    """
    ensure_admin_access(current_user)
    return delete_question(db, question_id)


@router.post("/import")
async def import_qs(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    """
    管理员通过表格批量导入题目。

    上传内容先完整读入再交给服务层解析，是为了让服务层能根据文件名保留来源、统计纠偏结果并统一落库。
    路由层不尝试理解 Excel 字段，避免导入模板调整后出现两套解析逻辑。

    @param file: 上传的题库表格文件。
    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @return: 导入数量、错误项和分类纠偏摘要。
    @raises HTTPException: 非管理员、文件解析失败或导入失败时抛出。
    """
    ensure_admin_access(current_user)
    content = await file.read()
    return import_questions(db, content, file.filename or "")


@router.post("/import/docx")
async def import_docx(
    file: UploadFile = File(...),
    province: str = "national",
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    管理员从 Word 真题文档导入题目。

    `province` 只作为旧导入入口的兜底地区，真实分类仍以套题标题、章节和题目元数据优先。
    这样能避免江苏事业单位、安徽省考、湖南监狱等题源被单纯文件名或岗位关键词带偏。

    @param file: 上传的 Word 题库文件。
    @param province: 旧模板传入的默认地区兜底。
    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @return: 导入数量、解析失败项和分类复核提示。
    @raises HTTPException: 非管理员、文件解析失败或导入失败时抛出。
    """
    ensure_admin_access(current_user)
    content = await file.read()
    return import_from_docx(db, content, file.filename or "", province)
