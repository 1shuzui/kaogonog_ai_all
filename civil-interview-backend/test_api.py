"""Quick test script to verify API endpoints"""
import logging
import requests

BASE = "https://xzqianmianyuzhoukeji.com/api"
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# 1. Login
r = requests.post(f"{BASE}/token", data={"username": "testuser", "password": "secret"})
logger.info("API smoke login completed", extra={"event": "api_smoke.login", "status_code": r.status_code})
token = r.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# 2. Get random questions
r = requests.get(f"{BASE}/questions/random?province=national&count=2", headers=headers)
logger.info("API smoke random questions completed", extra={"event": "api_smoke.questions_random", "status_code": r.status_code, "count": len(r.json())})
questions = r.json()
if questions:
    q_ids = [q["id"] for q in questions]
    logger.info("API smoke random question ids", extra={"event": "api_smoke.question_ids", "question_ids": q_ids})

    # 3. Start exam
    r = requests.post(f"{BASE}/exam/start", json={"questionIds": q_ids}, headers=headers)
    logger.info("API smoke exam start completed", extra={"event": "api_smoke.exam_start", "status_code": r.status_code, "response": r.json()})

# 4. Test new endpoints
r = requests.put(f"{BASE}/user/preferences", json={"defaultPrepTime": 90}, headers=headers)
logger.info("API smoke preferences completed", extra={"event": "api_smoke.preferences", "status_code": r.status_code, "response": r.json()})

r = requests.post(f"{BASE}/targeted/focus", json={"province": "national", "position": "tax"}, headers=headers)
logger.info("API smoke targeted focus completed", extra={"event": "api_smoke.targeted_focus", "status_code": r.status_code, "keys": list(r.json().keys())})

r = requests.post(f"{BASE}/questions/generate", json={"province": "national", "position": "tax", "count": 2}, headers=headers)
logger.info("API smoke questions generate completed", extra={"event": "api_smoke.questions_generate", "status_code": r.status_code, "count": len(r.json())})

r = requests.post(f"{BASE}/training/generate", json={"dimension": "analysis", "count": 2}, headers=headers)
logger.info("API smoke training generate completed", extra={"event": "api_smoke.training_generate", "status_code": r.status_code, "count": len(r.json())})

r = requests.get(f"{BASE}/history/stats", headers=headers)
logger.info("API smoke history stats completed", extra={"event": "api_smoke.history_stats", "status_code": r.status_code})

logger.info("API smoke completed", extra={"event": "api_smoke.completed"})
