"""
Pydantic 协议模型包入口。

schemas 用来固定请求和响应形状，保护 PC、小程序和管理端的兼容性。这里不放转换逻辑，避免接口字段规则散落在路由、服务和前端之间。

@param: 无；这是包初始化文件，不接收业务请求。
@return: 无直接返回；提供协议模型的稳定导入路径。
@raises ImportError: Python 包路径或 Pydantic 依赖异常时会在导入阶段失败。
"""
