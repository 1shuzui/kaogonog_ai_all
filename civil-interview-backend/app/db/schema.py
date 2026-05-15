"""Small runtime schema patches for existing deployments."""
from __future__ import annotations

import logging

from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)


def _column_names(engine, table_name: str) -> set[str]:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def ensure_runtime_schema(engine) -> None:
    columns = _column_names(engine, "users")
    if not columns:
        columns = set()
    if columns and "role" not in columns:
        with engine.begin() as conn:
            if engine.dialect.name == "mysql":
                conn.execute(text("ALTER TABLE users ADD COLUMN `role` VARCHAR(32) NOT NULL DEFAULT 'user' AFTER province"))
            else:
                conn.execute(text("ALTER TABLE users ADD COLUMN `role` VARCHAR(32) NOT NULL DEFAULT 'user'"))
        logger.info("Runtime schema patched", extra={"event": "database.schema.patched", "table": "users", "column": "role"})

    wechat_columns = {
        "wechat_mini_openid": "VARCHAR(128)",
        "wechat_unionid": "VARCHAR(128)",
        "wechat_web_openid": "VARCHAR(128)",
    }
    for column, column_type in wechat_columns.items():
        if columns and column not in columns:
            with engine.begin() as conn:
                if engine.dialect.name == "mysql":
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN `{column}` {column_type} NULL"))
                    if column in {"wechat_mini_openid", "wechat_web_openid"}:
                        conn.execute(text(f"CREATE UNIQUE INDEX `idx_users_{column}` ON users (`{column}`)"))
                    else:
                        conn.execute(text(f"CREATE INDEX `idx_users_{column}` ON users (`{column}`)"))
                else:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {column} {column_type} NULL"))
                    unique = "UNIQUE " if column in {"wechat_mini_openid", "wechat_web_openid"} else ""
                    conn.execute(text(f"CREATE {unique}INDEX IF NOT EXISTS idx_users_{column} ON users({column})"))
            columns.add(column)
            logger.info("Runtime schema patched", extra={"event": "database.schema.patched", "table": "users", "column": column})

    answer_columns = _column_names(engine, "exam_answers")
    if answer_columns and "media_record" not in answer_columns:
        with engine.begin() as conn:
            if engine.dialect.name == "mysql":
                conn.execute(text("ALTER TABLE exam_answers ADD COLUMN `media_record` JSON NULL"))
            else:
                conn.execute(text("ALTER TABLE exam_answers ADD COLUMN media_record JSON"))
        logger.info(
            "Runtime schema patched",
            extra={"event": "database.schema.patched", "table": "exam_answers", "column": "media_record"},
        )

    with engine.begin() as conn:
        inspector = inspect(engine)
        if "feedback_tickets" not in inspector.get_table_names():
            if engine.dialect.name == "mysql":
                conn.execute(text("""
                    CREATE TABLE `feedback_tickets` (
                        `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
                        `username` VARCHAR(64) NOT NULL,
                        `feedback_type` VARCHAR(64) NOT NULL DEFAULT '其他建议',
                        `question_id` VARCHAR(64) DEFAULT '',
                        `summary` TEXT NOT NULL,
                        `contact` VARCHAR(128) DEFAULT '',
                        `route_path` VARCHAR(200) DEFAULT '',
                        `province` VARCHAR(32) DEFAULT 'national',
                        `status` VARCHAR(32) NOT NULL DEFAULT 'pending',
                        `admin_note` TEXT,
                        `handled_by` VARCHAR(64) DEFAULT '',
                        `handled_at` DATETIME NULL,
                        `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX `idx_feedback_tickets_username` (`username`),
                        INDEX `idx_feedback_tickets_status` (`status`),
                        INDEX `idx_feedback_tickets_province` (`province`),
                        INDEX `idx_feedback_tickets_created_at` (`created_at`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE feedback_tickets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username VARCHAR(64) NOT NULL,
                        feedback_type VARCHAR(64) NOT NULL DEFAULT '其他建议',
                        question_id VARCHAR(64) DEFAULT '',
                        summary TEXT NOT NULL,
                        contact VARCHAR(128) DEFAULT '',
                        route_path VARCHAR(200) DEFAULT '',
                        province VARCHAR(32) DEFAULT 'national',
                        status VARCHAR(32) NOT NULL DEFAULT 'pending',
                        admin_note TEXT DEFAULT '',
                        handled_by VARCHAR(64) DEFAULT '',
                        handled_at DATETIME NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_feedback_tickets_username ON feedback_tickets(username)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_feedback_tickets_status ON feedback_tickets(status)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_feedback_tickets_province ON feedback_tickets(province)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_feedback_tickets_created_at ON feedback_tickets(created_at)"))
            logger.info("Runtime schema patched", extra={"event": "database.schema.patched", "table": "feedback_tickets"})
