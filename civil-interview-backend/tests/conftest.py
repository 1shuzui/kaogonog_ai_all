"""
pytest 测试基础设施：为 SQLite 注册 MySQL 生产表结构使用的排序规则。

生产数据库是 MySQL，部分模型字段声明了 `utf8mb4_0900_ai_ci`。单元测试使用内存 SQLite
时，注册一个稳定的近似排序规则即可复用同一套 ORM 表结构，而不需要改变生产模型定义。
"""
import sqlite3

from sqlalchemy import event
from sqlalchemy.engine import Engine


@event.listens_for(Engine, "connect")
def register_mysql_collation_for_sqlite(dbapi_connection, _connection_record):
    """让所有 SQLite 测试连接都能解析 MySQL 字符串排序规则。"""
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return

    def compare(left, right):
        left_key = str(left or "").casefold()
        right_key = str(right or "").casefold()
        return (left_key > right_key) - (left_key < right_key)

    dbapi_connection.create_collation("utf8mb4_0900_ai_ci", compare)
