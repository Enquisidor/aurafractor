"""
Database connection pooling and query helpers.

Uses psycopg2 SimpleConnectionPool for connection pooling.
All queries use parameterized statements to prevent SQL injection.
"""

import os
import logging
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple, Union

from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

logger = logging.getLogger(__name__)

_pool: Optional[SimpleConnectionPool] = None

MIN_CONNECTIONS = int(os.getenv('DB_MIN_CONNECTIONS', '1'))
MAX_CONNECTIONS = int(os.getenv('DB_MAX_CONNECTIONS', '20'))


def get_pool() -> SimpleConnectionPool:
    """Get or create the connection pool (lazy initialization)."""
    global _pool
    if _pool is None:
        database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/music_separation')
        try:
            _pool = SimpleConnectionPool(
                MIN_CONNECTIONS,
                MAX_CONNECTIONS,
                database_url,
            )
            logger.info('Database connection pool created (min=%d, max=%d)', MIN_CONNECTIONS, MAX_CONNECTIONS)
        except Exception as exc:
            logger.error('Failed to create DB pool: %s', exc)
            raise
    return _pool


def get_db_connection():
    """Get a database connection from the pool."""
    return get_pool().getconn()


def release_db_connection(conn) -> None:
    """Return a connection to the pool."""
    pool = get_pool()
    pool.putconn(conn)


@contextmanager
def db_connection():
    """Context manager that yields a connection and returns it to the pool."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        release_db_connection(conn)


@contextmanager
def db_transaction():
    """Context manager for database transactions.

    Commits on success, rolls back on any exception.
    """
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_db_connection(conn)


def execute_query(
    sql: str,
    params: Optional[Tuple] = None,
    fetch_one: bool = False,
    fetch_all: bool = True,
    conn=None,
) -> Union[Optional[Dict], List[Dict], None]:
    """Execute a SELECT query and return results as dicts.

    Args:
        sql: Parameterized SQL query.
        params: Query parameters (prevents SQL injection).
        fetch_one: Return a single row dict or None.
        fetch_all: Return list of row dicts (default).
        conn: Optional existing connection; if None, borrows from pool.

    Returns:
        Single dict, list of dicts, or None depending on fetch_one/fetch_all.
    """
    own_conn = conn is None
    if own_conn:
        conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch_one:
                row = cur.fetchone()
                return dict(row) if row else None
            if fetch_all:
                rows = cur.fetchall()
                return [dict(r) for r in rows]
            return None
    finally:
        if own_conn:
            release_db_connection(conn)


def execute_transaction(
    operations: List[Tuple[str, Optional[Tuple]]],
) -> List[Optional[Dict]]:
    """Execute multiple SQL statements in a single transaction.

    Args:
        operations: List of (sql, params) tuples.

    Returns:
        List of result rows from RETURNING clauses (or None if no RETURNING).
    """
    results = []
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for sql, params in operations:
                cur.execute(sql, params)
                try:
                    row = cur.fetchone()
                    results.append(dict(row) if row else None)
                except Exception:
                    results.append(None)
    return results


def health_check() -> bool:
    """Verify the database is reachable."""
    try:
        result = execute_query('SELECT 1 AS alive', fetch_one=True)
        return result is not None
    except Exception as exc:
        logger.error('DB health check failed: %s', exc)
        return False
