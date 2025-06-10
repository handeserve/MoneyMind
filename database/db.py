import sqlite3
from contextlib import contextmanager
import logging
from typing import Generator
import threading

logger = logging.getLogger(__name__)

# 使用线程本地存储来保存数据库连接
_thread_local = threading.local()

def get_db_connection() -> sqlite3.Connection:
    """
    获取数据库连接，使用线程本地存储确保每个线程使用自己的连接。
    """
    if not hasattr(_thread_local, "connection"):
        _thread_local.connection = sqlite3.connect("personal_expenses.db", check_same_thread=False)
        _thread_local.connection.row_factory = sqlite3.Row
    return _thread_local.connection

def close_db_connection():
    """
    关闭当前线程的数据库连接。
    """
    if hasattr(_thread_local, "connection"):
        _thread_local.connection.close()
        del _thread_local.connection

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    数据库连接的上下文管理器。
    注意：这个函数现在只用于初始化数据库，不应该在路由处理函数中使用。
    """
    conn = get_db_connection()
    try:
        yield conn
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        # 不要在这里关闭连接，让 FastAPI 的依赖注入系统管理连接生命周期
        pass

def init_db():
    """
    初始化数据库，创建必要的表。
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 创建支出表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_time TIMESTAMP NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            category_l1 TEXT,
            category_l2 TEXT,
            category_l3 TEXT,
            channel TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 创建导入记录表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS import_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            channel TEXT NOT NULL,
            import_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_records INTEGER DEFAULT 0,
            imported_records INTEGER DEFAULT 0,
            skipped_records INTEGER DEFAULT 0,
            failed_records INTEGER DEFAULT 0
        )
        """)
        
        conn.commit()
        logger.info("Database initialized successfully") 