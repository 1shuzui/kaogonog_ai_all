"""
评分路由注册测试防止前端仍在调用的入口被重构漏挂。

评分链路曾经同时存在普通评分、带媒体评分和历史查询入口；路由拆分时如果只改 service 不检查 router，
PC 或小程序会表现为“提交评分失败”，但本地函数测试仍可能通过。

@param: 无；直接读取 v1 router 的已注册路径。
@return: 无直接返回；断言通过表示评分入口仍暴露给前端。
@raises ImportError: API router 或评分路由模块导入失败时会失败。
"""
import unittest

from app.api.v1 import api_router


class ScoringRouteRegistrationTestCase(unittest.TestCase):
    """
    评分路由注册用例集合，确认评分相关入口没有在 router 重构时漏挂。

    PC 和小程序提交评分、查看结果、查询 ASR 状态都依赖这些路径；service 存在但 router 漏挂时，
    页面会直接失败，所以这里单独守路由层。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 测试用例类。
    @raises AssertionError: 任一前端依赖评分路由缺失时由断言报告。
    """
    def test_scoring_routes_are_registered(self):
        """
        评分、转写、结果和法律文档入口必须注册到 v1 router。

        法律文档入口放在同一断言里，是因为登录/评分页可能在提交前同步拉取协议内容。

        @param: 无；直接读取 `api_router.routes`。
        @return: None；必需路径全部存在时通过。
        @raises AssertionError: 路由漏挂或路径被误改时失败。
        """
        route_paths = {route.path for route in api_router.routes}

        self.assertIn("/scoring/asr-status", route_paths)
        self.assertIn("/scoring/transcribe", route_paths)
        self.assertIn("/scoring/evaluate", route_paths)
        self.assertIn("/scoring/result/{exam_id}/{question_id}", route_paths)
        self.assertIn("/legal/documents", route_paths)


if __name__ == "__main__":
    unittest.main()
