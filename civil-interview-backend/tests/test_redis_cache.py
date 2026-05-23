import unittest

from app.core import redis_cache

TEST_REDIS_URL = "redis://127.0.0.1:6379/15"


class RedisCacheHelpersTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_url = redis_cache.settings.redis_url
        redis_cache.settings.redis_url = TEST_REDIS_URL
        await redis_cache.close_redis()
        client = await redis_cache.get_redis()
        if client is None:
            self.fail("Redis client was not created for integration test")
        await client.ping()
        await client.delete("test:redis-cache:json")

    async def asyncTearDown(self):
        client = await redis_cache.get_redis()
        if client is not None:
            await client.delete("test:redis-cache:json")
        await redis_cache.close_redis()
        redis_cache.settings.redis_url = self.original_url

    async def test_cache_get_and_set_json_use_real_redis(self):
        payload = {"ok": True, "message": "真实 Redis 缓存"}

        self.assertTrue(await redis_cache.cache_set_json("test:redis-cache:json", payload, 30))
        self.assertEqual(await redis_cache.cache_get_json("test:redis-cache:json"), payload)


if __name__ == "__main__":
    unittest.main()
