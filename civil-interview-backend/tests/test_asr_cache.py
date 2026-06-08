"""
这个测试文件守住 `test_asr_cache` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
import hashlib
import unittest

from app.core import ai
from app.core import redis_cache

TEST_REDIS_URL = "redis://127.0.0.1:6379/15"


class AsrCacheTestCase(unittest.IsolatedAsyncioTestCase):
    """
    AsrCacheTestCase 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

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
        self.client = await redis_cache.get_redis()
        if self.client is None:
            self.fail("Redis client was not created for ASR integration test")
        await self.client.ping()
        self.keys: list[str] = []

    async def asyncTearDown(self):
        """
        asyncTearDown 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        if self.keys:
            await self.client.delete(*self.keys)
        await redis_cache.close_redis()
        redis_cache.settings.redis_url = self.original_url

    async def test_transcribe_audio_file_returns_cached_transcript_from_real_redis(self):
        """
        test_transcribe_audio_file_returns_cached_transcript_from_real_redis 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        audio_bytes = b"x" * 4096
        asr_model = ai._resolve_asr_model()
        remote_asr_model = ai._resolve_remote_asr_model()
        asr_cache_scope = hashlib.sha256(
            "|".join(
                [
                    ai.settings.asr_provider,
                    asr_model,
                    remote_asr_model,
                    ai.settings.funasr_vad_model_name,
                    ai.settings.funasr_punc_model_name if ai.settings.funasr_enable_punc else "",
                    "zh",
                    ai.ASR_SIMPLIFIED_CHINESE_PROMPT,
                    ai.ASR_CACHE_SCHEMA,
                ]
            ).encode("utf-8")
        ).hexdigest()[:12]
        cache_key = f"asr:transcript:{asr_cache_scope}:{hashlib.sha256(audio_bytes).hexdigest()}"
        self.keys.append(cache_key)

        await redis_cache.cache_set_json(cache_key, "缓存文本", 30)
        result = await ai.transcribe_audio_file(audio_bytes, filename="answer.webm")

        self.assertEqual(result, "缓存文本")


if __name__ == "__main__":
    unittest.main()
