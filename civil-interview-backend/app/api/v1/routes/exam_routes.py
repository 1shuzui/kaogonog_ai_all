"""
这个路由文件提供考试创建、答题保存和考试完成接口；它只做请求参数、鉴权依赖和服务层转发，业务规则尽量留在 service 里。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.access import ensure_exam_start_access
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, ExamStartRequest
from app.services.exam_service import start_exam, upload_recording, complete_exam

router = APIRouter(prefix="/exam", tags=["exam"])


@router.post("/start")
def exam_start(data: ExamStartRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    exam_start 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    ensure_exam_start_access(current_user, data.questionIds)
    return start_exam(db, data, current_user.username)


@router.post("/{exam_id}/upload")
async def exam_upload(
    exam_id: str,
    questionId: str = Form(...),
    mediaType: str = Form(""),
    source: str = Form("live_recording"),
    recording: UploadFile = File(...),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    exam_upload 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param exam_id: 考试记录标识；用于把多题作答、扣权益和历史结果绑定到同一次练习。
    @param questionId: 题目相关数据；真实题源、题型分类和能力维度需要分开处理。
    @param mediaType: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param source: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param recording: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    content = await recording.read()
    return upload_recording(
        db,
        exam_id,
        questionId,
        recording.filename or "",
        content,
        media_type=mediaType or recording.content_type or "",
        source=source,
    )


@router.post("/{exam_id}/complete")
def exam_complete(exam_id: str, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    exam_complete 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param exam_id: 考试记录标识；用于把多题作答、扣权益和历史结果绑定到同一次练习。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return complete_exam(db, exam_id)
