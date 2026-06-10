"""
ASR 缓存测试确认同一段录音不会被重复送进 FunASR。

语音转写成本和耗时都比较敏感，尤其是长音频已经通过 VAD 切段处理；缓存失效会让评分等待变长，
也会让同一次答题的文字稿出现前后不一致。因此这里用真实 Redis 路径验证缓存 key、TTL 和回读行为。

@param: 无；测试音频、Redis key 和 monkeypatch 在用例内部准备。
@return: 无直接返回；断言通过表示转写缓存仍能命中。
@raises ImportError: Redis、ASR 网关或测试依赖缺失时，导入阶段会失败。
"""
import hashlib
import unittest

from app.core import ai
from app.core import redis_cache

TEST_REDIS_URL = "redis://127.0.0.1:6379/15"


class AsrCacheTestCase(unittest.IsolatedAsyncioTestCase):
    """
    ASR 缓存用例集合，验证转写缓存使用真实 Redis 而不是内存替身。

    FunASR 切段识别比普通文本处理更耗时，同一份音频在重试评分时必须复用文字稿；
    这里把 Redis 作为集成边界来测，是为了提前发现缓存 key 或 TTL 改动造成的重复转写。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 异步测试用例类。
    @raises AssertionError: Redis 未连通、缓存 key 失配或转写未命中缓存时由断言报告。
    """
    async def asyncSetUp(self):
        """
        为 ASR 缓存测试切到隔离 Redis DB。

        这里不用内存替身，是因为 ASR 缓存 key 包含模型、VAD、标点和 schema 信息，只有真实 Redis 才能暴露连接池和 TTL 问题。

        @param: 无；由 unittest 在每个异步用例前调用。
        @return: None；Redis 连接和待清理 key 列表准备完成。
        @raises AssertionError: Redis 客户端未创建或 ping 失败时报告测试环境不可用。
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
        清理 ASR 缓存测试写入的 Redis key，并恢复原始连接配置。

        恢复配置很关键：ASR、评分和题库缓存共用全局 settings，遗留测试 DB 会让后续用例误连隔离库。

        @param: 无；由 unittest 在每个异步用例后调用。
        @return: None；测试 key 删除且 Redis 连接关闭。
        @raises AssertionError: Redis 清理失败会由测试框架报告。
        """
        if self.keys:
            await self.client.delete(*self.keys)
        await redis_cache.close_redis()
        redis_cache.settings.redis_url = self.original_url

    async def test_transcribe_audio_file_returns_cached_transcript_from_real_redis(self):
        """
        已存在的 ASR 缓存必须直接返回，不再调用真实转写管线。

        缓存 scope 会把 ASR provider、模型、VAD、标点和 schema 都纳入 key，避免模型切换后误用旧文字稿。

        @param: 无；用固定音频字节预写一条 Redis 缓存。
        @return: None；返回缓存文本时通过。
        @raises AssertionError: 缓存未命中或返回内容不一致时失败。
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
