import sqlite3
import threading
import asyncio
from typing import Any, List, Optional, Tuple

_local = threading.local()

def get_connection(db_path="novel_world_zh.db"):
    """Thread-local pooled connection with auto-reconnect.
    
    Safe for sync endpoints (FastAPI runs them in thread pool).
    If an endpoint closes the connection, it will be re-opened on next access.
    """
    conn = getattr(_local, "conn", None)
    
    # Check if existing connection is still alive
    if conn is not None:
        try:
            conn.execute("SELECT 1")
        except (sqlite3.ProgrammingError, sqlite3.OperationalError):
            conn = None
    
    if conn is None:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA cache_size=-8000")
        _local.conn = conn
        _local.db_path = db_path
    
    return conn

def close_connection():
    """Close the thread-local connection. Call on app shutdown."""
    conn = getattr(_local, "conn", None)
    if conn:
        try:
            conn.close()
        except Exception:
            pass
        _local.conn = None
        _local.db_path = None

async def db_execute(sql: str, params: tuple = None, fetchone: bool = False,
                     fetchall: bool = True, commit: bool = False,
                     db_path: str = "novel_world_zh.db") -> Any:
    """Execute a DB query in a thread pool. Non-blocking for async endpoints."""
    def _run():
        conn = get_connection(db_path)
        c = conn.cursor()
        if params:
            c.execute(sql, params)
        else:
            c.execute(sql)
        if commit:
            conn.commit()
        if fetchone:
            return c.fetchone()
        if fetchall:
            return c.fetchall()
        return None
    return await asyncio.to_thread(_run)

async def db_execute_many(sql: str, params_list: List[tuple], db_path: str = "novel_world_zh.db"):
    """Execute multiple statements in a thread pool."""
    def _run():
        conn = get_connection(db_path)
        c = conn.cursor()
        c.executemany(sql, params_list)
        conn.commit()
    return await asyncio.to_thread(_run)
