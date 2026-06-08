"""
这个脚本写入基础账号、套餐或示例数据；本地初始化可用它，现网执行前要先确认不会覆盖真实数据。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
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

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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
