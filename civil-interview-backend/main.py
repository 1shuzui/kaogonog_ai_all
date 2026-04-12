"""前端兼容后端。

这个服务保留 `civil-interview-frontend` 现有接口约定，
底层直接复用 `ai_gongwu_backend` 的题库、评分引擎和测评落库能力。
"""

from __future__ import annotations

import json
import os
import random
import secrets
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_BACKEND_ROOT = REPO_ROOT / "ai_gongwu_backend"
if str(AI_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_BACKEND_ROOT))

from app.core.config import settings as engine_settings
from app.core.database import SessionLocal, init_database
from app.models.schemas import EvaluationResult, QuestionDefinition
from app.services.evaluation_store import EvaluationStore
from app.services.flow import InterviewFlowService
from app.services.llm.client import LLMClient
from app.services.media.video_processor import process_audio, process_video
from app.services.question_bank import QuestionBank, QuestionNotFoundError


APP_ROOT = Path(__file__).resolve().parent
STATE_ROOT = APP_ROOT / "storage"
UPLOAD_ROOT = STATE_ROOT / "uploads"
CUSTOM_QUESTION_STATE_PATH = STATE_ROOT / "custom_questions.json"
SESSION_STATE_PATH = STATE_ROOT / "exam_sessions.json"
USER_STATE_PATH = STATE_ROOT / "users.json"
CUSTOM_QUESTION_MIRROR_DIR = AI_BACKEND_ROOT / "assets" / "questions" / "custom_frontend"

TOKEN_STORE: dict[str, str] = {}

FRONTEND_DIMENSIONS = {
    "legal": "法治思维",
    "practical": "实务落地",
    "logic": "逻辑结构",
    "expression": "语言表达",
    "analysis": "综合分析",
    "emergency": "应急应变",
}

PROVINCE_OPTIONS = [
    {"code": "national", "name": "国考"},
    {"code": "beijing", "name": "北京"},
    {"code": "shanghai", "name": "上海"},
    {"code": "guangdong", "name": "广东"},
    {"code": "jiangsu", "name": "江苏"},
    {"code": "zhejiang", "name": "浙江"},
    {"code": "shandong", "name": "山东"},
    {"code": "sichuan", "name": "四川"},
    {"code": "hubei", "name": "湖北"},
    {"code": "hunan", "name": "湖南"},
    {"code": "henan", "name": "河南"},
    {"code": "hebei", "name": "河北"},
    {"code": "fujian", "name": "福建"},
    {"code": "anhui", "name": "安徽"},
    {"code": "liaoning", "name": "辽宁"},
    {"code": "shaanxi", "name": "陕西"},
]

PROVINCE_TO_CODE = {item["name"]: item["code"] for item in PROVINCE_OPTIONS}
PROVINCE_TO_NAME = {item["code"]: item["name"] for item in PROVINCE_OPTIONS}
PROVINCE_TO_NAME["national"] = "全国"

POSITION_OPTIONS = [
    {"code": "tax", "name": "税务系统"},
    {"code": "customs", "name": "海关系统"},
    {"code": "police", "name": "公安系统"},
    {"code": "court", "name": "法院系统"},
    {"code": "procurate", "name": "检察系统"},
    {"code": "market", "name": "市场监管"},
    {"code": "general", "name": "综合管理"},
    {"code": "township", "name": "乡镇基层"},
    {"code": "finance", "name": "银保监会"},
    {"code": "diplomacy", "name": "外交系统"},
]

POSITION_FOCUS = {
    "tax": {
        "coreFocus": [
            {"name": "依法征管", "weight": 35, "desc": "强调依法治税、程序规范与风险控制。"},
            {"name": "纳税服务", "weight": 35, "desc": "兼顾办税便利度、群众体验与政策落地。"},
            {"name": "协调沟通", "weight": 30, "desc": "处理投诉、争议和跨部门协同。"},
        ],
        "highFreqTypes": [
            {"type": "综合分析", "frequency": "高", "example": "围绕税费优惠政策落实谈看法。"},
            {"type": "情景应变", "frequency": "高", "example": "纳税人情绪激动投诉窗口服务，如何处理？"},
        ],
        "hotTopics": ["数字化办税", "税费优惠精准推送", "营商环境优化"],
        "strategy": ["多用依法行政与服务并重的表达", "准备投诉处置与舆情回应框架", "熟悉基层征管场景"],
    },
    "township": {
        "coreFocus": [
            {"name": "群众工作", "weight": 40, "desc": "强调走访、倾听诉求与矛盾调解。"},
            {"name": "基层执行", "weight": 35, "desc": "强调政策落地、组织协调和闭环推进。"},
            {"name": "应急处置", "weight": 25, "desc": "面对突发舆情和现场事件的快速响应。"},
        ],
        "highFreqTypes": [
            {"type": "综合分析", "frequency": "高", "example": "围绕基层治理现代化谈理解。"},
            {"type": "组织管理", "frequency": "中", "example": "如何组织一次民情走访和矛盾排查？"},
        ],
        "hotTopics": ["乡村振兴", "基层减负", "网格治理", "农村人居环境整治"],
        "strategy": ["多写群众视角与基层执行细节", "准备走访调研和群众沟通框架", "回答中注意可操作性"],
    },
}

POSITION_DIMENSION_HINTS = {
    "tax": ["legal", "practical", "analysis"],
    "customs": ["legal", "analysis", "emergency"],
    "police": ["emergency", "legal", "practical"],
    "court": ["legal", "logic", "expression"],
    "procurate": ["legal", "analysis", "logic"],
    "market": ["practical", "analysis", "legal"],
    "general": ["analysis", "logic", "expression"],
    "township": ["practical", "analysis", "emergency"],
    "finance": ["analysis", "logic", "legal"],
    "diplomacy": ["expression", "analysis", "logic"],
}


class KeywordGroups(BaseModel):
    scoring: list[str] = Field(default_factory=list)
    deducting: list[str] = Field(default_factory=list)
    bonus: list[str] = Field(default_factory=list)


class ScoringPoint(BaseModel):
    content: str
    score: float = Field(default=5.0, ge=0.0)


class FrontendQuestionPayload(BaseModel):
    id: str | None = None
    stem: str
    dimension: str = "analysis"
    province: str = "national"
    prepTime: int = 90
    answerTime: int = 180
    scoringPoints: list[ScoringPoint] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    keywords: KeywordGroups = Field(default_factory=KeywordGroups)


class StartExamPayload(BaseModel):
    questionIds: list[str] = Field(default_factory=list)


class EvaluatePayload(BaseModel):
    questionId: str
    transcript: str
    examId: str | None = None


class RegisterPayload(BaseModel):
    username: str
    password: str
    email: str | None = None
    full_name: str | None = None


class ProfilePayload(BaseModel):
    full_name: str | None = None
    email: str | None = None


class PasswordPayload(BaseModel):
    oldPassword: str | None = None
    newPassword: str


class PreferencesPayload(BaseModel):
    defaultPrepTime: int = 90
    defaultAnswerTime: int = 180
    enableVideo: bool = True


class FocusPayload(BaseModel):
    province: str
    position: str


class QuestionGenerationPayload(BaseModel):
    province: str = "national"
    position: str = "general"
    count: int = 5


class TrainingPayload(BaseModel):
    dimension: str
    count: int = 3


def ensure_runtime_dirs() -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    CUSTOM_QUESTION_MIRROR_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normalize_province_code(value: str | None) -> str:
    if not value:
        return "national"
    lowered = value.strip().lower()
    if lowered in PROVINCE_TO_NAME:
        return lowered
    return PROVINCE_TO_CODE.get(value.strip(), "national")


def province_display_name(code: str) -> str:
    return PROVINCE_TO_NAME.get(code, "全国")


def classify_question_dimension(question: QuestionDefinition) -> str:
    haystack = " ".join(
        [
            question.type,
            question.question,
            " ".join(question.tags),
            " ".join(question.coreKeywords),
            " ".join(question.strongKeywords),
        ]
    )
    rules = [
        ("emergency", ("应急", "应变", "突发", "舆情")),
        ("legal", ("法治", "法律", "执法", "依法", "合规")),
        ("logic", ("逻辑", "结构", "论证")),
        ("expression", ("表达", "语言", "沟通", "发言")),
        ("practical", ("组织", "执行", "基层", "服务", "落实", "协同", "实务")),
    ]
    for key, keywords in rules:
        if any(keyword in haystack for keyword in keywords):
            return key
    return "analysis"


def make_frontend_question_id() -> str:
    return f"FE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3)}"


def question_definition_to_frontend(question: QuestionDefinition) -> dict[str, Any]:
    return {
        "id": question.id,
        "stem": question.question,
        "dimension": classify_question_dimension(question),
        "province": normalize_province_code(question.province),
        "prepTime": 90,
        "answerTime": 180,
        "scoringPoints": [
            {"content": item.name, "score": item.score}
            for item in question.dimensions
        ],
        "synonyms": list(dict.fromkeys(question.weakKeywords)),
        "keywords": {
            "scoring": list(dict.fromkeys(question.coreKeywords + question.strongKeywords)),
            "deducting": question.penaltyKeywords,
            "bonus": question.bonusKeywords,
        },
        "source": "builtin",
        "readonly": True,
    }


def normalize_frontend_question(payload: FrontendQuestionPayload, *, question_id: str | None = None) -> dict[str, Any]:
    dimension = payload.dimension if payload.dimension in FRONTEND_DIMENSIONS else "analysis"
    scoring_points = [
        {
            "content": (point.content or f"采分点{index + 1}").strip(),
            "score": max(float(point.score), 0.0),
        }
        for index, point in enumerate(payload.scoringPoints or [])
    ]
    if not scoring_points:
        scoring_points = [
            {
                "content": FRONTEND_DIMENSIONS[dimension],
                "score": 20.0,
            }
        ]

    return {
        "id": question_id or payload.id or make_frontend_question_id(),
        "stem": payload.stem.strip(),
        "dimension": dimension,
        "province": normalize_province_code(payload.province),
        "prepTime": max(payload.prepTime, 30),
        "answerTime": max(payload.answerTime, 60),
        "scoringPoints": scoring_points,
        "synonyms": [item.strip() for item in payload.synonyms if item.strip()],
        "keywords": {
            "scoring": [item.strip() for item in payload.keywords.scoring if item.strip()],
            "deducting": [item.strip() for item in payload.keywords.deducting if item.strip()],
            "bonus": [item.strip() for item in payload.keywords.bonus if item.strip()],
        },
        "source": "custom",
        "readonly": False,
    }


def frontend_question_to_engine_payload(question: dict[str, Any]) -> dict[str, Any]:
    dimensions = []
    for index, point in enumerate(question["scoringPoints"]):
        point_name = str(point.get("content") or f"采分点{index + 1}").strip()
        if not point_name:
            point_name = f"采分点{index + 1}"
        dimensions.append(
            {
                "name": point_name[:60],
                "score": max(float(point.get("score") or 0.0), 0.0),
            }
        )

    full_score = round(sum(item["score"] for item in dimensions), 1) or 20.0
    scoring_keywords = question["keywords"]["scoring"]
    bonus_keywords = question["keywords"]["bonus"]
    deducting_keywords = question["keywords"]["deducting"]

    return {
        "id": question["id"],
        "type": FRONTEND_DIMENSIONS.get(question["dimension"], "综合分析"),
        "province": province_display_name(question["province"]),
        "fullScore": full_score,
        "question": question["stem"],
        "dimensions": dimensions,
        "coreKeywords": scoring_keywords,
        "strongKeywords": question.get("synonyms", []),
        "weakKeywords": [],
        "bonusKeywords": bonus_keywords,
        "penaltyKeywords": deducting_keywords,
        "scoringCriteria": [f"{item['name']}（{item['score']}分）" for item in dimensions],
        "deductionRules": [f"若出现“{item}”等表达，需重点核查扣分原因。" for item in deducting_keywords],
        "sourceDocument": "civil-interview-frontend",
        "referenceAnswer": "",
        "tags": [FRONTEND_DIMENSIONS.get(question["dimension"], "综合分析"), province_display_name(question["province"])],
    }


def custom_question_asset_path(question_id: str) -> Path:
    return CUSTOM_QUESTION_MIRROR_DIR / f"{question_id}.json"


def load_custom_questions() -> dict[str, dict[str, Any]]:
    raw = load_json(CUSTOM_QUESTION_STATE_PATH, {"items": []})
    items = {}
    for item in raw.get("items", []):
        items[item["id"]] = item
    return items


def save_custom_questions(questions: dict[str, dict[str, Any]]) -> None:
    ordered_items = [questions[key] for key in sorted(questions)]
    save_json(CUSTOM_QUESTION_STATE_PATH, {"items": ordered_items})


def sync_custom_question_asset(question: dict[str, Any]) -> None:
    asset_path = custom_question_asset_path(question["id"])
    save_json(asset_path, frontend_question_to_engine_payload(question))


def delete_custom_question_asset(question_id: str) -> None:
    asset_path = custom_question_asset_path(question_id)
    if asset_path.exists():
        asset_path.unlink()


def build_question_bank() -> QuestionBank:
    return QuestionBank(engine_settings.QUESTION_DB_PATH)


def build_flow_service() -> InterviewFlowService:
    llm_client = LLMClient()
    if os.getenv("COMPAT_FORCE_RULE_BASED", "").lower() in {"1", "true", "yes"}:
        llm_client.client = None
    return InterviewFlowService(
        llm_client=llm_client,
        question_bank=build_question_bank(),
        evaluation_store=EvaluationStore(session_factory=SessionLocal),
    )


def load_exam_sessions() -> dict[str, dict[str, Any]]:
    raw = load_json(SESSION_STATE_PATH, {"items": []})
    return {item["examId"]: item for item in raw.get("items", [])}


def save_exam_sessions(sessions: dict[str, dict[str, Any]]) -> None:
    ordered_items = [sessions[key] for key in sorted(sessions)]
    save_json(SESSION_STATE_PATH, {"items": ordered_items})


def create_exam_session(question_ids: list[str]) -> dict[str, Any]:
    sessions = load_exam_sessions()
    exam_id = f"exam_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(3)}"
    session = {
        "examId": exam_id,
        "questionIds": question_ids,
        "recordIds": [],
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
        "completedAt": None,
        "uploads": [],
    }
    sessions[exam_id] = session
    save_exam_sessions(sessions)
    return session


def update_exam_session(exam_id: str, updater) -> dict[str, Any]:
    sessions = load_exam_sessions()
    session = sessions.get(exam_id)
    if session is None:
        session = {
            "examId": exam_id,
            "questionIds": [],
            "recordIds": [],
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "completedAt": None,
            "uploads": [],
        }
        sessions[exam_id] = session

    updater(session)
    session["updatedAt"] = now_iso()
    save_exam_sessions(sessions)
    return session


def append_record_to_exam(exam_id: str, record_id: int, question_id: str) -> None:
    def updater(session: dict[str, Any]) -> None:
        if question_id not in session["questionIds"]:
            session["questionIds"].append(question_id)
        if record_id not in session["recordIds"]:
            session["recordIds"].append(record_id)

    update_exam_session(exam_id, updater)


def add_upload_to_exam(exam_id: str, filename: str) -> None:
    def updater(session: dict[str, Any]) -> None:
        session["uploads"].append({"filename": filename, "uploadedAt": now_iso()})

    update_exam_session(exam_id, updater)


def mark_exam_completed(exam_id: str) -> dict[str, Any]:
    return update_exam_session(exam_id, lambda session: session.update({"completedAt": now_iso()}))


def load_users() -> dict[str, dict[str, Any]]:
    raw = load_json(USER_STATE_PATH, {"items": []})
    users = {}
    for item in raw.get("items", []):
        users[item["username"]] = item
    return users


def save_users(users: dict[str, dict[str, Any]]) -> None:
    ordered_items = [users[key] for key in sorted(users)]
    save_json(USER_STATE_PATH, {"items": ordered_items})


def ensure_user(username: str, password: str) -> dict[str, Any]:
    users = load_users()
    user = users.get(username)
    if user is None:
        user = {
            "username": username,
            "password": password,
            "email": "",
            "full_name": username,
            "province": "national",
            "preferences": {
                "defaultPrepTime": 90,
                "defaultAnswerTime": 180,
                "enableVideo": True,
            },
        }
        users[username] = user
        save_users(users)
    return user


def build_token(username: str) -> str:
    token = secrets.token_urlsafe(24)
    TOKEN_STORE[token] = username
    return token


def require_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供登录令牌。")

    token = authorization.split(" ", 1)[1].strip()
    username = TOKEN_STORE.get(token)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录令牌已失效。")

    users = load_users()
    user = users.get(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在。")
    return user


def list_all_frontend_questions() -> list[dict[str, Any]]:
    custom_questions = load_custom_questions()
    question_bank = build_question_bank()
    merged = {
        question.id: question_definition_to_frontend(question)
        for question in question_bank.list_questions()
    }
    merged.update(custom_questions)
    return [merged[key] for key in sorted(merged)]


def get_frontend_question(question_id: str) -> dict[str, Any]:
    custom_questions = load_custom_questions()
    if question_id in custom_questions:
        return custom_questions[question_id]

    question_bank = build_question_bank()
    try:
        return question_definition_to_frontend(question_bank.get_question(question_id))
    except QuestionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def get_engine_question(question_id: str) -> QuestionDefinition:
    try:
        return build_question_bank().get_question(question_id)
    except QuestionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def get_dimension_display_name(key: str) -> str:
    return FRONTEND_DIMENSIONS.get(key, key)


def build_frontend_result(result: EvaluationResult, question: QuestionDefinition) -> dict[str, Any]:
    scoring_matches = set(
        result.matched_keywords.get("core", [])
        + result.matched_keywords.get("strong", [])
        + result.matched_keywords.get("weak", [])
    )
    bonus_matches = set(result.matched_keywords.get("bonus", []))
    transcript = result.transcript

    dimensions = []
    for dimension in question.dimensions:
        lost_reasons = [
            item.reason
            for item in result.deduction_items
            if item.dimension == dimension.name
        ]
        dimensions.append(
            {
                "name": dimension.name,
                "score": round(result.dimension_scores.get(dimension.name, 0.0), 1),
                "maxScore": dimension.score,
                "lostReasons": lost_reasons,
            }
        )

    ai_comment = result.rationale or "系统已完成结构化评分。"
    if result.validation_notes:
        ai_comment = f"{ai_comment}\n校验说明：{'；'.join(result.validation_notes[:3])}"

    scoring_keywords = list(dict.fromkeys(question.coreKeywords + question.strongKeywords))
    return {
        "recordId": result.record_id,
        "questionId": question.id,
        "questionType": question.type,
        "totalScore": round(result.total_score, 1),
        "maxScore": question.fullScore,
        "aiComment": ai_comment,
        "dimensions": dimensions,
        "matchedKeywords": {
            "scoring": [
                {
                    "word": keyword,
                    "score": 1,
                    "inTranscript": keyword in transcript,
                    "matched": keyword in scoring_matches,
                }
                for keyword in scoring_keywords
            ],
            "deducting": [
                {
                    "word": keyword,
                    "penalty": 1,
                    "inTranscript": keyword in transcript,
                }
                for keyword in question.penaltyKeywords
            ],
            "bonus": [
                {
                    "word": keyword,
                    "bonus": 1,
                    "inTranscript": keyword in transcript,
                    "matched": keyword in bonus_matches,
                }
                for keyword in question.bonusKeywords
            ],
        },
        "highlightedTranscript": transcript,
        "transcript": transcript,
        "validationNotes": result.validation_notes,
        "source": result.source,
        "sourceFilename": result.source_filename,
    }


def compute_session_summary(
    session: dict[str, Any],
    evaluation_store: EvaluationStore,
) -> dict[str, Any] | None:
    if not session["recordIds"]:
        return None

    details = []
    for record_id in session["recordIds"]:
        detail = evaluation_store.get_record_detail(record_id)
        if detail is not None:
            details.append(detail)
    if not details:
        return None

    question_map = {
        detail.question_id: get_engine_question(detail.question_id)
        for detail in details
    }

    percentages = []
    category_scores: dict[str, list[float]] = {}
    for detail in details:
        question = question_map[detail.question_id]
        percent = round(detail.total_score / max(question.fullScore, 1.0) * 100, 1)
        percentages.append(percent)
        category_key = classify_question_dimension(question)
        category_scores.setdefault(category_key, []).append(percent)

    total_score = round(sum(percentages) / len(percentages), 1)
    ordered_categories = []
    for category_key in sorted(category_scores):
        scores = category_scores[category_key]
        ordered_categories.append(
            {
                "name": get_dimension_display_name(category_key),
                "score": round(sum(scores) / len(scores), 1),
                "maxScore": 100,
            }
        )

    first_question = question_map[details[0].question_id]
    question_summary = first_question.question
    if len(details) > 1:
        question_summary = f"{question_summary[:24]} 等 {len(details)} 题"

    completed_at = session.get("completedAt") or session.get("updatedAt") or session.get("createdAt")
    if total_score >= 90:
        grade = "A"
    elif total_score >= 75:
        grade = "B"
    elif total_score >= 60:
        grade = "C"
    else:
        grade = "D"

    return {
        "examId": session["examId"],
        "questionSummary": question_summary,
        "date": completed_at,
        "grade": grade,
        "totalScore": total_score,
        "maxScore": 100,
        "questionCount": len(details),
        "dimensions": ordered_categories,
        "province": normalize_province_code(first_question.province),
    }


def parse_uploaded_json(file: UploadFile) -> list[dict[str, Any]]:
    content = file.file.read()
    try:
        raw = json.loads(content.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="导入文件不是有效的 UTF-8 JSON。") from exc

    if isinstance(raw, dict) and isinstance(raw.get("questions"), list):
        return raw["questions"]
    if isinstance(raw, list):
        return raw
    raise HTTPException(status_code=400, detail="导入 JSON 必须是数组或包含 questions 数组的对象。")


def infer_media_suffix(upload: UploadFile, default_suffix: str = ".webm") -> str:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix:
        return suffix

    content_type = (upload.content_type or "").lower()
    mapping = {
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/webm": ".webm",
        "video/webm": ".webm",
        "video/mp4": ".mp4",
    }
    return mapping.get(content_type, default_suffix)


def choose_media_parser(upload: UploadFile, suffix: str):
    content_type = (upload.content_type or "").lower()
    if content_type.startswith("video/"):
        return process_video
    if content_type.startswith("audio/"):
        return process_audio
    if suffix in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
        return process_video
    return process_audio


app = FastAPI(
    title="Civil Interview Compatibility Backend",
    version="1.2.0",
    description="对 civil-interview-frontend 暴露旧接口，对接 ai_gongwu_backend 评分引擎。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    ensure_runtime_dirs()
    init_database()


@app.post("/token")
async def login(username: str = Form(...), password: str = Form(...)) -> dict[str, Any]:
    if not username.strip() or not password.strip():
        raise HTTPException(status_code=400, detail="用户名和密码不能为空。")

    users = load_users()
    user = users.get(username)
    if user is None:
        user = ensure_user(username.strip(), password.strip())
    elif user.get("password") and user["password"] != password:
        raise HTTPException(status_code=401, detail="用户名或密码错误。")

    token = build_token(username.strip())
    return {"access_token": token, "token_type": "bearer"}


@app.post("/register")
async def register(payload: RegisterPayload) -> dict[str, Any]:
    users = load_users()
    if payload.username in users:
        raise HTTPException(status_code=400, detail="用户名已存在。")

    users[payload.username] = {
        "username": payload.username,
        "password": payload.password,
        "email": payload.email or "",
        "full_name": payload.full_name or payload.username,
        "province": "national",
        "preferences": {
            "defaultPrepTime": 90,
            "defaultAnswerTime": 180,
            "enableVideo": True,
        },
    }
    save_users(users)
    return {"success": True}


@app.get("/user/info")
async def get_user_info(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return {
        "id": user["username"],
        "name": user.get("full_name") or user["username"],
        "avatar": "",
        "province": user.get("province", "national"),
    }


@app.get("/user/me")
async def get_user_me(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return {"username": user["username"], "email": user.get("email", ""), "full_name": user.get("full_name", user["username"])}


@app.put("/user/profile")
async def update_user_profile(
    payload: ProfilePayload,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    users = load_users()
    record = users[user["username"]]
    record["full_name"] = payload.full_name or record.get("full_name") or user["username"]
    record["email"] = payload.email or record.get("email", "")
    save_users(users)
    return {"success": True}


@app.put("/user/password")
async def update_password(
    payload: PasswordPayload,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    users = load_users()
    users[user["username"]]["password"] = payload.newPassword
    save_users(users)
    return {"success": True}


@app.put("/user/preferences")
async def update_preferences(
    payload: PreferencesPayload,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    users = load_users()
    users[user["username"]]["preferences"] = payload.model_dump()
    save_users(users)
    return {"success": True}


@app.get("/user/provinces")
async def list_provinces() -> list[dict[str, str]]:
    return PROVINCE_OPTIONS


@app.get("/positions")
async def list_positions() -> list[dict[str, str]]:
    return POSITION_OPTIONS


@app.get("/questions/random")
async def get_random_questions(
    province: str = Query(default=""),
    dimension: str = Query(default=""),
    count: int = Query(default=5, ge=1, le=20),
) -> list[dict[str, Any]]:
    questions = list_all_frontend_questions()
    normalized_province = normalize_province_code(province)
    if province:
        questions = [item for item in questions if item["province"] == normalized_province]
    if dimension:
        questions = [item for item in questions if item["dimension"] == dimension]
    if not questions:
        questions = list_all_frontend_questions()
    random.shuffle(questions)
    return questions[:count]


@app.get("/questions")
async def list_questions(
    keyword: str = Query(default=""),
    dimension: str = Query(default=""),
    province: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    current: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    questions = list_all_frontend_questions()
    effective_page = page if page > 1 else current
    normalized_province = normalize_province_code(province)

    if keyword.strip():
        lowered_keyword = keyword.strip().lower()
        questions = [item for item in questions if lowered_keyword in item["stem"].lower()]
    if dimension:
        questions = [item for item in questions if item["dimension"] == dimension]
    if province:
        questions = [item for item in questions if item["province"] == normalized_province]

    total = len(questions)
    start = (effective_page - 1) * pageSize
    end = start + pageSize
    return {"list": questions[start:end], "total": total}


@app.get("/questions/{question_id}")
async def get_question(question_id: str) -> dict[str, Any]:
    return get_frontend_question(question_id)


@app.post("/questions")
async def create_question(payload: FrontendQuestionPayload) -> dict[str, Any]:
    questions = load_custom_questions()
    normalized = normalize_frontend_question(payload)

    if normalized["id"] in questions:
        raise HTTPException(status_code=400, detail=f"题目 ID 已存在: {normalized['id']}")
    try:
        build_question_bank().get_question(normalized["id"])
    except QuestionNotFoundError:
        pass
    else:
        raise HTTPException(status_code=400, detail=f"题目 ID 已存在: {normalized['id']}")

    questions[normalized["id"]] = normalized
    save_custom_questions(questions)
    sync_custom_question_asset(normalized)
    return normalized


@app.put("/questions/{question_id}")
async def update_question(question_id: str, payload: FrontendQuestionPayload) -> dict[str, Any]:
    questions = load_custom_questions()
    if question_id not in questions:
        raise HTTPException(status_code=400, detail="内置题库当前为只读，不支持直接修改。")

    normalized = normalize_frontend_question(payload, question_id=question_id)
    questions[question_id] = normalized
    save_custom_questions(questions)
    sync_custom_question_asset(normalized)
    return normalized


@app.delete("/questions/{question_id}")
async def delete_question(question_id: str) -> dict[str, Any]:
    questions = load_custom_questions()
    if question_id not in questions:
        raise HTTPException(status_code=400, detail="内置题库当前为只读，不支持直接删除。")

    del questions[question_id]
    save_custom_questions(questions)
    delete_custom_question_asset(question_id)
    return {"success": True}


@app.post("/questions/import")
async def import_questions(file: UploadFile = File(...)) -> dict[str, Any]:
    imported_items = parse_uploaded_json(file)
    custom_questions = load_custom_questions()
    imported_count = 0
    failed = 0

    for raw_item in imported_items:
        try:
            payload = FrontendQuestionPayload.model_validate(raw_item)
            normalized = normalize_frontend_question(payload)
            if normalized["id"] in custom_questions:
                raise ValueError(f"重复题目 ID: {normalized['id']}")
            try:
                build_question_bank().get_question(normalized["id"])
            except QuestionNotFoundError:
                pass
            else:
                raise ValueError(f"重复题目 ID: {normalized['id']}")

            custom_questions[normalized["id"]] = normalized
            sync_custom_question_asset(normalized)
            imported_count += 1
        except Exception:
            failed += 1

    save_custom_questions(custom_questions)
    return {"imported": imported_count, "failed": failed}


@app.post("/exam/start")
async def start_exam(payload: StartExamPayload) -> dict[str, Any]:
    if not payload.questionIds:
        raise HTTPException(status_code=400, detail="请至少选择一道题目。")
    session = create_exam_session(payload.questionIds)
    return {"examId": session["examId"]}


@app.post("/exam/{exam_id}/upload")
async def upload_recording(exam_id: str, recording: UploadFile = File(...)) -> dict[str, Any]:
    suffix = infer_media_suffix(recording)
    filename = f"{exam_id}_{datetime.now().strftime('%H%M%S')}{suffix}"
    file_path = UPLOAD_ROOT / filename
    with file_path.open("wb") as handle:
        shutil.copyfileobj(recording.file, handle)
    add_upload_to_exam(exam_id, filename)
    return {"success": True, "filename": filename}


@app.post("/exam/{exam_id}/complete")
async def complete_exam(exam_id: str) -> dict[str, Any]:
    session = mark_exam_completed(exam_id)
    return {"success": True, "examId": session["examId"], "completedAt": session["completedAt"]}


@app.post("/scoring/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)) -> dict[str, Any]:
    suffix = infer_media_suffix(audio)
    parser = choose_media_parser(audio, suffix)

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            temp_path = handle.name
            shutil.copyfileobj(audio.file, handle)
        extraction = parser(temp_path)
        return {"transcript": extraction.transcript}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"转写失败: {exc}") from exc
    finally:
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink(missing_ok=True)


@app.post("/scoring/evaluate")
async def evaluate_answer(payload: EvaluatePayload) -> dict[str, Any]:
    flow_service = build_flow_service()
    try:
        result = flow_service.evaluate_text_only(
            question_id=payload.questionId,
            text_content=payload.transcript,
            source_filename=f"{payload.examId or 'frontend'}-{payload.questionId}.txt",
        )
    except QuestionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"评分失败: {exc}") from exc

    if payload.examId and result.record_id is not None:
        append_record_to_exam(payload.examId, result.record_id, payload.questionId)

    question = get_engine_question(payload.questionId)
    return build_frontend_result(result, question)


@app.get("/scoring/result/{exam_id}/{question_id:path}")
async def get_scoring_result(exam_id: str, question_id: str = "") -> dict[str, Any]:
    sessions = load_exam_sessions()
    session = sessions.get(exam_id)
    if session is None or not session["recordIds"]:
        raise HTTPException(status_code=404, detail="对应的考试结果不存在。")

    evaluation_store = EvaluationStore(session_factory=SessionLocal)
    target_record = None
    for record_id in reversed(session["recordIds"]):
        detail = evaluation_store.get_record_detail(record_id)
        if detail is None:
            continue
        if question_id and detail.question_id != question_id:
            continue
        target_record = detail
        break

    if target_record is None:
        raise HTTPException(status_code=404, detail="未找到对应题目的评分结果。")

    question = get_engine_question(target_record.question_id)
    return build_frontend_result(target_record.final_result, question)


@app.get("/history")
async def get_history(
    province: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    current: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    effective_page = page if page > 1 else current
    normalized_province = normalize_province_code(province)
    sessions = load_exam_sessions()
    evaluation_store = EvaluationStore(session_factory=SessionLocal)

    items = []
    for session in sessions.values():
        summary = compute_session_summary(session, evaluation_store)
        if summary is None:
            continue
        if province and summary["province"] != normalized_province:
            continue
        items.append(summary)

    items.sort(key=lambda item: item["date"], reverse=True)
    total = len(items)
    start = (effective_page - 1) * pageSize
    end = start + pageSize
    return {"list": items[start:end], "total": total}


@app.get("/history/stats")
async def get_history_stats() -> dict[str, Any]:
    sessions = load_exam_sessions()
    evaluation_store = EvaluationStore(session_factory=SessionLocal)
    summaries = [
        compute_session_summary(session, evaluation_store)
        for session in sessions.values()
    ]
    summaries = [item for item in summaries if item is not None]
    if not summaries:
        return {
            "totalExams": 0,
            "avgScore": 0,
            "bestScore": 0,
            "weakestDimension": "",
            "dimensionAverages": [],
        }

    dimension_scores: dict[str, list[float]] = {}
    for summary in summaries:
        for item in summary["dimensions"]:
            dimension_scores.setdefault(item["name"], []).append(item["score"])

    dimension_averages = [
        {
            "name": name,
            "avg": round(sum(scores) / len(scores), 1),
            "maxScore": 100,
        }
        for name, scores in sorted(dimension_scores.items())
    ]
    weakest_dimension = min(dimension_averages, key=lambda item: item["avg"])["name"] if dimension_averages else ""

    return {
        "totalExams": len(summaries),
        "avgScore": round(sum(item["totalScore"] for item in summaries) / len(summaries), 1),
        "bestScore": max(item["totalScore"] for item in summaries),
        "weakestDimension": weakest_dimension,
        "dimensionAverages": dimension_averages,
    }


@app.get("/history/trend")
async def get_history_trend(days: int = Query(default=30, ge=1, le=365)) -> list[dict[str, Any]]:
    del days
    sessions = load_exam_sessions()
    evaluation_store = EvaluationStore(session_factory=SessionLocal)
    summaries = [
        compute_session_summary(session, evaluation_store)
        for session in sessions.values()
    ]
    summaries = [item for item in summaries if item is not None]
    summaries.sort(key=lambda item: item["date"])
    return [{"date": item["date"], "score": item["totalScore"]} for item in summaries[-30:]]


@app.get("/history/{exam_id}")
async def get_history_detail(exam_id: str) -> dict[str, Any]:
    sessions = load_exam_sessions()
    session = sessions.get(exam_id)
    if session is None:
        raise HTTPException(status_code=404, detail="考试记录不存在。")

    evaluation_store = EvaluationStore(session_factory=SessionLocal)
    summary = compute_session_summary(session, evaluation_store)
    if summary is None:
        raise HTTPException(status_code=404, detail="考试记录尚无评分结果。")

    records = []
    for record_id in session["recordIds"]:
        detail = evaluation_store.get_record_detail(record_id)
        if detail is None:
            continue
        question = get_engine_question(detail.question_id)
        records.append(build_frontend_result(detail.final_result, question))
    return {"summary": summary, "records": records}


@app.post("/targeted/focus")
async def get_focus_analysis(payload: FocusPayload) -> dict[str, Any]:
    base = POSITION_FOCUS.get(payload.position, POSITION_FOCUS["township"])
    strategy = list(base["strategy"])
    strategy.insert(0, f"优先准备 {province_display_name(normalize_province_code(payload.province))} 地区的政策化表达。")
    return {
        "coreFocus": base["coreFocus"],
        "highFreqTypes": base["highFreqTypes"],
        "hotTopics": base["hotTopics"],
        "strategy": strategy,
    }


@app.post("/questions/generate")
async def generate_questions(payload: QuestionGenerationPayload) -> list[dict[str, Any]]:
    preferred_dimensions = POSITION_DIMENSION_HINTS.get(payload.position, ["analysis"])
    questions = list_all_frontend_questions()
    province = normalize_province_code(payload.province)
    filtered = [item for item in questions if item["province"] == province]
    if not filtered:
        filtered = questions

    priority = [item for item in filtered if item["dimension"] in preferred_dimensions]
    random.shuffle(priority)
    if len(priority) < payload.count:
        remainder = [item for item in filtered if item["id"] not in {entry["id"] for entry in priority}]
        random.shuffle(remainder)
        priority.extend(remainder)
    return priority[: payload.count]


@app.post("/training/generate")
async def generate_training_questions(payload: TrainingPayload) -> list[dict[str, Any]]:
    questions = [item for item in list_all_frontend_questions() if item["dimension"] == payload.dimension]
    if not questions:
        questions = list_all_frontend_questions()
    random.shuffle(questions)
    return questions[: payload.count]


@app.get("/health")
async def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "civil-interview-backend",
        "questionCount": len(list_all_frontend_questions()),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8050)
