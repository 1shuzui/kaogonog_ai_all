import hashlib
import unittest

from app.core import ai
from app.core import redis_cache

TEST_REDIS_URL = "redis://127.0.0.1:6379/15"


class AsrCacheTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_url = redis_cache.settings.redis_url
        redis_cache.settings.redis_url = TEST_REDIS_URL
        await redis_cache.close_redis()
        self.client = await redis_cache.get_redis()
        if self.client is None:
            self.fail("Redis client was not created for ASR integration test")
        await self.client.ping()
        self.keys: list[str] = []

    async def asyncTearDown(self):
        if self.keys:
            await self.client.delete(*self.keys)
        await redis_cache.close_redis()
        redis_cache.settings.redis_url = self.original_url

    async def test_transcribe_audio_file_returns_cached_transcript_from_real_redis(self):
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
