"""Seed the SQLite database with initial questions and a default admin user"""
import json
import logging
import os
import sys

# Ensure we can import from the backend root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import engine, SessionLocal, Base
from app.models.entities import User, Question
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)


def seed():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Seed tables ready", extra={"event": "seed.tables.ready"})

    db = SessionLocal()
    try:
        # ----- Default admin user -----
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                full_name="管理员",
                email="admin@example.com",
                province="national",
                role="admin",
            )
            db.add(admin)
            logger.info("Seed default admin created", extra={"event": "seed.admin.created", "username": "admin"})
        else:
            logger.info("Seed default admin skipped", extra={"event": "seed.admin.skipped", "username": "admin"})

        # ----- Seed questions from seed_questions.json -----
        json_path = os.path.join(os.path.dirname(__file__), "seed_questions.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                questions = json.load(f)
            inserted = 0
            for q in questions:
                qid = q.get("id") or ""
                if qid and db.query(Question).filter(Question.id == qid).first():
                    continue
                row = Question(
                    id=qid,
                    stem=q.get("stem", ""),
                    dimension=q.get("dimension", "analysis"),
                    province=q.get("province", "national"),
                    prep_time=q.get("prepTime", 90),
                    answer_time=q.get("answerTime", 180),
                    scoring_points=q.get("scoringPoints", []),
                    keywords=q.get("keywords", {"scoring": [], "deducting": [], "bonus": []}),
                )
                db.add(row)
                inserted += 1
            db.commit()
            logger.info(
                "Seed questions inserted",
                extra={"event": "seed.questions.inserted", "inserted": inserted, "source": "seed_questions.json"},
            )
        else:
            logger.info(
                "Seed questions skipped",
                extra={"event": "seed.questions.skipped", "reason": "file_not_found", "source": "seed_questions.json"},
            )

        db.commit()
        logger.info("Seed completed", extra={"event": "seed.completed"})

    except Exception as e:
        db.rollback()
        logger.exception("Seed failed", extra={"event": "seed.failed", "error": str(e)})
        raise
    finally:
        db.close()


if __name__ == "__main__":
    configure_logging(settings)
    seed()
