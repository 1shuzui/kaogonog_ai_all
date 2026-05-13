"""Quick integration test for key APIs"""
import logging
import urllib.request, urllib.parse, json

BASE = "https://xzqianmianyuzhoukeji.com/api"
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

def post_form(url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body)
    return json.loads(urllib.request.urlopen(req).read())

def get_auth(url, token):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    return json.loads(urllib.request.urlopen(req).read())

def post_json(url, data, token):
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    return json.loads(urllib.request.urlopen(req).read())

# 1. Login
token_resp = post_form(f"{BASE}/token", {"username": "admin", "password": "admin123"})
token = token_resp["access_token"]
logger.info("Integration login completed", extra={"event": "integration.login", "token_present": bool(token)})

# 2. User info
user = get_auth(f"{BASE}/user/info", token)
logger.info("Integration user info completed", extra={"event": "integration.user_info", "username": user.get("id") or user.get("username")})

# 3. Provinces
provinces = get_auth(f"{BASE}/user/provinces", token)
logger.info("Integration provinces completed", extra={"event": "integration.provinces", "count": len(provinces)})

# 4. Questions list
qs = get_auth(f"{BASE}/questions?current=1&pageSize=3", token)
logger.info("Integration questions completed", extra={"event": "integration.questions", "total": qs["total"], "has_first": bool(qs["list"])})

# 5. Random questions
rqs = get_auth(f"{BASE}/questions/random?count=2", token)
logger.info("Integration random questions completed", extra={"event": "integration.questions_random", "count": len(rqs)})

# 6. Exam start
exam = post_json(f"{BASE}/exam/start", {"questionIds": [qs['list'][0]['id']]}, token)
logger.info("Integration exam start completed", extra={"event": "integration.exam_start", "exam_id": exam["examId"]})

# 7. Scoring evaluate
score = post_json(f"{BASE}/scoring/evaluate", {
    "questionId": qs['list'][0]['id'],
    "transcript": "我认为这个问题需要从多个角度分析。首先，基层治理需要网格化管理。其次，要注重精细化管理和责任到人。最后，要结合共建共治共享的理念推进社会治理现代化。",
    "examId": exam['examId']
}, token)
logger.info("Integration scoring completed", extra={"event": "integration.scoring", "total_score": score["totalScore"], "grade": score["grade"]})

# 8. History
hist = get_auth(f"{BASE}/history", token)
logger.info("Integration history completed", extra={"event": "integration.history", "total": hist["total"]})

# 9. Stats
stats = get_auth(f"{BASE}/history/stats", token)
logger.info("Integration history stats completed", extra={"event": "integration.history_stats", "total_exams": stats["totalExams"]})

# 10. Positions
pos = get_auth(f"{BASE}/positions", token)
logger.info("Integration positions completed", extra={"event": "integration.positions", "count": len(pos)})

logger.info("Integration API tests passed", extra={"event": "integration.completed"})
