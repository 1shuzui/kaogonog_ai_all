"""Quick integration test for key APIs"""
import urllib.request, urllib.parse, json

BASE = "http://localhost:8050"

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
print(f"[OK] Login: token={token[:30]}...")

# 2. User info
user = get_auth(f"{BASE}/user/info", token)
print(f"[OK] User info: {user}")

# 3. Provinces
provinces = get_auth(f"{BASE}/user/provinces", token)
print(f"[OK] Provinces: {len(provinces)} items")

# 4. Questions list
qs = get_auth(f"{BASE}/questions?current=1&pageSize=3", token)
print(f"[OK] Questions: total={qs['total']}, first={qs['list'][0]['stem'][:20] if qs['list'] else 'none'}...")

# 5. Random questions
rqs = get_auth(f"{BASE}/questions/random?count=2", token)
print(f"[OK] Random questions: {len(rqs)} items")

# 6. Exam start
exam = post_json(f"{BASE}/exam/start", {"questionIds": [qs['list'][0]['id']]}, token)
print(f"[OK] Exam start: examId={exam['examId']}")

# 7. Scoring evaluate
score = post_json(f"{BASE}/scoring/evaluate", {
    "questionId": qs['list'][0]['id'],
    "transcript": "我认为这个问题需要从多个角度分析。首先，基层治理需要网格化管理。其次，要注重精细化管理和责任到人。最后，要结合共建共治共享的理念推进社会治理现代化。",
    "examId": exam['examId']
}, token)
print(f"[OK] Scoring: totalScore={score['totalScore']}, grade={score['grade']}")

# 8. History
hist = get_auth(f"{BASE}/history", token)
print(f"[OK] History: total={hist['total']}")

# 9. Stats
stats = get_auth(f"{BASE}/history/stats", token)
print(f"[OK] Stats: totalExams={stats['totalExams']}")

# 10. Positions
pos = get_auth(f"{BASE}/positions", token)
print(f"[OK] Positions: {len(pos)} items")

print("\n=== ALL API TESTS PASSED ===")
