"""
Redis 缓存测试确认 JSON 序列化和 TTL 策略没有偏离运行时行为。

题库、评分和转写缓存共用同一套 Redis helper；如果 helper 只在 mock 环境通过，现网可能出现中文字段乱码、过期时间不生效或空值误判。
因此这里直接连真实 Redis 测基础读写，而不是只测 Python 字典替身。

@param: 无；测试 key 和 Redis 连接在异步 fixture 中创建。
@return: 无直接返回；断言通过表示缓存 helper 可以处理真实 JSON 值。
@raises ImportError: Redis 客户端或缓存模块导入失败时会中断测试。
"""
import unittest

from app.core import redis_cache

TEST_REDIS_URL = "redis://127.0.0.1:6379/15"


class RedisCacheHelpersTestCase(unittest.IsolatedAsyncioTestCase):
    """
    Redis helper 用例集合，验证 JSON 值在真实 Redis 中能稳定写入和读取。

    题库、评分和 ASR 共用这些 helper；只测 mock 会漏掉编码、过期时间和连接池释放这类线上问题。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 异步测试用例类。
    @raises AssertionError: Redis 未连通或 JSON helper 读写不一致时由断言报告。
    """
    async def asyncSetUp(self):
        """
        将缓存 helper 测试切到隔离 Redis DB，并清掉固定测试 key。

        固定 key 便于验证真实 JSON 编码和 TTL 行为；隔离 DB 避免误删本地开发缓存。

        @param: 无；由 unittest 在每个异步用例前调用。
        @return: None；Redis 连接可用且测试 key 处于干净状态。
        @raises AssertionError: Redis 客户端未创建或 ping 失败时报告测试环境不可用。
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
        清理缓存 helper 测试 key，并恢复进入测试前的 Redis URL。

        全局 Redis URL 会被 ASR、评分和题库缓存复用，恢复它可以防止后续测试在错误库里读写数据。

        @param: 无；由 unittest 在每个异步用例后调用。
        @return: None；测试 key 删除且 Redis 连接关闭。
        @raises AssertionError: Redis 清理失败会由测试框架报告。
        """
        client = await redis_cache.get_redis()
        if client is not None:
            await client.delete("test:redis-cache:json")
        await redis_cache.close_redis()
        redis_cache.settings.redis_url = self.original_url

    async def test_cache_get_and_set_json_use_real_redis(self):
        """
        JSON 缓存 helper 必须能保留中文文本和布尔字段。

        评分建议、题库标签和转写文本都含中文；这里用真实 Redis 写回读一遍，确认编码和反序列化没有漂移。

        @param: 无；使用固定测试 key 写入中文 JSON。
        @return: None；读回内容和写入内容一致时通过。
        @raises AssertionError: Redis 写入失败或 JSON 反序列化结果不一致时失败。
        """
        payload = {"ok": True, "message": "真实 Redis 缓存"}

        self.assertTrue(await redis_cache.cache_set_json("test:redis-cache:json", payload, 30))
        self.assertEqual(await redis_cache.cache_get_json("test:redis-cache:json"), payload)


if __name__ == "__main__":
    unittest.main()
