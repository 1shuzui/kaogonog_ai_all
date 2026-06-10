"""
空库初始化脚本，用来给本地后端补齐默认管理员和少量示例题。

这个脚本会直接写数据库，不属于线上迁移工具；现网数据库已经有真实用户、订单和题库资产时不要把它当作修复命令执行。
需要初始化正式表结构时优先使用 `database_setup.py`，需要导入真实题库时走题库导入脚本，避免示例题污染统计分析。

@param: 无；执行时读取当前数据库配置和同目录 `seed_questions.json`。
@return: 无直接返回；执行结果通过标准输出和数据库记录体现。
@raises ImportError: 项目包路径、配置模块、ORM 模型或安全工具缺失时导入失败。
"""
import json
import os
import sys

# Ensure we can import from the backend root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import engine, SessionLocal, Base
from app.models.entities import User, Question
from app.core.config import settings
from app.core.security import get_password_hash


def seed():
    # Create all tables
    """
    创建缺失表并写入默认管理员和示例题，保证空库能完成一次本地冒烟测试。

    现网执行前需要确认 seed_questions.json 内容，避免把测试题误同步到真实题库。

    @param: 无；读取当前数据库配置和同目录 `seed_questions.json`。
    @return: 无返回值；通过 stdout 打印插入或跳过结果。
    @raises Exception: 建表、写入默认用户或写入 seed 题失败时回滚并上抛。
    """
    Base.metadata.create_all(bind=engine)
    print("[seed] Tables created (or already exist)")

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
            )
            db.add(admin)
            print("[seed] Created default user: admin / admin123")
        else:
            print("[seed] Admin user already exists, skipped")

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
            print(f"[seed] Inserted {inserted} question(s) from seed_questions.json")
        else:
            print("[seed] seed_questions.json not found, skipping questions")

        db.commit()
        print("[seed] Done!")

    except Exception as e:
        db.rollback()
        print(f"[seed] ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
