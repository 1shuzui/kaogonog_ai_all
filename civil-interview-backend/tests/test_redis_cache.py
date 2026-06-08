"""
这个测试文件守住 `test_redis_cache` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
import unittest

from app.core import redis_cache

TEST_REDIS_URL = "redis://127.0.0.1:6379/15"


class RedisCacheHelpersTestCase(unittest.IsolatedAsyncioTestCase):
    """
    RedisCacheHelpersTestCase 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

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
        client = await redis_cache.get_redis()
        if client is None:
            self.fail("Redis client was not created for integration test")
        await client.ping()
        await client.delete("test:redis-cache:json")

    async def asyncTearDown(self):
        """
        asyncTearDown 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        client = await redis_cache.get_redis()
        if client is not None:
            await client.delete("test:redis-cache:json")
        await redis_cache.close_redis()
        redis_cache.settings.redis_url = self.original_url

    async def test_cache_get_and_set_json_use_real_redis(self):
        """
        test_cache_get_and_set_json_use_real_redis 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        payload = {"ok": True, "message": "真实 Redis 缓存"}

        self.assertTrue(await redis_cache.cache_set_json("test:redis-cache:json", payload, 30))
        self.assertEqual(await redis_cache.cache_get_json("test:redis-cache:json"), payload)


if __name__ == "__main__":
    unittest.main()
