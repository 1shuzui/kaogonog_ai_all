"""
这个路由文件提供题库列表、随机题、导入和编辑接口；它只做请求参数、鉴权依赖和服务层转发，业务规则尽量留在 service 里。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
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
    list_qs 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param keyword: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param dimension: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param province: 地区筛选值；只表示地域，不替代考试体系或岗位方向。
    @param position: 岗位/方向筛选值；允许为空表示不限，避免无题库分类被误判为通用模板。
    @param subcategory: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param subcategory2: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param examCategory: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param year: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param current: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param pageSize: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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
    random_qs 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param province: 地区筛选值；只表示地域，不替代考试体系或岗位方向。
    @param count: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param dimension: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param position: 岗位/方向筛选值；允许为空表示不限，避免无题库分类被误判为通用模板。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    ensure_random_question_access(current_user, count)
    return get_random_questions(db, province=province, count=count, dimension=dimension, position=position)


@router.get("/{question_id}")
def get_q(question_id: str, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    """
    get_q 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param question_id: 题目唯一标识；评分、收藏和错题复盘需要用它追溯同一道真实题源。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    ensure_question_read_access(current_user, question_id)
    return get_question(db, question_id)


@router.post("")
def create_q(data: QuestionCreate, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    """
    create_q 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    ensure_admin_access(current_user)
    return create_question(db, data)


@router.put("/{question_id}")
def update_q(question_id: str, data: QuestionUpdate, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    """
    update_q 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param question_id: 题目唯一标识；评分、收藏和错题复盘需要用它追溯同一道真实题源。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    ensure_admin_access(current_user)
    return update_question(db, question_id, data)


@router.delete("/{question_id}")
def delete_q(question_id: str, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    """
    delete_q 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param question_id: 题目唯一标识；评分、收藏和错题复盘需要用它追溯同一道真实题源。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    ensure_admin_access(current_user)
    return delete_question(db, question_id)


@router.post("/import")
async def import_qs(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    """
    import_qs 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param file: 文件对象或路径；脚本和上传流程依赖它保留来源可追溯性。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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
    import_docx 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param file: 文件对象或路径；脚本和上传流程依赖它保留来源可追溯性。
    @param province: 地区筛选值；只表示地域，不替代考试体系或岗位方向。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    ensure_admin_access(current_user)
    content = await file.read()
    return import_from_docx(db, content, file.filename or "", province)


