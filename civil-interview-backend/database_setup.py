"""
MySQL 初始化、增量补字段和种子数据脚本，负责让本机、服务器和新机器的表结构保持同一口径。

正常部署只应执行默认模式或 `--check`：默认模式会创建缺失数据库、创建缺失表、补齐旧字段并幂等写入套餐和题库种子；
`--check` 只读连接和表行数，适合上线前确认没有连错库。`--reset` 会删库重建，只能在明确要清空环境时使用，
不得用于现网排障。这里的 DDL 是线上 MySQL 的准绳，ORM 模型新增表或字段时要和本文件保持类型、长度和 collation 一致。

@param: 命令行参数决定检查、建表、只写种子或重置；数据库连接来自 `.env`/`DATABASE_URL`/`MYSQL_*`。
@return: 通过 stdout 输出执行进度；脚本本身不返回业务对象。
@raises RuntimeError: 数据库配置缺失、MySQL 连接失败、DDL 或种子写入失败时抛出底层异常。
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

SUBSCRIPTION_PACKAGE_SEEDS = [
    ("trial_3h", "3小时套餐", "hourly", 99.00, 180, 180, 0, "3小时全真模拟/专项练习套餐"),
    ("monthly_1h_day", "包月套餐 1小时/天", "monthly", 299.00, 1800, 60, 30, "包月每日1小时"),
    ("monthly_2h_day", "包月包 2小时/天", "monthly", 499.00, 3600, 120, 30, "包月每日2小时"),
    ("premium_1000", "高阶包月 1000元档", "premium", 1000.00, 9000, 300, 30, "长期用户高阶套餐"),
    ("premium_2000", "高阶包月 2000元档", "premium", 2000.00, 24000, 800, 30, "长期用户旗舰套餐"),
]


def parse_database_url(url: str) -> dict:
    """
    拆解 DATABASE_URL，方便部署脚本直接拿到 PyMySQL 需要的连接参数。

    部署环境有时只给一条连接串，不给 MYSQL_* 分项变量，所以这里保留两种配置入口。

    @param url: MySQL 连接串，支持 `mysql://` 和 `mysql+pymysql://` 前缀。
    @return: PyMySQL 可直接使用的 host、port、user、password、database 字典。
    @raises ValueError: 连接串缺少用户、密码、主机或数据库片段时由拆分逻辑抛出。
    """
    url = url.replace("mysql+pymysql://", "").replace("mysql://", "")
    url = url.split("?")[0]
    user_pass, host_db = url.split("@", 1)
    user, password = user_pass.split(":", 1)
    host_port, database = host_db.split("/", 1)
    if ":" in host_port:
        host, port = host_port.split(":", 1)
        port = int(port)
    else:
        host, port = host_port, 3306
    return {"host": host, "port": port, "user": user, "password": password, "database": database}


def get_mysql_config() -> dict:
    """
    从 .env 读取 MySQL 配置，优先使用 DATABASE_URL，缺失时再拼 MYSQL_* 变量。

    缺少必要配置时直接报错，是为了避免脚本误连到默认库或本机临时库。

    @param: 无；读取后端目录下 `.env` 以及当前进程环境变量。
    @return: 带 charset、cursorclass 和 autocommit 设置的 MySQL 连接配置。
    @raises RuntimeError: DATABASE_URL 和 MYSQL_* 必填项都缺失时抛出。
    """
    load_dotenv(BASE_DIR / ".env")
    database_url = os.getenv("DATABASE_URL", "")
    if database_url and "mysql" in database_url:
        config = parse_database_url(database_url)
    else:
        required = ["MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"]
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            raise RuntimeError(f"缺少环境变量: {', '.join(missing)}\n请在 .env 中设置 DATABASE_URL 或 MYSQL_* 变量")
        config = {
            "host": os.getenv("MYSQL_HOST"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER"),
            "password": os.getenv("MYSQL_PASSWORD"),
            "database": os.getenv("MYSQL_DATABASE"),
        }
    config.update({"charset": "utf8mb4", "cursorclass": pymysql.cursors.DictCursor, "autocommit": False})
    return config


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
        agreed_terms_version VARCHAR(20) DEFAULT '',
        agreed_terms_at DATETIME NULL,
        last_login_at DATETIME NULL,
        last_active_at DATETIME NULL,
        last_login_device VARCHAR(200) DEFAULT '',
        login_device_history JSON NULL,
        invite_code VARCHAR(32) NULL DEFAULT '',
        invite_partner_id BIGINT NULL,
        invite_bound_at DATETIME NULL,
        invite_source VARCHAR(40) NULL DEFAULT '',
        registered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_users_last_login_at (last_login_at),
        INDEX idx_users_last_active_at (last_active_at),
        INDEX idx_users_registered_at (registered_at),
        INDEX idx_users_invite_code (invite_code),
        INDEX idx_users_invite_partner_id (invite_partner_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS invite_partners (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(100) NOT NULL UNIQUE,
        enabled BOOLEAN NOT NULL DEFAULT TRUE,
        remark TEXT NULL,
        contact_name VARCHAR(100) NULL DEFAULT '',
        contact_phone VARCHAR(50) NULL DEFAULT '',
        contact_wechat VARCHAR(100) NULL DEFAULT '',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_invite_partners_enabled (enabled)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS invite_codes (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        code VARCHAR(32) NOT NULL UNIQUE,
        partner_id BIGINT NOT NULL,
        enabled BOOLEAN NOT NULL DEFAULT TRUE,
        remark TEXT NULL,
        created_by VARCHAR(64) NULL DEFAULT '',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        CONSTRAINT fk_invite_codes_partner FOREIGN KEY (partner_id) REFERENCES invite_partners(id)
            ON DELETE RESTRICT ON UPDATE CASCADE,
        INDEX idx_invite_codes_partner_id (partner_id),
        INDEX idx_invite_codes_enabled (enabled)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS invite_registration_events (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(64) NOT NULL UNIQUE,
        registered_date DATE NOT NULL,
        invite_code_id BIGINT NULL,
        invite_partner_id BIGINT NULL,
        invite_code_snapshot VARCHAR(32) NULL DEFAULT '',
        invite_partner_snapshot VARCHAR(100) NULL DEFAULT '',
        source VARCHAR(40) NULL DEFAULT '',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_ire_registered_date (registered_date),
        INDEX idx_ire_invite_partner_id (invite_partner_id),
        INDEX idx_ire_invite_code_id (invite_code_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS invite_activity_daily (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(64) NOT NULL,
        active_date DATE NOT NULL,
        invite_code_id BIGINT NULL,
        invite_partner_id BIGINT NULL,
        invite_code_snapshot VARCHAR(32) NULL DEFAULT '',
        invite_partner_snapshot VARCHAR(100) NULL DEFAULT '',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_iad_username_active_date (username, active_date),
        INDEX idx_iad_date_partner_code (active_date, invite_partner_id, invite_code_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS invite_payment_events (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        order_no VARCHAR(100) NOT NULL UNIQUE,
        username VARCHAR(64) NOT NULL,
        paid_date DATE NOT NULL,
        invite_code_id BIGINT NULL,
        invite_partner_id BIGINT NULL,
        invite_code_snapshot VARCHAR(32) NULL DEFAULT '',
        invite_partner_snapshot VARCHAR(100) NULL DEFAULT '',
        paid_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
        refunded_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
        net_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_ipe_username (username),
        INDEX idx_ipe_paid_date (paid_date),
        INDEX idx_ipe_invite_partner_id (invite_partner_id),
        INDEX idx_ipe_invite_code_id (invite_code_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS invite_audit_logs (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        action_type VARCHAR(50) NOT NULL,
        target_type VARCHAR(50) NOT NULL,
        target_id VARCHAR(100) NOT NULL DEFAULT '',
        operator VARCHAR(64) NOT NULL DEFAULT '',
        before_snapshot JSON NULL,
        after_snapshot JSON NULL,
        reason TEXT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_ial_action_type (action_type),
        INDEX idx_ial_target_type (target_type),
        INDEX idx_ial_operator (operator)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS system_metric_snapshots (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        bucket_start DATETIME NOT NULL,
        cpu_percent FLOAT NOT NULL DEFAULT 0,
        memory_percent FLOAT NOT NULL DEFAULT 0,
        memory_used_mb INT NOT NULL DEFAULT 0,
        memory_total_mb INT NOT NULL DEFAULT 0,
        disk_percent FLOAT NOT NULL DEFAULT 0,
        disk_used_gb FLOAT NOT NULL DEFAULT 0,
        disk_total_gb FLOAT NOT NULL DEFAULT 0,
        load_1m FLOAT NOT NULL DEFAULT 0,
        load_5m FLOAT NOT NULL DEFAULT 0,
        load_15m FLOAT NOT NULL DEFAULT 0,
        backend_pid INT NOT NULL DEFAULT 0,
        backend_status VARCHAR(30) NOT NULL DEFAULT 'running',
        db_ok BOOLEAN NOT NULL DEFAULT FALSE,
        redis_ok BOOLEAN NOT NULL DEFAULT FALSE,
        extra_payload JSON NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_sms_bucket_start (bucket_start),
        INDEX idx_sms_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS server_error_events (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        status_code INT NOT NULL DEFAULT 500,
        method VARCHAR(10) NOT NULL DEFAULT '',
        path VARCHAR(255) NOT NULL DEFAULT '',
        request_id VARCHAR(80) NULL DEFAULT '',
        error_type VARCHAR(120) NULL DEFAULT '',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_see_status_code (status_code),
        INDEX idx_see_created_status (created_at, status_code),
        INDEX idx_see_path_created (path, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS user_activity_sessions (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        event_id VARCHAR(80) NOT NULL,
        username VARCHAR(100) NOT NULL,
        session_id VARCHAR(80) NOT NULL DEFAULT '',
        client_type VARCHAR(30) NOT NULL DEFAULT 'pc',
        route_path VARCHAR(255) NULL DEFAULT '',
        duration_seconds INT NOT NULL DEFAULT 0,
        active_at DATETIME NOT NULL,
        active_date DATE NOT NULL,
        extra_payload JSON NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_uas_user FOREIGN KEY (username) REFERENCES users(username)
            ON DELETE CASCADE ON UPDATE CASCADE,
        UNIQUE KEY uq_uas_event_id (event_id),
        INDEX idx_uas_username_active (username, active_at),
        INDEX idx_uas_session (session_id),
        INDEX idx_uas_client_type (client_type),
        INDEX idx_uas_active_date (active_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS user_activity_daily (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(100) NOT NULL,
        active_date DATE NOT NULL,
        active_seconds INT NOT NULL DEFAULT 0,
        heartbeat_count INT NOT NULL DEFAULT 0,
        last_active_at DATETIME NULL,
        client_types JSON NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        CONSTRAINT fk_uad_user FOREIGN KEY (username) REFERENCES users(username)
            ON DELETE CASCADE ON UPDATE CASCADE,
        UNIQUE KEY uq_uad_username_active_date (username, active_date),
        INDEX idx_uad_active_date (active_date)
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
        media_record JSON NULL,
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
        total_score FLOAT NOT NULL DEFAULT 0,
        max_score FLOAT NOT NULL DEFAULT 100,
        grade VARCHAR(4) NOT NULL DEFAULT 'B',
        dimensions JSON NULL,
        province VARCHAR(50) NOT NULL DEFAULT 'national',
        completed_at DATETIME NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        CONSTRAINT fk_hr_exam FOREIGN KEY (exam_id) REFERENCES exams(id)
            ON DELETE CASCADE ON UPDATE CASCADE,
        INDEX idx_hr_username (username)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS subscription_packages (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        package_code VARCHAR(100) NOT NULL UNIQUE,
        package_name VARCHAR(100) NOT NULL,
        package_type VARCHAR(30) NOT NULL,
        price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
        total_minutes INT NOT NULL DEFAULT 0,
        daily_limit_minutes INT NOT NULL DEFAULT 0,
        duration_days INT NOT NULL DEFAULT 0,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        description VARCHAR(255) NULL DEFAULT '',
        extra_config JSON NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_sp_type_active (package_type, is_active)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS payment_orders (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        order_no VARCHAR(100) NOT NULL UNIQUE,
        username VARCHAR(100) NOT NULL,
        package_code VARCHAR(100) NOT NULL,
        package_type VARCHAR(30) NOT NULL,
        amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
        pay_channel VARCHAR(30) NOT NULL DEFAULT 'wechat',
        status VARCHAR(30) NOT NULL DEFAULT 'pending',
        third_party_order_no VARCHAR(100) NULL DEFAULT '',
        paid_at DATETIME NULL,
        callback_payload JSON NULL,
        extra_payload JSON NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        CONSTRAINT fk_po_user FOREIGN KEY (username) REFERENCES users(username)
            ON DELETE CASCADE ON UPDATE CASCADE,
        INDEX idx_po_username_created (username, created_at),
        INDEX idx_po_status_created (status, created_at),
        INDEX idx_po_package_code (package_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS user_subscriptions (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(100) NOT NULL,
        package_code VARCHAR(100) NOT NULL,
        plan_type VARCHAR(30) NOT NULL,
        plan_name VARCHAR(100) NOT NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'active',
        is_trial BOOLEAN NOT NULL DEFAULT FALSE,
        trial_completed BOOLEAN NOT NULL DEFAULT FALSE,
        total_minutes INT NOT NULL DEFAULT 0,
        used_minutes INT NOT NULL DEFAULT 0,
        daily_limit_minutes INT NOT NULL DEFAULT 0,
        daily_used_minutes INT NOT NULL DEFAULT 0,
        last_reset_date DATE NULL,
        start_at DATETIME NULL,
        end_at DATETIME NULL,
        source_order_no VARCHAR(100) NULL DEFAULT '',
        extra_payload JSON NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        CONSTRAINT fk_us_user FOREIGN KEY (username) REFERENCES users(username)
            ON DELETE CASCADE ON UPDATE CASCADE,
        UNIQUE KEY uq_us_username_package_start (username, package_code, start_at),
        INDEX idx_us_username_status (username, status),
        INDEX idx_us_end_at (end_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS usage_records (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(100) NOT NULL,
        exam_id VARCHAR(100) NOT NULL,
        question_id VARCHAR(100) NULL,
        usage_type VARCHAR(30) NOT NULL DEFAULT 'practice',
        usage_seconds INT NOT NULL DEFAULT 0,
        billed_minutes INT NOT NULL DEFAULT 0,
        reported_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        extra_payload JSON NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        CONSTRAINT fk_ur_user FOREIGN KEY (username) REFERENCES users(username)
            ON DELETE CASCADE ON UPDATE CASCADE,
        CONSTRAINT fk_ur_exam FOREIGN KEY (exam_id) REFERENCES exams(id)
            ON DELETE CASCADE ON UPDATE CASCADE,
        INDEX idx_ur_username_reported (username, reported_at),
        INDEX idx_ur_exam_reported (exam_id, reported_at),
        INDEX idx_ur_usage_type (usage_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS entitlement_adjustments (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        target_username VARCHAR(100) COLLATE utf8mb4_0900_ai_ci NOT NULL,
        subscription_id BIGINT NULL,
        action_type VARCHAR(30) NOT NULL,
        minutes_delta INT NOT NULL DEFAULT 0,
        before_snapshot JSON NULL,
        after_snapshot JSON NULL,
        reason_type VARCHAR(64) NOT NULL DEFAULT '其他',
        remark TEXT NULL,
        operator VARCHAR(100) COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_ea_user FOREIGN KEY (target_username) REFERENCES users(username)
            ON DELETE CASCADE ON UPDATE CASCADE,
        CONSTRAINT fk_ea_subscription FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id)
            ON DELETE SET NULL ON UPDATE CASCADE,
        INDEX idx_ea_target_created (target_username, created_at),
        INDEX idx_ea_subscription (subscription_id),
        INDEX idx_ea_action_created (action_type, created_at),
        INDEX idx_ea_operator_created (operator, created_at),
        INDEX idx_ea_reason (reason_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS targeted_focus_configs (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        target_key VARCHAR(255) NOT NULL UNIQUE,
        target_code VARCHAR(100) NULL DEFAULT '',
        target_name VARCHAR(255) NULL DEFAULT '',
        province VARCHAR(64) NULL DEFAULT '',
        position VARCHAR(64) NULL DEFAULT '',
        payload JSON NULL,
        enabled BOOLEAN NOT NULL DEFAULT TRUE,
        updated_by VARCHAR(100) NULL DEFAULT '',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_tfc_code (target_code),
        INDEX idx_tfc_province_position (province, position),
        INDEX idx_tfc_enabled (enabled)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
]


def check_connection(config: dict) -> bool:
    """
    在建库前先验证 MySQL 能连接，减少执行到一半才失败的部署事故。

    这里只查版本号，不改任何表，适合上线前做只读检查。

    @param config: MySQL 连接配置。
    @return: 连接成功返回 True，连接失败返回 False 并打印原因。
    @raises: 内部捕获连接异常，不向外抛出。
    """
    try:
        conn = pymysql.connect(host=config["host"], port=config["port"], user=config["user"],
                               password=config["password"], charset=config["charset"],
                               cursorclass=config["cursorclass"], autocommit=True)
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            ver = cur.fetchone()
            print(f" [OK] MySQL 版本: {ver['VERSION()']}")
        conn.close()
        return True
    except Exception as e:
        print(f" [FAIL] 无法连接 MySQL: {e}")
        return False


def create_database(config: dict):
    """
    创建业务库并固定 utf8mb4，保证题干、转写和中文套题名能完整保存。

    脚本显式建库，是为了新服务器初始化时不依赖人工提前建好 schema。

    @param config: 配置载荷；用于管理员或环境变量覆盖默认行为，调用方需保证来源可信。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    conn = pymysql.connect(host=config["host"], port=config["port"], user=config["user"],
                            password=config["password"], charset=config["charset"],
                            cursorclass=config["cursorclass"], autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{config['database']}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f" [OK] 数据库`{config['database']}` 已就绪")
    finally:
        conn.close()


def drop_database(config: dict):
    """
    删除目标业务库，仅在显式 reset 时使用。

    这个函数会清空真实数据，保留独立函数名是为了让调用点足够醒目。

    @param config: 配置载荷；用于管理员或环境变量覆盖默认行为，调用方需保证来源可信。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    conn = pymysql.connect(host=config["host"], port=config["port"], user=config["user"],
                            password=config["password"], charset=config["charset"],
                            cursorclass=config["cursorclass"], autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{config['database']}`")
            print(f" [WARN] 数据库`{config['database']}` 已删除")
    finally:
        conn.close()


def _column_exists(cur, database: str, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (database, table, column),
    )
    return cur.fetchone()["cnt"] > 0


def _add_column_if_missing(cur, database: str, table: str, column: str, ddl: str) -> None:
    if not _column_exists(cur, database, table, column):
        cur.execute(f"ALTER TABLE `{table}` ADD COLUMN {ddl}")


def _index_exists(cur, database: str, table: str, index_name: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND INDEX_NAME = %s
        """,
        (database, table, index_name),
    )
    return cur.fetchone()["cnt"] > 0


def _add_index_if_missing(cur, database: str, table: str, index_name: str, ddl: str) -> None:
    if not _index_exists(cur, database, table, index_name):
        cur.execute(ddl)


def ensure_schema_updates(conn, database: str) -> None:
    """
    给旧库补新增字段和索引，让老服务器不需要手写迁移 SQL 也能跟上当前代码。

    这里按列和索引逐项检查，是为了重复执行脚本时保持幂等。

    @param conn: 已连接到目标业务库的 PyMySQL 连接。
    @param database: 当前要检查的 schema 名。
    @return: 无返回值；缺失字段、索引或 legacy key 会被补齐。
    @raises pymysql.MySQLError: DDL 或数据回填失败时沿调用栈上抛，由外层事务回滚。
    """
    with conn.cursor() as cur:
        _add_column_if_missing(cur, database, "users", "agreed_terms_version", "agreed_terms_version VARCHAR(20) DEFAULT ''")
        _add_column_if_missing(cur, database, "users", "agreed_terms_at", "agreed_terms_at DATETIME NULL")
        _add_column_if_missing(cur, database, "users", "last_login_at", "last_login_at DATETIME NULL")
        _add_column_if_missing(cur, database, "users", "last_active_at", "last_active_at DATETIME NULL")
        _add_column_if_missing(cur, database, "users", "registered_at", "registered_at DATETIME NULL")
        cur.execute("UPDATE users SET registered_at = COALESCE(created_at, NOW()) WHERE registered_at IS NULL")
        _add_index_if_missing(cur, database, "users", "idx_users_last_login_at", "CREATE INDEX idx_users_last_login_at ON users (last_login_at)")
        _add_index_if_missing(cur, database, "users", "idx_users_last_active_at", "CREATE INDEX idx_users_last_active_at ON users (last_active_at)")
        _add_index_if_missing(cur, database, "users", "idx_users_registered_at", "CREATE INDEX idx_users_registered_at ON users (registered_at)")
        _add_column_if_missing(cur, database, "users", "last_login_device", "last_login_device VARCHAR(200) DEFAULT ''")
        _add_column_if_missing(cur, database, "users", "login_device_history", "login_device_history JSON NULL")
        _add_column_if_missing(cur, database, "users", "invite_code", "invite_code VARCHAR(32) DEFAULT ''")
        _add_column_if_missing(cur, database, "users", "invite_partner_id", "invite_partner_id BIGINT NULL")
        _add_column_if_missing(cur, database, "users", "invite_bound_at", "invite_bound_at DATETIME NULL")
        _add_column_if_missing(cur, database, "users", "invite_source", "invite_source VARCHAR(40) DEFAULT ''")
        _add_index_if_missing(cur, database, "users", "idx_users_invite_code", "CREATE INDEX idx_users_invite_code ON users (invite_code)")
        _add_index_if_missing(cur, database, "users", "idx_users_invite_partner_id", "CREATE INDEX idx_users_invite_partner_id ON users (invite_partner_id)")
        _add_column_if_missing(cur, database, "exam_answers", "score_result", "score_result JSON NULL AFTER transcript")
        _add_column_if_missing(cur, database, "history_records", "total_score", "total_score FLOAT NOT NULL DEFAULT 0")
        _add_column_if_missing(cur, database, "history_records", "max_score", "max_score FLOAT NOT NULL DEFAULT 100")
        _add_column_if_missing(cur, database, "history_records", "grade", "grade VARCHAR(4) NOT NULL DEFAULT 'B'")
        _add_column_if_missing(cur, database, "history_records", "dimensions", "dimensions JSON NULL")
        _add_column_if_missing(cur, database, "targeted_focus_configs", "target_key", "target_key VARCHAR(255) NULL")
        _add_column_if_missing(cur, database, "targeted_focus_configs", "target_code", "target_code VARCHAR(100) DEFAULT ''")
        _add_column_if_missing(cur, database, "targeted_focus_configs", "target_name", "target_name VARCHAR(255) DEFAULT ''")
        _add_column_if_missing(cur, database, "targeted_focus_configs", "payload", "payload JSON NULL")
        _add_column_if_missing(cur, database, "targeted_focus_configs", "enabled", "enabled BOOLEAN NOT NULL DEFAULT TRUE")
        cur.execute(
            """
            UPDATE targeted_focus_configs
            SET target_key = CONCAT('legacy:', province, '|', position, '|', id)
            WHERE target_key IS NULL OR target_key = ''
            """
        )
        cur.execute("ALTER TABLE targeted_focus_configs MODIFY COLUMN target_key VARCHAR(255) NOT NULL")
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'targeted_focus_configs' AND INDEX_NAME = 'uq_tfc_target_key'
            """,
            (database,),
        )
        if cur.fetchone()["cnt"] == 0:
            cur.execute("CREATE UNIQUE INDEX uq_tfc_target_key ON targeted_focus_configs (target_key)")


def create_tables(config: dict):
    """
    创建或更新核心业务表，覆盖用户、题目、考试、订单、权益和定向备面配置。

    所有表结构集中在这里，是为了新机器部署和旧库补字段走同一份脚本。

    @param config: 配置载荷；用于管理员或环境变量覆盖默认行为，调用方需保证来源可信。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    conn = pymysql.connect(**config)
    try:
        with conn.cursor() as cur:
            for sql in TABLE_STATEMENTS:
                cur.execute(sql)
        ensure_schema_updates(conn, config["database"])
        conn.commit()
        print(f" [OK] {len(TABLE_STATEMENTS)} 张表已创建/更新")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def check_tables(config: dict):
    """
    打印当前表和记录数，方便部署后确认有没有连错库或漏导数据。

    它只读表数量，不输出用户隐私和题目正文。

    @param config: 配置载荷；用于管理员或环境变量覆盖默认行为，调用方需保证来源可信。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    conn = pymysql.connect(**config)
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = [list(row.values())[0] for row in cur.fetchall()]
            print(f" [INFO] 现有表 {', '.join(tables) if tables else '(空)'}")
            for table in tables:
                cur.execute(f"SELECT COUNT(*) AS cnt FROM `{table}`")
                count = cur.fetchone()["cnt"]
                print(f" - {table}: {count} 条记录")
    finally:
        conn.close()


def seed_default_user(conn):
    """
    写入默认管理员账号，方便全新环境第一次登录后台。

    已存在 admin 时只更新展示资料，不替换用户名以外的真实用户数据。

    @param conn: 已连接到目标业务库的 PyMySQL 连接。
    @return: 无返回值；默认管理员存在则只刷新展示资料。
    @raises pymysql.MySQLError: 插入或更新失败时沿调用栈上抛。
    """
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
    sql = """
    INSERT INTO users (username, hashed_password, full_name, email, province, registered_at)
    VALUES (%s, %s, %s, %s, %s, NOW())
    ON DUPLICATE KEY UPDATE full_name = VALUES(full_name), email = VALUES(email)
    """
    with conn.cursor() as cur:
        cur.execute(sql, ("admin", pwd_context.hash("admin123"), "管理员", "admin@example.com", "national"))
        print(" [OK] 默认用户: admin / admin123")


def seed_subscription_packages(conn):
    """
    写入当前上架套餐，保证套餐中心和微信虚拟支付道具能对上。

    套餐用 package_code 幂等更新，避免重复执行脚本生成多份同名套餐。

    @param conn: 已连接到目标业务库的 PyMySQL 连接。
    @return: 无返回值；套餐按 package_code 幂等写入。
    @raises pymysql.MySQLError: 套餐写入失败时沿调用栈上抛。
    """
    sql = """
    INSERT INTO subscription_packages (package_code, package_name, package_type, price, total_minutes, daily_limit_minutes, duration_days, description)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        package_name = VALUES(package_name),
        package_type = VALUES(package_type),
        price = VALUES(price),
        total_minutes = VALUES(total_minutes),
        daily_limit_minutes = VALUES(daily_limit_minutes),
        duration_days = VALUES(duration_days),
        description = VALUES(description),
        is_active = TRUE
    """
    with conn.cursor() as cur:
        for package in SUBSCRIPTION_PACKAGE_SEEDS:
            cur.execute(sql, package)
        print(f" [OK] 套餐配置: {len(SUBSCRIPTION_PACKAGE_SEEDS)} 个")


def seed_questions(conn):
    """
    从 seed_questions.json 写入基础题目，用于空库演示和本地冒烟测试。

    正式题库主要靠导入资产同步，这里只是保证新环境不会完全没题可测。

    @param conn: 已连接到目标业务库的 PyMySQL 连接。
    @return: 成功写入或更新的 seed 题目数量；文件缺失时返回 0。
    @raises json.JSONDecodeError: seed_questions.json 不是合法 JSON 时抛出。
    @raises pymysql.MySQLError: 题目写入失败时沿调用栈上抛。
    """
    if not SEED_QUESTIONS_PATH.exists():
        print(f" [SKIP] 题目文件不存在 {SEED_QUESTIONS_PATH}")
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
                json.dumps(q.get("keywords", {"scoring": [], "deducting": [], "bonus": []}), ensure_ascii=False)
            ))
            count += 1
    print(f" [OK] 导入 {count} 道题目")
    return count


def seed_from_db_json(conn):
    """
    迁移早期 db.json 里的用户、考试和历史记录，给老数据一次性搬到 MySQL 的通道。

    迁移使用 INSERT IGNORE，是为了重复执行时不覆盖已经进入 MySQL 的真实记录。

    @param conn: 已连接到目标业务库的 PyMySQL 连接。
    @return: 无返回值；旧 JSON 不存在时直接跳过。
    @raises json.JSONDecodeError: db.json 不是合法 JSON 时抛出。
    @raises pymysql.MySQLError: 旧数据写入失败时沿调用栈上抛。
    """
    if not DB_JSON_PATH.exists():
        return
    print(" [INFO] 检测到 db.json，尝试迁移旧数据...")
    with DB_JSON_PATH.open("r", encoding="utf-8") as f:
        db_data = json.load(f)
    users = db_data.get("users", {})
    if users:
        user_sql = """
        INSERT INTO users (username, hashed_password, full_name, email, province)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE full_name = VALUES(full_name), email = VALUES(email)
        """
        with conn.cursor() as cur:
            for user in users.values():
                cur.execute(user_sql, (
                    user.get("username"),
                    user.get("hashed_password", ""),
                    user.get("full_name", ""),
                    user.get("email", ""),
                    user.get("province", "national")
                ))
        print(f" [OK] 迁移 {len(users)} 个用户")

    exams = db_data.get("exams", {})
    if exams:
        exam_sql = """
        INSERT IGNORE INTO exams (id, user_id, question_ids, status, start_time, end_time)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        with conn.cursor() as cur:
            for exam_id, exam in exams.items():
                cur.execute(exam_sql, (
                    exam_id,
                    exam.get("username", ""),
                    json.dumps(exam.get("questionIds", []), ensure_ascii=False),
                    exam.get("status", "completed"),
                    exam.get("startTime"),
                    exam.get("endTime")
                ))
        print(f" [OK] 迁移 {len(exams)} 条考试记录")

    history = db_data.get("history", [])
    if history:
        hist_sql = """
        INSERT IGNORE INTO history_records (exam_id, username, question_count, province, completed_at)
        VALUES (%s, %s, %s, %s, %s)
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
                    item.get("province", "national"),
                    item.get("completedAt")
                ))
        print(f" [OK] 迁移 {len(history)} 条历史记录")


def run_seed(config: dict):
    """
    按固定顺序写入默认用户、套餐、题目和旧 JSON 数据。

    这些写入放在同一个事务里，是为了任何一步失败时不留下半套初始化数据。

    @param config: 配置载荷；用于管理员或环境变量覆盖默认行为，调用方需保证来源可信。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    conn = pymysql.connect(**config)
    try:
        seed_default_user(conn)
        seed_subscription_packages(conn)
        seed_questions(conn)
        seed_from_db_json(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    """
    命令行入口，给部署人员提供检查、建表、重置和只写种子数据几种模式。

    交互输出写得直白，是为了服务器上执行脚本时能快速看出卡在哪一步。

    @param: 无；从命令行参数和环境变量读取执行模式与数据库配置。
    @return: 无返回值；成功或失败通过 stdout 和进程退出码体现。
    @raises SystemExit: 配置缺失、连接失败或用户选择退出时结束进程。
    """
    parser = argparse.ArgumentParser(description="公务员面试系统 - MySQL 一键部署")
    parser.add_argument("--reset", action="store_true", help="删库重置（清除所有数据）")
    parser.add_argument("--seed-only", action="store_true", help="仅写入种子数据（不建表）")
    parser.add_argument("--check", action="store_true", help="仅检查连接和表状态")
    args = parser.parse_args()

    print("=" * 60)
    print(" 公务员面试练习平台 - MySQL 一键部署脚本")
    print("=" * 60)

    print("\n[1/5] 读取数据库配置...")
    try:
        config = get_mysql_config()
        print(f" [OK] {config['user']}@{config['host']}:{config['port']}/{config['database']}")
    except Exception as e:
        print(f" [FAIL] {e}")
        sys.exit(1)

    print("\n[2/5] 检查 MySQL 连接...")
    if not check_connection(config):
        sys.exit(1)

    if args.check:
        print("\n[检查模式] 查看表状态...")
        try:
            check_tables(config)
        except Exception as e:
            print(f" [INFO] {e}")
        print("\n检查完毕")
        return

    if args.reset:
        print("\n[3/5] 删除并重建数据库...")
        drop_database(config)
    else:
        print("\n[3/5] 创建数据库（如不存在）...")
        create_database(config)

    if not args.seed_only:
        print("\n[4/5] 创建表结构...")
        create_tables(config)
    else:
        print("\n[4/5] 跳过建表（仅种子模式）")

    print("\n[5/5] 写入种子数据...")
    run_seed(config)

    print("\n部署完成！")


if __name__ == "__main__":
    main()
