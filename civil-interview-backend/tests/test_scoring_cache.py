"""
这个测试文件守住 `test_scoring_cache` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import redis_cache
from app.db.session import Base
from app.models.entities import Question
from app.services import scoring_service

TEST_REDIS_URL = "redis://127.0.0.1:6379/15"


class ScoringCacheTestCase(unittest.IsolatedAsyncioTestCase):
    """
    ScoringCacheTestCase 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    async def asyncSetUp(self):
        """
        asyncSetUp 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        self.original_url = redis_cache.settings.redis_url
        redis_cache.settings.redis_url = TEST_REDIS_URL
        await redis_cache.close_redis()
        self.redis_client = await redis_cache.get_redis()
        if self.redis_client is None:
            self.fail("Redis client was not created for scoring integration test")
        await self.redis_client.ping()
        for key in await self.redis_client.keys("llm:score:score_cache_q1:*"):
            await self.redis_client.delete(key)

        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(
            Question(
                id="score_cache_q1",
                stem="请谈谈如何做好群众沟通工作。",
                dimension="practical",
                province="jiangsu",
                scoring_points=[{"content": "主动沟通协调", "score": 10}],
                keywords={
                    "scoring": ["沟通", "协调"],
                    "deducting": [],
                    "bonus": [],
                    "_meta": {"coreKeywords": ["群众"], "strongKeywords": ["落实"]},
                },
            )
        )
        self.db.commit()

    async def asyncTearDown(self):
        """
        asyncTearDown 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        for key in await self.redis_client.keys("llm:score:score_cache_q1:*"):
            await self.redis_client.delete(key)
        await redis_cache.close_redis()
        redis_cache.settings.redis_url = self.original_url
        self.db.close()
        self.engine.dispose()

    async def test_evaluate_answer_writes_and_reads_score_result_from_real_redis(self):
        """
        test_evaluate_answer_writes_and_reads_score_result_from_real_redis 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        original_key = scoring_service.settings.llm_api_key
        scoring_service.settings.llm_api_key = ""
        try:
            transcript = "首先我会根据政策规定主动沟通群众诉求，协调资源推进落实，并及时总结完善机制。"
            result = await scoring_service.evaluate_answer(
                self.db,
                "score_cache_q1",
                transcript,
                None,
            )
            keys = await self.redis_client.keys("llm:score:score_cache_q1:*")
            self.assertEqual(len(keys), 1)

            sentinel = {
                "totalScore": 88,
                "maxScore": 100,
                "grade": "A",
                "dimensions": [],
                "mediaRecord": {"url": "old"},
                "visualObservation": "old observation",
            }
            await redis_cache.cache_set_json(keys[0], sentinel, 30)
            cached_result = await scoring_service.evaluate_answer(
                self.db,
                "score_cache_q1",
                transcript,
                None,
            )
        finally:
            scoring_service.settings.llm_api_key = original_key

        self.assertIn("totalScore", result)
        self.assertEqual(cached_result["totalScore"], 88)
        self.assertNotIn("mediaRecord", cached_result)
        self.assertNotIn("visualObservation", cached_result)


if __name__ == "__main__":
    unittest.main()
