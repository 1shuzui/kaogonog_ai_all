"""
Refactored Civil Service Interview AI Scoring API (v2.1 - Pydantic V2 Fixed)
修复了 Pydantic V2 的 @validator 弃用警告
"""
import json
import os
import time
import uuid
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# --- Security: Load env vars first (P0.1) ---
load_dotenv()

# --- FastAPI & Pydantic V2 (P2.9) ---
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
# 注意：这里导入了 field_validator
from pydantic import BaseModel, Field, field_validator
from passlib.context import CryptContext
from jose import JWTError, jwt
import logging

# --- LLM & ASR (P0.3, P1.3) ---
from openai import OpenAI
import asyncio

# --- Two-Stage Scoring (New) ---
from two_stage_scoring import (
    build_evidence_extraction_prompt,
    build_evidence_based_scoring_prompt,
    validate_evidence,
    validate_scoring_result,
    fallback_scoring
)

# ================= Configuration =================
# --- Security: Moved to .env (P0.1) ---
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in .env file")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# API Keys
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")

# --- CORS ---
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# --- Logging (P3.16) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= Database Placeholder =================
PERSISTENT_DB_PATH = "db.json"

def load_db():
    if os.path.exists(PERSISTENT_DB_PATH):
        try:
            with open(PERSISTENT_DB_PATH, 'r') as f:
                data = json.load(f)
                for key in ["questions", "exams", "history", "users"]:
                    if key not in data:
                        data[key] = []
                return data
        except Exception as e:
            logger.error(f"Failed to load DB: {e}")
    return {"questions": [], "exams": {}, "history": [], "users": {}}

def save_db(data):
    try:
        with open(PERSISTENT_DB_PATH, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save DB: {e}")

mock_db = load_db()

# --- 题目种子数据：若数据库中无题目则自动填充 ---
if not mock_db.get("questions"):
    seed_path = os.path.join(os.path.dirname(__file__), "seed_questions.json")
    if os.path.exists(seed_path):
        with open(seed_path, "r", encoding="utf-8") as f:
            mock_db["questions"] = json.load(f)
        save_db(mock_db)
        logger.info(f"Seeded {len(mock_db['questions'])} questions from seed_questions.json")

# ================= Models (Pydantic V2) =================

# 模拟省份映射
PROVINCE_NAMES = {"zhejiang": "浙江", "national": "全国", "henan": "河南"}

class QuestionCreate(BaseModel):
    stem: str
    dimension: str = "analysis"
    province: str = "national"
    prepTime: int = 90
    answerTime: int = 180
    scoringPoints: List[Dict[str, Any]] = Field(default_factory=list)
    keywords: Dict[str, List[str]] = Field(default_factory=dict)

    # --- Pydantic V2 Style Validator (Fixed) ---
    @field_validator('stem')
    @classmethod
    def stem_not_empty(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Stem cannot be empty')
        return v

class EvaluateRequest(BaseModel):
    questionId: str
    transcript: str
    examId: Optional[str] = None

    # --- Pydantic V2 Style Validator (Fixed) ---
    @field_validator('transcript')
    @classmethod
    def transcript_length(cls, v):
        if len(v) > 5000:
            raise ValueError('Transcript too long')
        return v

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None

    # --- Pydantic V2 Style Validator (Fixed) ---
    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

# ================= JWT & Auth =================
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class AuthUser(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

class UserInDB(AuthUser):
    hashed_password: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# 模拟用户数据库
fake_users_db = {
    "testuser": {
        "username": "testuser",
        "full_name": "Test User",
        "email": "test@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
    },
    "hanhan": {
        "username": "hanhan",
        "full_name": "hanhan",
        "email": "",
        "hashed_password": "$2b$12$stxYEqkAA2ZjahnaZRoPYO5f6FTbc7e.dhHvNN5eqm/Bcy8xYR3NG",
        "disabled": False,
    }
}

# 从 db.json 恢复已注册用户（解决重启后用户丢失问题）
for uname, udata in mock_db.get("users", {}).items():
    if uname not in fake_users_db and isinstance(udata, dict) and "hashed_password" in udata:
        fake_users_db[uname] = udata
        logger.info(f"Restored registered user: {uname}")

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    # (P2.10) datetime.utcnow() -> datetime.now(timezone.utc)
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

# ================= LLM Logic =================
client = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL, timeout=25.0)

def build_prompt(answer_text: str, question: Dict, province_name: str = "national") -> str:
    return f"""
    You are a strict civil service interview scoring expert for {province_name}.
    Evaluate the following answer based on the question and criteria.
    
    Question: {question.get('stem', '')}
    Expected Points: {json.dumps(question.get('scoringPoints', []))}
    
    Candidate Answer: {answer_text}
    
    Output JSON only with scores for each dimension.
    """

def call_llm_api(prompt: str, system_msg: str = None, temperature: float = 0.1, max_tokens: int = 2000) -> Optional[Dict]:
    if not QWEN_API_KEY:
        logger.error("[ERROR] API Key not configured")
        return None
    if system_msg is None:
        system_msg = "You are a civil service interview expert. Output JSON only."

    try:
        response = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=25.0
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content)
    except Exception as e:
        logger.error(f"[ERROR] API call failed: {e}")
        return None

async def call_llm_api_async(prompt: str, system_msg: str = None, temperature: float = 0.1, max_tokens: int = 2000) -> Optional[Dict]:
    """异步调用LLM，避免阻塞事件循环"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: call_llm_api(prompt, system_msg, temperature, max_tokens))

class LLMResponseSchema(BaseModel):
    total_score: float
    dimension_scores: Dict[str, float]
    rationale: str

def validate_llm_response(raw_json: Dict):
    try:
        return LLMResponseSchema(**raw_json)
    except Exception as e:
        logger.error(f"LLM Response validation error: {e}")
        return None

# ================= ASR Integration =================
async def transcribe_audio_file(audio_bytes: bytes) -> str:
    try:
        await asyncio.sleep(1) # 模拟处理延迟
        if b"noise" in audio_bytes:
            return "This is a noisy recording, I cannot hear clearly."
        # (P2.10) datetime.utcnow() -> datetime.now(timezone.utc)
        return f"Transcribed: Candidate is discussing a topic relevant to the exam. Dynamic transcript generated at {datetime.now(timezone.utc)}."
    except Exception as e:
        logger.error(f"ASR Error: {e}")
        raise HTTPException(status_code=500, detail="Transcription failed")

# ================= API App =================
app = FastAPI(title="Civil Service Interview AI Scoring API", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 0. Auth ---
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register")
async def register_user(data: RegisterRequest):
    if data.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already registered")
    user_data = {
        "username": data.username,
        "full_name": data.full_name or data.username,
        "email": data.email or "",
        "hashed_password": get_password_hash(data.password),
        "disabled": False,
    }
    fake_users_db[data.username] = user_data
    # 同步到 mock_db 以持久化（解决重启后用户丢失问题）
    if not isinstance(mock_db.get("users"), dict):
        mock_db["users"] = {}
    mock_db["users"][data.username] = user_data
    save_db(mock_db)
    return {"success": True, "message": "User created successfully"}

# --- 1. Scoring & Exam Fixes ---
@app.post("/scoring/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    try:
        audio_bytes = await audio.read()
        transcript = await transcribe_audio_file(audio_bytes)
        return {
            "transcript": transcript,
            "duration": len(transcript) / 10
        }
    except Exception as e:
        logger.error(f"Transcription endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Transcription service error")

@app.post("/scoring/evaluate")
async def evaluate_answer(request: EvaluateRequest, current_user: AuthUser = Depends(get_current_user)):
    """
    两阶段评分接口
    阶段1：证据抽取
    阶段2：基于证据评分
    """
    question = next((q for q in mock_db["questions"] if q["id"] == request.questionId), None)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    province_code = question.get("province", "national")
    province_name = PROVINCE_NAMES.get(province_code, province_code).title()

    dim_mapping = {
        "analysis": "综合分析",
        "practical": "实务落地",
        "emergency": "应急应变",
        "legal": "法治思维",
        "logic": "逻辑结构",
        "expression": "语言表达"
    }

    # ===== 阶段1：证据抽取 =====
    logger.info("Stage 1: Evidence extraction")
    evidence_prompt = build_evidence_extraction_prompt(request.transcript, question)
    evidence_raw = await call_llm_api_async(evidence_prompt)

    evidence = {"present": [], "absent": [], "penalty": [], "bonus": []}
    if evidence_raw and isinstance(evidence_raw, dict):
        evidence = evidence_raw.get("evidence", evidence)
        # 校验证据
        evidence = validate_evidence(evidence, request.transcript)
    else:
        logger.warning("Evidence extraction failed, using empty evidence")

    # ===== 阶段2：基于证据评分 =====
    logger.info("Stage 2: Evidence-based scoring")
    scoring_prompt = build_evidence_based_scoring_prompt(evidence, question)
    scoring_raw = await call_llm_api_async(scoring_prompt)

    dim_scores = {}
    rationale = ""
    scoring_result = None

    if scoring_raw and isinstance(scoring_raw, dict):
        # 获取维度满分映射
        max_scores = {d.get("name", f"维度{i}"): d.get("score", 0)
                     for i, d in enumerate(question.get("dimensions", []))}

        # 校验评分结果
        is_valid, errors, scoring_result = validate_scoring_result(scoring_raw, evidence, max_scores)

        if is_valid:
            dim_scores = scoring_result.get("dimension_scores", {})
            rationale = scoring_result.get("overall_rationale", "")
        else:
            logger.warning(f"Scoring validation failed: {errors}")

    # 如果两阶段评分都失败，使用兜底评分
    if not dim_scores:
        logger.warning("Two-stage scoring failed, using fallback")
        scoring_result = fallback_scoring(request.transcript, question, evidence)
        dim_scores = scoring_result.get("dimension_scores", {})
        rationale = scoring_result.get("overall_rationale", "")

    frontend_dims = []
    total = 0
    max_score = 30

    for key, display_name in dim_mapping.items():
        score = dim_scores.get(key, dim_scores.get(display_name, 0))
        frontend_dims.append({
            "name": display_name,
            "key": key,
            "score": round(score, 2),
            "maxScore": 20 if key in ["analysis", "practical"] else 15,
            "lostReasons": []
        })
        total += score

    grade = "B"
    if total / max_score > 0.85:
        grade = "A"

    result = {
        "totalScore": round(total, 2),
        "maxScore": max_score,
        "grade": grade,
        "dimensions": frontend_dims,
        "aiComment": rationale or "评分完成",
    }

    exam_id = request.examId
    if exam_id and exam_id in mock_db["exams"]:
        if "answers" not in mock_db["exams"][exam_id]:
            mock_db["exams"][exam_id]["answers"] = {}
        mock_db["exams"][exam_id]["answers"][request.questionId] = {
            "text": request.transcript,
            "score_result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        save_db(mock_db)

    return result

@app.get("/scoring/result/{exam_id}/{question_id}")
async def get_scoring_result(exam_id: str, question_id: str, current_user: AuthUser = Depends(get_current_user)):
    """获取指定考试中某道题的评分结果"""
    exams = mock_db.get("exams", {})
    if isinstance(exams, list):
        exams = {}
    if exam_id not in exams:
        raise HTTPException(status_code=404, detail="考试未找到")
    exam = exams[exam_id]
    answers = exam.get("answers", {})
    if question_id not in answers:
        raise HTTPException(status_code=404, detail="该题目的评分结果未找到")
    answer_data = answers[question_id]
    result = answer_data.get("score_result")
    if not result:
        raise HTTPException(status_code=404, detail="评分结果未找到")
    return result

@app.post("/exam/{exam_id}/complete")
async def complete_exam(exam_id: str, current_user: AuthUser = Depends(get_current_user)):
    if exam_id not in mock_db["exams"]:
        raise HTTPException(status_code=404, detail="Exam not found")

    exam = mock_db["exams"][exam_id]
    exam["status"] = "completed"
    exam["endTime"] = datetime.now(timezone.utc).isoformat()

    total_score = 0
    question_count = 0
    # 汇总各维度分数
    dim_totals = {}
    dim_max = {
        "综合分析": 20, "实务落地": 20,
        "法治思维": 15, "应急应变": 15,
        "逻辑结构": 15, "语言表达": 15
    }
    for q_id, answer_data in exam.get("answers", {}).items():
        score_data = answer_data.get("score_result", {})
        total_score += score_data.get("totalScore", 0)
        question_count += 1
        for dim_name, dim_score in score_data.get("dimensionScores", {}).items():
            if dim_name not in dim_totals:
                dim_totals[dim_name] = []
            dim_totals[dim_name].append(dim_score)

    avg_score = total_score / question_count if question_count > 0 else 0

    # 计算维度平均分
    dimensions = []
    for dim_name, max_score in dim_max.items():
        vals = dim_totals.get(dim_name, [])
        avg = round(sum(vals) / len(vals), 2) if vals else 0
        dimensions.append({"name": dim_name, "score": avg, "maxScore": max_score})

    history_record = {
        "examId": exam_id,
        "userId": current_user.user_id if hasattr(current_user, 'user_id') else None,
        "username": current_user.username if hasattr(current_user, 'username') else None,
        "date": exam["endTime"],
        "completedAt": exam["endTime"],
        "questionCount": question_count,
        "totalScore": round(avg_score, 2),
        "maxScore": 100,
        "grade": "B",
        "province": "national",
        "dimensions": dimensions,
        "questionSummary": f"Completed Exam: {exam_id}"
    }
    mock_db["history"].append(history_record)
    save_db(mock_db)

    return {"success": True, "finalScore": avg_score}

class ExamStartRequest(BaseModel):
    questionIds: List[str]

@app.post("/exam/start")
async def start_exam(data: ExamStartRequest, current_user: AuthUser = Depends(get_current_user)):
    """开始考试"""
    exam_id = f"exam_{uuid.uuid4().hex[:8]}"
    if isinstance(mock_db.get("exams"), list):
        mock_db["exams"] = {}
    mock_db["exams"][exam_id] = {
        "id": exam_id,
        "questionIds": data.questionIds,
        "startTime": datetime.now(timezone.utc).isoformat(),
        "status": "in_progress",
        "answers": {},
    }
    save_db(mock_db)
    return {
        "examId": exam_id,
        "questionIds": data.questionIds,
        "startTime": mock_db["exams"][exam_id]["startTime"],
    }

@app.post("/exam/{exam_id}/upload")
async def upload_recording(exam_id: str, recording: UploadFile = File(...), current_user: AuthUser = Depends(get_current_user)):
    """上传录音文件"""
    return {"success": True, "fileUrl": f"/uploads/{recording.filename}"}

@app.get("/positions")
async def get_positions(current_user: AuthUser = Depends(get_current_user)):
    """获取岗位系统列表"""
    return [
        {"code": "tax", "name": "\u7a0e\u52a1\u7cfb\u7edf"},
        {"code": "customs", "name": "\u6d77\u5173\u7cfb\u7edf"},
        {"code": "police", "name": "\u516c\u5b89\u7cfb\u7edf"},
        {"code": "court", "name": "\u6cd5\u9662\u7cfb\u7edf"},
        {"code": "procurate", "name": "\u68c0\u5bdf\u7cfb\u7edf"},
        {"code": "market", "name": "\u5e02\u573a\u76d1\u7ba1"},
        {"code": "general", "name": "\u7efc\u5408\u7ba1\u7406"},
        {"code": "township", "name": "\u4e61\u9547\u57fa\u5c42"},
        {"code": "finance", "name": "\u94f6\u4fdd\u76d1\u4f1a"},
        {"code": "diplomacy", "name": "\u5916\u4ea4\u7cfb\u7edf"},
    ]

# --- User Profile APIs (Added) ---
class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None

@app.get("/user/info")
async def get_user_info(current_user: AuthUser = Depends(get_current_user)):
    """获取当前登录用户的信息"""
    if current_user.username not in fake_users_db:
        raise HTTPException(status_code=404, detail="用户未找到")
    user_data = fake_users_db[current_user.username]
    return {
        "id": user_data["username"],
        "name": user_data.get("full_name", user_data["username"]),
        "avatar": user_data.get("avatar", ""),
        "province": user_data.get("province", "national"),
        "email": user_data.get("email", "")
    }

@app.put("/user/profile")
async def update_user_profile(data: UserProfileUpdate, current_user: AuthUser = Depends(get_current_user)):
    """更新用户资料"""
    if current_user.username not in fake_users_db:
        raise HTTPException(status_code=404, detail="用户未找到")
    user_data = fake_users_db[current_user.username]
    if data.full_name is not None:
        user_data["full_name"] = data.full_name
    if data.email is not None:
        user_data["email"] = data.email
    return {"success": True, "message": "信息已更新"}

@app.put("/user/password")
async def change_password(data: dict, current_user: AuthUser = Depends(get_current_user)):
    """修改密码"""
    if current_user.username not in fake_users_db:
        raise HTTPException(status_code=404, detail="用户未找到")
    user_data = fake_users_db[current_user.username]
    # Verify old password
    if not verify_password(data.get("old_password"), user_data["hashed_password"]):
        raise HTTPException(status_code=400, detail="原密码错误")
    # Update password
    user_data["hashed_password"] = get_password_hash(data.get("new_password"))
    return {"success": True, "message": "密码修改成功"}

@app.put("/user/preferences")
async def update_preferences(data: dict, current_user: AuthUser = Depends(get_current_user)):
    """更新用户偏好设置"""
    if current_user.username not in fake_users_db:
        raise HTTPException(status_code=404, detail="用户未找到")
    user_data = fake_users_db[current_user.username]
    if "preferences" not in user_data:
        user_data["preferences"] = {}
    user_data["preferences"].update(data)
    return {"success": True, "message": "偏好设置已更新"}

@app.get("/user/provinces")
async def get_provinces():
    """获取省份列表"""
    return [
        {"code": "national", "name": "国家公务员考试"},
        {"code": "beijing", "name": "北京"},
        {"code": "guangdong", "name": "广东"},
        {"code": "zhejiang", "name": "浙江"},
        {"code": "sichuan", "name": "四川"},
        {"code": "jiangsu", "name": "江苏"},
        {"code": "henan", "name": "河南"},
        {"code": "shandong", "name": "山东"}
    ]

@app.get("/user/me")
async def get_current_user_info(current_user: AuthUser = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email
    }

@app.get("/history")
async def get_history(current: int = 1, pageSize: int = 10, total: int = 0, current_user: AuthUser = Depends(get_current_user)):
    """获取历史记录列表"""
    history_list = mock_db.get("history", [])
    # 分页
    start = (current - 1) * pageSize
    end = start + pageSize
    paginated = history_list[start:end]
    return {
        "list": paginated,
        "total": len(history_list),
        "current": current,
        "pageSize": pageSize
    }

@app.get("/history/stats")
async def get_history_stats(current_user: AuthUser = Depends(get_current_user)):
    """获取历史统计"""
    history_list = mock_db.get("history", [])

    # 维度定义（与前端 constants.js 对齐）
    dim_defs = [
        {"key": "legal", "name": "法治思维", "maxScore": 20},
        {"key": "practical", "name": "实务落地", "maxScore": 20},
        {"key": "logic", "name": "逻辑结构", "maxScore": 15},
        {"key": "expression", "name": "语言表达", "maxScore": 15},
        {"key": "analysis", "name": "综合分析", "maxScore": 15},
        {"key": "emergency", "name": "应急应变", "maxScore": 15},
    ]

    if not history_list:
        dimension_averages = [
            {"name": d["name"], "avg": 0, "maxScore": d["maxScore"]}
            for d in dim_defs
        ]
        return {
            "totalExams": 0,
            "avgScore": 0,
            "bestScore": 0,
            "weakestDimension": "",
            "dimensionAverages": dimension_averages,
        }

    scores = [h.get("totalScore", 0) for h in history_list]

    # 计算各维度平均分
    dim_totals = {d["name"]: [] for d in dim_defs}
    for h in history_list:
        for dim in h.get("dimensions", []):
            name = dim.get("name")
            if name in dim_totals:
                dim_totals[name].append(dim.get("score", 0))

    dimension_averages = []
    for d in dim_defs:
        vals = dim_totals[d["name"]]
        avg = round(sum(vals) / len(vals), 2) if vals else 0
        dimension_averages.append({
            "name": d["name"],
            "avg": avg,
            "maxScore": d["maxScore"],
        })

    # 找出薄弱维度（得分百分比最低的）
    weakest = ""
    lowest_pct = 100
    for da in dimension_averages:
        if da["maxScore"] > 0 and da["avg"] > 0:
            pct = da["avg"] / da["maxScore"] * 100
            if pct < lowest_pct:
                lowest_pct = pct
                weakest = da["name"]

    return {
        "totalExams": len(history_list),
        "avgScore": round(sum(scores) / len(scores), 2),
        "bestScore": max(scores) if scores else 0,
        "weakestDimension": weakest,
        "dimensionAverages": dimension_averages,
    }

@app.get("/history/trend")
async def get_history_trend(limit: int = 7, current_user: AuthUser = Depends(get_current_user)):
    """获取历史趋势（近几次成绩）"""
    history_list = mock_db.get("history", [])
    # 筛选当前用户的记录（兼容旧记录没有username的情况）
    user_history = [
        h for h in history_list
        if h.get("username") == current_user.username or not h.get("username")
    ]
    user_history.sort(key=lambda x: x.get("completedAt", x.get("date", "")), reverse=True)

    # 取近 limit 次，再按时间正序排列（方便图表展示）
    recent = user_history[:limit]
    trend = []
    for i, record in enumerate(reversed(recent)):
        trend.append({
            "index": i + 1,
            "label": f"第{i + 1}次",
            "score": record.get("totalScore", 0),
            "date": record.get("completedAt", "")[:10] if record.get("completedAt") else ""
        })
    return trend

@app.get("/history/{exam_id}")
async def get_history_detail(exam_id: str, current_user: AuthUser = Depends(get_current_user)):
    """获取历史记录详情"""
    history_list = mock_db.get("history", [])
    record = next((h for h in history_list if h.get("examId") == exam_id), None)
    if not record:
        raise HTTPException(status_code=404, detail="历史记录未找到")
    return record

@app.get("/questions")
async def get_questions(
    keyword: str = "",
    dimension: str = "",
    province: str = "",
    current: int = 1,
    pageSize: int = 10,
    total: int = 0,
    current_user: AuthUser = Depends(get_current_user)
):
    """获取题目列表"""
    questions = mock_db.get("questions", [])

    # 过滤
    if keyword:
        questions = [q for q in questions if keyword in q.get("stem", "")]
    if dimension:
        questions = [q for q in questions if q.get("dimension") == dimension]
    if province and province != "all":
        questions = [q for q in questions if q.get("province") in (province, "national")]

    # 分页
    start = (current - 1) * pageSize
    end = start + pageSize
    paginated = questions[start:end]

    return {
        "list": paginated,
        "total": len(questions),
        "current": current,
        "pageSize": pageSize
    }

@app.get("/questions/random")
async def get_random_questions(
    province: str = "national",
    count: int = 5,
    current_user: AuthUser = Depends(get_current_user)
):
    """获取随机题目"""
    questions = mock_db.get("questions", [])
    if province and province != "all":
        questions = [q for q in questions if q.get("province") in (province, "national")]
    count = min(count, len(questions))
    return random.sample(questions, count) if questions else []

@app.get("/questions/{question_id}")
async def get_question_by_id(question_id: str, current_user: AuthUser = Depends(get_current_user)):
    """获取单个题目详情"""
    question = next((q for q in mock_db.get("questions", []) if q["id"] == question_id), None)
    if not question:
        raise HTTPException(status_code=404, detail="题目未找到")
    return question

@app.post("/questions")
async def create_question(data: QuestionCreate, current_user: AuthUser = Depends(get_current_user)):
    """创建题目"""
    question = data.model_dump()
    question["id"] = f"q_{uuid.uuid4().hex[:8]}"
    mock_db["questions"].append(question)
    save_db(mock_db)
    return question

@app.put("/questions/{question_id}")
async def update_question(question_id: str, data: QuestionCreate, current_user: AuthUser = Depends(get_current_user)):
    """更新题目"""
    for i, q in enumerate(mock_db.get("questions", [])):
        if q["id"] == question_id:
            updated = data.model_dump()
            updated["id"] = question_id
            mock_db["questions"][i] = updated
            save_db(mock_db)
            return updated
    raise HTTPException(status_code=404, detail="题目未找到")

@app.delete("/questions/{question_id}")
async def delete_question(question_id: str, current_user: AuthUser = Depends(get_current_user)):
    """删除题目"""
    questions = mock_db.get("questions", [])
    mock_db["questions"] = [q for q in questions if q["id"] != question_id]
    if len(mock_db["questions"]) == len(questions):
        raise HTTPException(status_code=404, detail="题目未找到")
    save_db(mock_db)
    return {"success": True}

# --- Targeted Training APIs ---
POSITION_NAMES = {
    "tax": "税务系统", "customs": "海关系统", "police": "公安系统",
    "court": "法院系统", "procurate": "检察系统", "market": "市场监管",
    "general": "综合管理", "township": "乡镇基层", "finance": "银保监会",
    "diplomacy": "外交系统"
}

DIMENSION_NAMES = {
    "analysis": "综合分析", "practical": "实务落地", "emergency": "应急应变",
    "legal": "法治思维", "logic": "逻辑结构", "expression": "语言表达"
}

@app.post("/targeted/focus")
async def get_focus_analysis(data: dict, current_user: AuthUser = Depends(get_current_user)):
    """获取岗位重点分析"""
    province = data.get("province", "national")
    position = data.get("position", "general")
    position_name = POSITION_NAMES.get(position, position)

    # 尝试使用 LLM 生成分析
    if QWEN_API_KEY:
        prompt = f"""请为公务员面试考生提供"{position_name}"岗位的面试重点分析。
请严格以JSON格式返回，包含以下字段：
- coreFocus: 数组(3项)，每项包含 name(能力名称,字符串), weight(权重百分比,数字), desc(描述,字符串)
- highFreqTypes: 数组(2-3项)，每项包含 type(题型,字符串), frequency(高/中/低,字符串), example(示例题目,字符串)
- hotTopics: 字符串数组(3-5项)，当前热点话题
- strategy: 字符串数组(3-4项)，备考策略建议"""
        result = await call_llm_api_async(prompt, system_msg="你是公务员面试辅导专家，请只输出JSON格式。")
        if result and "coreFocus" in result:
            return result

    # 回退模板数据
    return {
        "coreFocus": [
            {"name": "岗位专业能力", "weight": 30, "desc": f"考察考生对{position_name}相关专业知识的理解和应用能力"},
            {"name": "综合分析能力", "weight": 25, "desc": "考察对社会热点问题的分析判断能力"},
            {"name": "沟通协调能力", "weight": 20, "desc": "考察人际交往和团队协作能力"}
        ],
        "highFreqTypes": [
            {"type": "综合分析", "frequency": "高", "example": f"谈谈你对当前{position_name}领域改革的看法"},
            {"type": "应急应变", "frequency": "高", "example": "在工作中遇到突发情况，你如何处理？"},
            {"type": "组织管理", "frequency": "中", "example": "领导交给你一项重要任务，你如何开展工作？"}
        ],
        "hotTopics": ["基层治理现代化", "数字政府建设", "营商环境优化", "乡村振兴"],
        "strategy": [
            f"熟悉{position_name}相关政策法规和工作职责",
            "关注时事热点，积累社会治理案例",
            "练习结构化答题框架，提升逻辑表达",
            "多做模拟练习，注意时间控制"
        ]
    }

@app.post("/questions/generate")
async def generate_questions(data: dict, current_user: AuthUser = Depends(get_current_user)):
    """根据岗位和省份生成面试题目"""
    province = data.get("province", "national")
    position = data.get("position", "general")
    count = min(data.get("count", 5), 10)
    position_name = POSITION_NAMES.get(position, position)

    generated = []

    # 尝试使用 LLM 生成
    if QWEN_API_KEY:
        prompt = f"""请为"{position_name}"岗位生成{count}道公务员面试题目。
每道题以JSON对象表示，所有题目放在一个JSON数组中返回。
每道题包含字段：
- stem: 题目内容(字符串)
- dimension: 所属维度(analysis/practical/emergency/legal/logic/expression 之一)
返回纯JSON数组，不要有其他内容。"""
        result = await call_llm_api_async(prompt, system_msg="你是公务员面试命题专家，请只输出JSON数组。", max_tokens=3000)
        if result and isinstance(result, list):
            for i, q in enumerate(result[:count]):
                generated.append({
                    "id": f"gen_{uuid.uuid4().hex[:8]}",
                    "stem": q.get("stem", ""),
                    "dimension": q.get("dimension", "analysis"),
                    "province": province,
                    "prepTime": 90,
                    "answerTime": 180,
                    "scoringPoints": q.get("scoringPoints", [
                        {"content": "观点明确，分析深入", "score": 7},
                        {"content": "措施具体可行", "score": 8},
                        {"content": "逻辑清晰，表达流畅", "score": 5}
                    ]),
                    "keywords": q.get("keywords", {
                        "scoring": [], "deducting": [], "bonus": []
                    })
                })
            if generated:
                return generated

    # 回退：从题库中按条件随机抽取
    questions = mock_db.get("questions", [])
    if province and province != "all":
        filtered = [q for q in questions if q.get("province") in (province, "national")]
    else:
        filtered = questions
    sample_count = min(count, len(filtered))
    if filtered:
        sampled = random.sample(filtered, sample_count)
        for q in sampled:
            generated.append({
                "id": f"gen_{uuid.uuid4().hex[:8]}",
                "stem": q.get("stem", ""),
                "dimension": q.get("dimension", "analysis"),
                "province": province,
                "prepTime": q.get("prepTime", 90),
                "answerTime": q.get("answerTime", 180),
                "scoringPoints": q.get("scoringPoints", []),
                "keywords": q.get("keywords", {"scoring": [], "deducting": [], "bonus": []})
            })
    return generated

@app.post("/training/generate")
async def generate_training_questions(data: dict, current_user: AuthUser = Depends(get_current_user)):
    """根据维度生成专项训练题目"""
    dimension = data.get("dimension", "analysis")
    count = min(data.get("count", 3), 10)
    dimension_name = DIMENSION_NAMES.get(dimension, dimension)

    generated = []

    # 尝试使用 LLM 生成
    if QWEN_API_KEY:
        prompt = f"""请生成{count}道考察"{dimension_name}"能力的公务员面试题目。
每道题以JSON对象表示，所有题目放在一个JSON数组中返回。
每道题包含字段：
- stem: 题目内容(字符串)
- scoringPoints: 采分点数组，每项包含 content(内容) 和 score(分值)
- keywords: 包含 scoring(得分关键词数组), deducting(扣分关键词数组), bonus(加分关键词数组)
返回纯JSON数组，不要有其他内容。"""
        result = await call_llm_api_async(prompt, system_msg="你是公务员面试命题专家，请只输出JSON数组。", max_tokens=3000)
        if result and isinstance(result, list):
            for q in result[:count]:
                generated.append({
                    "id": f"train_{uuid.uuid4().hex[:8]}",
                    "stem": q.get("stem", ""),
                    "dimension": dimension,
                    "province": "national",
                    "prepTime": 90,
                    "answerTime": 180,
                    "scoringPoints": q.get("scoringPoints", [
                        {"content": f"对{dimension_name}有清晰理解", "score": 7},
                        {"content": "结合实际提出措施", "score": 8},
                        {"content": "逻辑清晰、表达规范", "score": 5}
                    ]),
                    "keywords": q.get("keywords", {
                        "scoring": [], "deducting": [], "bonus": []
                    })
                })
            if generated:
                return generated

    # 回退：从题库中按维度随机抽取
    questions = mock_db.get("questions", [])
    filtered = [q for q in questions if q.get("dimension") == dimension]
    if not filtered:
        filtered = questions
    sample_count = min(count, len(filtered))
    if filtered:
        sampled = random.sample(filtered, sample_count)
        for q in sampled:
            generated.append({
                "id": f"train_{uuid.uuid4().hex[:8]}",
                "stem": q.get("stem", ""),
                "dimension": dimension,
                "province": "national",
                "prepTime": q.get("prepTime", 90),
                "answerTime": q.get("answerTime", 180),
                "scoringPoints": q.get("scoringPoints", []),
                "keywords": q.get("keywords", {"scoring": [], "deducting": [], "bonus": []})
            })
    return generated

@app.post("/questions/import")
async def import_questions(file: UploadFile = File(...), current_user: AuthUser = Depends(get_current_user)):
    """从文件导入题目（支持 JSON 和 Excel 格式）"""
    imported_count = 0
    failed_count = 0

    try:
        content = await file.read()
        filename = file.filename.lower() if file.filename else ""

        if filename.endswith(".json"):
            questions_data = json.loads(content.decode("utf-8"))
            if not isinstance(questions_data, list):
                raise HTTPException(status_code=400, detail="JSON 文件应包含题目数组")
            for q in questions_data:
                try:
                    question = {
                        "id": f"q_{uuid.uuid4().hex[:8]}",
                        "stem": q.get("stem", "").strip(),
                        "dimension": q.get("dimension", "analysis"),
                        "province": q.get("province", "national"),
                        "prepTime": q.get("prepTime", 90),
                        "answerTime": q.get("answerTime", 180),
                        "scoringPoints": q.get("scoringPoints", []),
                        "keywords": q.get("keywords", {"scoring": [], "deducting": [], "bonus": []})
                    }
                    if not question["stem"]:
                        failed_count += 1
                        continue
                    mock_db["questions"].append(question)
                    imported_count += 1
                except Exception:
                    failed_count += 1

        elif filename.endswith((".xlsx", ".xls")):
            import io
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                raise HTTPException(status_code=400, detail="Excel 文件为空")
            headers = [str(h).strip().lower() if h else "" for h in rows[0]]

            # 识别列索引
            col_map = {}
            for i, h in enumerate(headers):
                if h in ("题干", "stem"):
                    col_map["stem"] = i
                elif h in ("所属维度", "dimension"):
                    col_map["dimension"] = i
                elif h in ("省份", "province"):
                    col_map["province"] = i
                elif h in ("准备时间", "preptime"):
                    col_map["prepTime"] = i
                elif h in ("作答时间", "answertime"):
                    col_map["answerTime"] = i
                elif h in ("采分点", "scoringpoints"):
                    col_map["scoringPoints"] = i
                elif h in ("得分关键词", "scoringkeywords"):
                    col_map["scoringKeywords"] = i
                elif h in ("扣分关键词", "deductingkeywords"):
                    col_map["deductingKeywords"] = i
                elif h in ("加分关键词", "bonuskeywords"):
                    col_map["bonusKeywords"] = i

            if "stem" not in col_map:
                raise HTTPException(status_code=400, detail="Excel 缺少题干列")

            for row in rows[1:]:
                try:
                    stem = str(row[col_map["stem"]]).strip() if row[col_map["stem"]] else ""
                    if not stem:
                        failed_count += 1
                        continue

                    # 解析关键词
                    keywords = {"scoring": [], "deducting": [], "bonus": []}
                    for kw_type, kw_col in [("scoring", "scoringKeywords"), ("deducting", "deductingKeywords"), ("bonus", "bonusKeywords")]:
                        if kw_col in col_map and row[col_map[kw_col]]:
                            val = str(row[col_map[kw_col]]).strip()
                            if val.startswith("["):
                                keywords[kw_type] = json.loads(val)
                            else:
                                keywords[kw_type] = [w.strip() for w in val.split(",") if w.strip()]

                    # 解析采分点
                    scoring_points = []
                    if "scoringPoints" in col_map and row[col_map["scoringPoints"]]:
                        val = str(row[col_map["scoringPoints"]]).strip()
                        if val.startswith("["):
                            scoring_points = json.loads(val)

                    question = {
                        "id": f"q_{uuid.uuid4().hex[:8]}",
                        "stem": stem,
                        "dimension": str(row[col_map.get("dimension", -1)]).strip() if col_map.get("dimension") is not None and row[col_map["dimension"]] else "analysis",
                        "province": str(row[col_map.get("province", -1)]).strip() if col_map.get("province") is not None and row[col_map["province"]] else "national",
                        "prepTime": int(row[col_map["prepTime"]]) if "prepTime" in col_map and row[col_map["prepTime"]] else 90,
                        "answerTime": int(row[col_map["answerTime"]]) if "answerTime" in col_map and row[col_map["answerTime"]] else 180,
                        "scoringPoints": scoring_points,
                        "keywords": keywords
                    }
                    mock_db["questions"].append(question)
                    imported_count += 1
                except Exception:
                    failed_count += 1
            wb.close()
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式，请上传 .json 或 .xlsx 文件")

        if imported_count > 0:
            save_db(mock_db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")

    return {"imported": imported_count, "failed": failed_count}

if __name__ == "__main__":
    import uvicorn
    logger.info("[START] API server starting...")
    logger.info(f"[URL] http://localhost:8050")
    uvicorn.run(app, host="127.0.0.1", port=8050)