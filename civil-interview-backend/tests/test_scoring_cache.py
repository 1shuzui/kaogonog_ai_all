"""
评分缓存测试防止同一答案被重复送入 LLM 并生成不一致分数。

评分结果既影响用户历史记录，也影响权益扣减后的体验感；缓存命中失败会让重试请求产生新分数或额外等待。
这里使用真实 Redis 路径，验证评分服务写入和读取的是同一份结构化结果。

@param: 无；测试通过 monkeypatch 隔离 LLM 调用并准备缓存 key。
@return: 无直接返回；断言通过表示评分缓存读写仍可复用。
@raises ImportError: 评分服务、Redis helper 或测试依赖缺失时会失败。
"""
import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core import redis_cache
from app.db.session import Base
from app.models.entities import Question
from app.services import scoring_service

TEST_REDIS_URL = "redis://127.0.0.1:6379/15"


class ScoringCacheTestCase(unittest.IsolatedAsyncioTestCase):
    """
    评分缓存用例集合，确认同一题同一答案重试时复用结构化评分结果。

    评分结果会进入历史记录和能力概览，重试请求如果再次触发 LLM，既慢又可能得到略有差异的分数；
    这里用真实 Redis 和隔离题库记录验证缓存写入、读取和敏感媒体字段剥离。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 异步测试用例类。
    @raises AssertionError: Redis 未连通、评分缓存未命中或返回结构不安全时由断言报告。
    """
    async def asyncSetUp(self):
        """
        准备真实 Redis 缓存和隔离题库记录。

        评分缓存依赖题目采分点、关键词和答案文本共同生成 key；这里同时准备 Redis 和题库记录，才能验证缓存命中不会重复调用 LLM。

        @param: 无；由 unittest 在每个异步用例前调用。
        @return: None；Redis、内存库和测试题目准备完成。
        @raises AssertionError: Redis 未连通或测试题库准备失败时报告。
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

        @event.listens_for(self.engine, "connect")
        def _register_mysql_collation(dbapi_conn, _):
            dbapi_conn.create_collation(
                "utf8mb4_0900_ai_ci",
                lambda left, right: (left > right) - (left < right),
            )

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
        清理评分缓存 key、恢复 Redis URL，并释放临时数据库。

        评分缓存 key 带题目 ID 前缀；用例结束后主动清理，避免后续测试误读本用例写入的哨兵评分结果。

        @param: 无；由 unittest 在每个异步用例后调用。
        @return: None；缓存、连接和数据库资源全部释放。
        @raises AssertionError: Redis 清理或数据库释放失败会由测试框架报告。
        """
        for key in await self.redis_client.keys("llm:score:score_cache_q1:*"):
            await self.redis_client.delete(key)
        await redis_cache.close_redis()
        redis_cache.settings.redis_url = self.original_url
        self.db.close()
        self.engine.dispose()

    async def test_evaluate_answer_writes_and_reads_score_result_from_real_redis(self):
        """
        第一次评分要写缓存，第二次同题同答案要读缓存。

        缓存返回给前端前会去掉 mediaRecord 和 visualObservation，避免把旧上传媒体或视频观察混入新的评分展示。

        @param: 无；构造一题一答并手工替换缓存内容。
        @return: None；缓存命中且敏感媒体字段被剥离时通过。
        @raises AssertionError: 缓存没有写入、未命中或返回旧媒体字段时失败。
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

    async def test_transcribe_builds_asr_context_from_question_id(self):
        """
        转写接口拿到 questionId 后要把题目上下文传给底层 ASR。

        这里不跑真实 FunASR，只验证服务层会读取题干、采分点和关键词，生成上下文短语后传入 `transcribe_audio_file_with_meta`。

        @param: 无；monkeypatch 替换底层 ASR 入口。
        @return: None；上下文包含题目关键词且转写结果正常返回时通过。
        @raises AssertionError: questionId 没有进入 ASR 上下文链路时失败。
        """
        captured = {}

        async def fake_transcribe_audio_file_with_meta(audio_bytes, filename="answer.webm", context_phrases=None):
            captured["audio_bytes"] = audio_bytes
            captured["filename"] = filename
            captured["context_phrases"] = context_phrases or []
            return {
                "transcript": "测试文字稿",
                "asrMeta": {"audioSha256": ""},
                "needsRetry": False,
                "message": "",
            }

        original = scoring_service.transcribe_audio_file_with_meta
        scoring_service.transcribe_audio_file_with_meta = fake_transcribe_audio_file_with_meta
        try:
            result = await scoring_service.transcribe(
                b"audio-bytes",
                filename="answer.webm",
                db=self.db,
                question_id="score_cache_q1",
            )
        finally:
            scoring_service.transcribe_audio_file_with_meta = original

        self.assertEqual(result["transcript"], "测试文字稿")
        self.assertEqual(captured["audio_bytes"], b"audio-bytes")
        self.assertIn("沟通", captured["context_phrases"])
        self.assertIn("协调", captured["context_phrases"])
        self.assertIn("主动沟通协调", captured["context_phrases"])


if __name__ == "__main__":
    unittest.main()
