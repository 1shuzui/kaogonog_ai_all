import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, validate_production_settings
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.db.schema import ensure_runtime_schema
from app.db.session import engine, Base
from app.api.v1 import api_router

# ── logging ──────────────────────────────────────────────────────────────────
configure_logging(settings)
logger = logging.getLogger(__name__)


# ── app factory ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="公务员面试练习平台 API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(",") if settings.allowed_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware, access_log_enabled=settings.log_access_enabled)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if settings.app_env.lower() == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

# ── init DB + seed on first run ───────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    validate_production_settings()
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema(engine)
    logger.info(
        "Database tables ready",
        extra={
            "event": "app.startup.database_ready",
            "database_driver": settings.database_url.split(":")[0],
            "app_env": settings.app_env,
        },
    )
    # Auto-seed if DB is empty
    try:
        from seed import seed
        from app.db.session import SessionLocal
        from app.models.entities import Question
        from app.services.question_service import sync_curated_question_assets
        db = SessionLocal()
        count = db.query(Question).count()
        if count == 0:
            logger.info("Empty database, running seed", extra={"event": "app.startup.seed_start"})
            seed()
            count = db.query(Question).count()
        sync_result = sync_curated_question_assets(db)
        if sync_result.get("synced") or sync_result.get("updated"):
            logger.info(
                "Curated question assets synced: +%s new, %s updated",
                sync_result.get("synced", 0),
                sync_result.get("updated", 0),
                extra={
                    "event": "question.assets.synced",
                    "synced": sync_result.get("synced", 0),
                    "updated": sync_result.get("updated", 0),
                },
            )
        db.close()
    except Exception as e:
        logger.warning("Seed skipped", extra={"event": "app.startup.seed_skipped", "error": str(e)}, exc_info=True)


# ── routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router)


# ── health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/")
def root():
    return {"message": "Civil Interview API", "docs": "/docs"}


# ── run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8050, reload=True)
