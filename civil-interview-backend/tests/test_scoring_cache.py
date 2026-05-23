import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import redis_cache
from app.db.session import Base
from app.models.entities import Question
from app.services import scoring_service

TEST_REDIS_URL = "redis://127.0.0.1:6379/15"


class ScoringCacheTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
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
        for key in await self.redis_client.keys("llm:score:score_cache_q1:*"):
            await self.redis_client.delete(key)
        await redis_cache.close_redis()
        redis_cache.settings.redis_url = self.original_url
        self.db.close()
        self.engine.dispose()

    async def test_evaluate_answer_writes_and_reads_score_result_from_real_redis(self):
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
