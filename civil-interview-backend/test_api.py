"""Quick test script to verify API endpoints"""
import requests

BASE = "http://localhost:8050"

# 1. Login
r = requests.post(f"{BASE}/token", data={"username": "testuser", "password": "secret"})
print(f"1. Login: {r.status_code}")
token = r.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# 2. Get random questions
r = requests.get(f"{BASE}/questions/random?province=national&count=2", headers=headers)
print(f"2. Random questions: {r.status_code}, count={len(r.json())}")
questions = r.json()
if questions:
    q_ids = [q["id"] for q in questions]
    print(f"   IDs: {q_ids}")

    # 3. Start exam
    r = requests.post(f"{BASE}/exam/start", json={"questionIds": q_ids}, headers=headers)
    print(f"3. Start exam: {r.status_code}, response={r.json()}")

# 4. Test new endpoints
r = requests.put(f"{BASE}/user/preferences", json={"defaultPrepTime": 90}, headers=headers)
print(f"4. User preferences: {r.status_code}, response={r.json()}")

r = requests.post(f"{BASE}/targeted/focus", json={"province": "national", "position": "tax"}, headers=headers)
print(f"5. Targeted focus: {r.status_code}, keys={list(r.json().keys())}")

r = requests.post(f"{BASE}/questions/generate", json={"province": "national", "position": "tax", "count": 2}, headers=headers)
print(f"6. Questions generate: {r.status_code}, count={len(r.json())}")

r = requests.post(f"{BASE}/training/generate", json={"dimension": "analysis", "count": 2}, headers=headers)
print(f"7. Training generate: {r.status_code}, count={len(r.json())}")

r = requests.get(f"{BASE}/history/stats", headers=headers)
print(f"8. History stats: {r.status_code}")

print("\nAll tests completed!")
