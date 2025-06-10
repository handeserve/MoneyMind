from fastapi import HTTPException, Depends
import logging
import sqlite3
import threading
from contextlib import contextmanager
from typing import Generator
from sqlite3 import Connection

from database.db import get_db_connection, close_db_connection

logger = logging.getLogger(__name__)

# 使用线程本地存储来保存数据库连接
_thread_local = threading.local()

def get_db() -> Generator[Connection, None, None]:
    """
    数据库连接的依赖注入函数。
    确保每个请求使用独立的数据库连接，并在请求结束时关闭连接。
    """
    conn = get_db_connection()
    try:
        yield conn
    finally:
        # 在请求结束时关闭连接
        close_db_connection()

@contextmanager
def get_db_context() -> Generator[sqlite3.Connection, None, None]:
    """
    获取数据库连接的上下文管理器。
    每个线程使用自己的数据库连接。
    """
    if not hasattr(_thread_local, 'db'):
        _thread_local.db = get_db_connection()
    try:
        yield _thread_local.db
    finally:
        pass  # 不要在这里关闭连接，让 FastAPI 的依赖注入系统管理连接的生命周期 