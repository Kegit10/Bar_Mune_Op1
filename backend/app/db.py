import os
import psycopg2
import psycopg2.extras
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()

_pool = None


def init_pool():
    global _pool
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            1, 10,
            dsn=db_url,
            sslmode=os.environ.get('DB_SSLMODE', 'require')
        )
    else:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            1, 10,
            host=os.environ.get('DB_HOST', 'localhost'),
            port=int(os.environ.get('DB_PORT', 5432)),
            dbname=os.environ.get('DB_NAME', 'postgres'),
            user=os.environ.get('DB_USER', 'postgres'),
            password=os.environ.get('DB_PASSWORD', ''),
            sslmode=os.environ.get('DB_SSLMODE', 'require')
        )


def _get_conn():
    if _pool is None:
        init_pool()
    return _pool.getconn()


def _release_conn(conn):
    if _pool:
        _pool.putconn(conn)


def query(sql, params=None):
    """SELECT → lista de dicts"""
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        _release_conn(conn)


def query_one(sql, params=None):
    """SELECT → dict o None"""
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=None):
    """INSERT / UPDATE / DELETE → lista de dicts del RETURNING"""
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params or ())
        conn.commit()
        try:
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        except psycopg2.ProgrammingError:
            return []
    except Exception:
        conn.rollback()
        raise
    finally:
        _release_conn(conn)


def execute_one(sql, params=None):
    """INSERT / UPDATE / DELETE → primer dict o None"""
    rows = execute(sql, params)
    return rows[0] if rows else None
