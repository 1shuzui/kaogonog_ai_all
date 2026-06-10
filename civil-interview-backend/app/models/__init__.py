"""
ORM 模型包入口。

当前模型集中在 entities.py，覆盖用户、题库、练习、评分、订单、订阅、反馈和审计流水。包入口只做少量常用模型导出，不触发建表或迁移，让 database_setup.py 和运行时会话各自控制生命周期。

@param: 无；这是包初始化文件，不接收业务请求。
@return: 导出常用 SQLAlchemy Base 和实体类，方便测试或脚本按统一路径引用。
@raises ImportError: Python 包路径或 SQLAlchemy 依赖异常时会在导入阶段失败。
"""
from app.db.session import Base
from app.models.entities import User, Question, Exam, ExamAnswer, HistoryRecord

__all__ = ["Base", "User", "Question", "Exam", "ExamAnswer", "HistoryRecord"]
