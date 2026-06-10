"""
法律文档路由，为 PC 和小程序提供用户协议、隐私政策、儿童隐私保护和第三方 SDK 说明。

这些文档需要在登录、手机号授权、录音录像、虚拟支付等审核场景里稳定展示，因此用后端统一出口。
本路由不要求登录，避免用户在阅读协议前就被要求授权。

@param: 无；当前接口不需要查询参数或鉴权依赖。
@return: 返回最新法律文档集合、版本号和更新时间。
@raises HTTPException: 当前实现不主动抛业务错误；未来数据库化后缺文档时应返回明确错误。
"""
from fastapi import APIRouter

from app.services.legal_service import get_legal_documents

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get("/documents")
def legal_documents():
    """
    返回服务协议和隐私政策文档。

    审核材料和端侧协议弹窗需要稳定文本来源，所以协议内容由 legal_service 统一维护，路由不拼接文案。

    @param: 无。
    @return: 当前版本的协议、隐私和相关说明文本。
    @raises: 不主动抛业务异常。
    """
    return get_legal_documents()
