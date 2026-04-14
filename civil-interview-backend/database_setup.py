"""
一键部署脚本 — 初始化/重置 MySQL 数据库、建表、写入种子数据
用法:
    python database_setup.py              # 初始化（保留已有数据）
    python database_setup.py --reset      # 删库重建（危险！清除所有数据）
    python database_setup.py --seed-only  # 只写入种子数据（不建表）
    python database_setup.py --check      # 仅检查连接和表状态
"""
import argparse
import json
import os
import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
SEED_QUESTIONS_PATH = BASE_DIR / "seed_questions.json"
DB_JSON_PATH = BASE_DIR / "db.json"

# ── .env 解析 ─────────────────────────────────────────────────────────────────
# 支持两种格式:
#   1. DATABASE_URL=mysql+pymysql://user:pass@host:port/dbname?charset=utf8mb4
#   2. MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE

def parse_database_url(url: str) -> dict:
    """从 DATABASE_URL 解析 MySQL 连接信息"""
    # mysql+pymysql://root:123456@localhost:3306/civil_interview?charset=utf8mb4
    url = url.replace("mysql+pymysql://", "").replace("mysql://", "")
    url = url.split("?")[0]  # 去掉查询参数
    user_pass, host_db = url.split("@", 1)
    user, password = user_pass.split(":", 1)
    host_port, database = host_db.split("/", 1)
    if ":" in host_port:
        host, port = host_port.split(":", 1)
        port = int(port)
    else:
        host, port = host_port, 3306
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
    }


def get_mysql_config() -> dict:
    """从 .env 读取 MySQL 配置"""
    load_dotenv(BASE_DIR / ".env")

    database_url = os.getenv("DATABASE_URL", "")
    if database_url and "mysql" in database_url:
        config = parse_database_url(database_url)
    else:
        # 兼容 kaogong_backend 的 MYSQL_* 变量格式
        required = ["MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"]
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            raise RuntimeError(f"缺少环境变量: {', '.join(missing)}\n"
                             f"请在 .env 中设置 DATABASE_URL 或 MYSQL_* 变量")
        config = {
            "host": os.getenv("MYSQL_HOST"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER"),
            "password": os.getenv("MYSQL_PASSWORD"),
            "database": os.getenv("MYSQL_DATABASE"),
        }

    config.update({
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False,
    })
    return config


# ── MySQL 建表 SQL ────────────────────────────────────────────────────────────
TABLE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(100) NOT NULL UNIQUE,
        hashed_password VARCHAR(255) NOT NULL,
        full_name VARCHAR(100) NULL DEFAULT '',
        email VARCHAR(255) NULL DEFAULT '',
        avatar VARCHAR(255) NULL DEFAULT '',
        province VARCHAR(50) NOT NULL DEFAULT 'national',
        disabled BOOLEAN NOT NULL DEFAULT FALSE,
        preferences JSON NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS questions (
        id VARCHAR(100) PRIMARY KEY,
        stem TEXT NOT NULL,
        dimension VARCHAR(50) NOT NULL DEFAULT 'analysis',
        province VARCHAR(50) NOT NULL DEFAULT 'national',
        prep_time INT NOT NULL DEFAULT 90,
        answer_time INT NOT NULL DEFAULT 180,
        scoring_points JSON NULL,
        keywords JSON NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS exams (
        id VARCHAR(100) PRIMARY KEY,
        user_id VARCHAR(100) NOT NULL,
        question_ids JSON NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'in_progress',
        start_time DATETIME NULL,
        end_time DATETIME NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_exams_user_id (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS exam_answers (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        exam_id VARCHAR(100) NOT NULL,
        question_id VARCHAR(100) NOT NULL,
        transcript LONGTEXT NULL,
        score_result JSON NULL,
        answered_at DATETIME NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_exam_question (exam_id, question_id),
        CONSTRAINT fk_ea_exam FOREIGN KEY (exam_id) REFERENCES exams(id)
            ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS history_records (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        exam_id VARCHAR(100) NOT NULL UNIQUE,
        username VARCHAR(100) NOT NULL,
        question_count INT NOT NULL DEFAULT 0,
        total_score DECIMAL(10,2) NOT NULL DEFAULT 0,
        max_score DECIMAL(10,2) NOT NULL DEFAULT 100,
        grade VARCHAR(10) NULL DEFAULT 'B',
        province VARCHAR(50) NOT NULL DEFAULT 'national',
        dimensions JSON NULL,
        completed_at DATETIME NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        CONSTRAINT fk_hr_exam FOREIGN KEY (exam_id) REFERENCES exams(id)
            ON DELETE CASCADE ON UPDATE CASCADE,
        INDEX idx_hr_username (username)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
]


# ── 核心操作函数 ──────────────────────────────────────────────────────────────

def check_connection(config: dict) -> bool:
    """检查 MySQL 连接"""
    try:
        conn = pymysql.connect(
            host=config["host"], port=config["port"],
            user=config["user"], password=config["password"],
            charset=config["charset"], cursorclass=config["cursorclass"],
            autocommit=True,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            ver = cur.fetchone()
            print(f"  [OK] MySQL 版本: {ver['VERSION()']}")
        conn.close()
        return True
    except Exception as e:
        print(f"  [FAIL] 无法连接 MySQL: {e}")
        return False


def create_database(config: dict):
    """创建数据库（如果不存在）"""
    conn = pymysql.connect(
        host=config["host"], port=config["port"],
        user=config["user"], password=config["password"],
        charset=config["charset"], cursorclass=config["cursorclass"],
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config['database']}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            print(f"  [OK] 数据库 `{config['database']}` 已就绪")
    finally:
        conn.close()


def drop_database(config: dict):
    """删除数据库（危险操作！）"""
    conn = pymysql.connect(
        host=config["host"], port=config["port"],
        user=config["user"], password=config["password"],
        charset=config["charset"], cursorclass=config["cursorclass"],
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{config['database']}`")
            print(f"  [WARN] 数据库 `{config['database']}` 已删除")
    finally:
        conn.close()


def create_tables(config: dict):
    """创建所有表"""
    conn = pymysql.connect(**config)
    try:
        with conn.cursor() as cur:
            for sql in TABLE_STATEMENTS:
                cur.execute(sql)
        conn.commit()
        print(f"  [OK] {len(TABLE_STATEMENTS)} 张表已创建")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def check_tables(config: dict):
    """检查现有表状态"""
    conn = pymysql.connect(**config)
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = [list(row.values())[0] for row in cur.fetchall()]
            print(f"  [INFO] 现有表: {', '.join(tables) if tables else '(空)'}")
            for t in tables:
                cur.execute(f"SELECT COUNT(*) AS cnt FROM `{t}`")
                cnt = cur.fetchone()["cnt"]
                print(f"    - {t}: {cnt} 条记录")
    finally:
        conn.close()


# ── 种子数据 ──────────────────────────────────────────────────────────────────

def seed_default_user(conn):
    """创建默认管理员用户"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    sql = """
    INSERT INTO users (username, hashed_password, full_name, email, province)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        full_name = VALUES(full_name),
        email = VALUES(email)
    """
    with conn.cursor() as cur:
        cur.execute(sql, (
            "admin",
            pwd_context.hash("admin123"),
            "管理员",
            "admin@example.com",
            "national",
        ))
    print("  [OK] 默认用户: admin / admin123")


def seed_questions(conn):
    """从 seed_questions.json 导入题目"""
    if not SEED_QUESTIONS_PATH.exists():
        print(f"  [SKIP] 题目文件不存在: {SEED_QUESTIONS_PATH}")
        return 0

    with SEED_QUESTIONS_PATH.open("r", encoding="utf-8") as f:
        questions = json.load(f)

    if not isinstance(questions, list):
        questions = [questions]

    sql = """
    INSERT INTO questions (id, stem, dimension, province, prep_time, answer_time, scoring_points, keywords)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        stem = VALUES(stem),
        dimension = VALUES(dimension),
        province = VALUES(province),
        prep_time = VALUES(prep_time),
        answer_time = VALUES(answer_time),
        scoring_points = VALUES(scoring_points),
        keywords = VALUES(keywords)
    """

    count = 0
    with conn.cursor() as cur:
        for q in questions:
            cur.execute(sql, (
                q.get("id"),
                q.get("stem", ""),
                q.get("dimension", "analysis"),
                q.get("province", "national"),
                q.get("prepTime", 90),
                q.get("answerTime", 180),
                json.dumps(q.get("scoringPoints", []), ensure_ascii=False),
                json.dumps(q.get("keywords", {"scoring": [], "deducting": [], "bonus": []}), ensure_ascii=False),
            ))
            count += 1
    print(f"  [OK] 导入 {count} 道题目")
    return count


def seed_from_db_json(conn):
    """从旧的 db.json 迁移用户和考试数据（如存在）"""
    if not DB_JSON_PATH.exists():
        return

    print("  [INFO] 检测到 db.json，尝试迁移旧数据...")
    with DB_JSON_PATH.open("r", encoding="utf-8") as f:
        db_data = json.load(f)

    # 迁移用户
    users = db_data.get("users", {})
    if users:
        user_sql = """
        INSERT INTO users (username, hashed_password, full_name, email, province)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            full_name = VALUES(full_name),
            email = VALUES(email)
        """
        with conn.cursor() as cur:
            for user in users.values():
                cur.execute(user_sql, (
                    user.get("username"),
                    user.get("hashed_password", ""),
                    user.get("full_name", ""),
                    user.get("email", ""),
                    user.get("province", "national"),
                ))
        print(f"  [OK] 迁移 {len(users)} 个用户")

    # 迁移考试记录
    exams = db_data.get("exams", {})
    if exams:
        exam_sql = """
        INSERT IGNORE INTO exams (id, user_id, question_ids, status, start_time, end_time)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        with conn.cursor() as cur:
            for eid, exam in exams.items():
                cur.execute(exam_sql, (
                    eid,
                    exam.get("username", ""),
                    json.dumps(exam.get("questionIds", []), ensure_ascii=False),
                    exam.get("status", "completed"),
                    exam.get("startTime"),
                    exam.get("endTime"),
                ))
        print(f"  [OK] 迁移 {len(exams)} 条考试记录")

    # 迁移历史记录
    history = db_data.get("history", [])
    if history:
        hist_sql = """
        INSERT IGNORE INTO history_records (exam_id, username, question_count, total_score, max_score, grade, province, completed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        with conn.cursor() as cur:
            for item in history:
                exam_id = item.get("examId", "")
                if not exam_id:
                    continue
                cur.execute(hist_sql, (
                    exam_id,
                    item.get("username", ""),
                    item.get("questionCount", 0),
                    item.get("totalScore", 0),
                    item.get("maxScore", 100),
                    item.get("grade", "B"),
                    item.get("province", "national"),
                    item.get("completedAt"),
                ))
        print(f"  [OK] 迁移 {len(history)} 条历史记录")


def run_seed(config: dict):
    """执行完整种子数据写入"""
    conn = pymysql.connect(**config)
    try:
        seed_default_user(conn)
        seed_questions(conn)
        seed_from_db_json(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="公务员面试系统 — MySQL 一键部署")
    parser.add_argument("--reset", action="store_true", help="删库重建（清除所有数据！）")
    parser.add_argument("--seed-only", action="store_true", help="仅写入种子数据（不建表）")
    parser.add_argument("--check", action="store_true", help="仅检查连接和表状态")
    args = parser.parse_args()

    print("=" * 60)
    print("  公务员面试练习平台 — MySQL 一键部署脚本")
    print("=" * 60)

    # 1. 读取配置
    print("\n[1/5] 读取数据库配置...")
    try:
        config = get_mysql_config()
        print(f"  [OK] {config['user']}@{config['host']}:{config['port']}/{config['database']}")
    except Exception as e:
        print(f"  [FAIL] {e}")
        sys.exit(1)

    # 2. 检查连接
    print("\n[2/5] 检查 MySQL 连接...")
    if not check_connection(config):
        sys.exit(1)

    if args.check:
        print("\n[检查模式] 查看表状态...")
        try:
            check_tables(config)
        except Exception as e:
            print(f"  [INFO] {e}")
        print("\n✅ 检查完毕")
        return

    # 3. 创建/重置数据库
    print("\n[3/5] 准备数据库...")
    if args.reset:
        confirm = input(f"  ⚠️  确认删除数据库 `{config['database']}` 中的所有数据？(yes/no): ")
        if confirm.strip().lower() != "yes":
            print("  [取消] 操作已取消")
            sys.exit(0)
        drop_database(config)

    create_database(config)

    if args.seed_only:
        print("\n[4/5] 跳过建表（--seed-only 模式）")
    else:
        # 4. 创建表
        print("\n[4/5] 创建数据表...")
        create_tables(config)

    # 5. 写入种子数据
    print("\n[5/5] 写入种子数据...")
    run_seed(config)

    # 完成
    print("\n" + "=" * 60)
    check_tables(config)
    print("=" * 60)
    print("✅ 部署完成！")
    print(f"   数据库: {config['host']}:{config['port']}/{config['database']}")
    print(f"   默认账号: admin / admin123")
    print(f"   启动后端: python -m uvicorn main:app --host 127.0.0.1 --port 8050")
    print("=" * 60)


if __name__ == "__main__":
    main()
