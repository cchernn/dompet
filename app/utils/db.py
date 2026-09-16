import os

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.sql import SQL, Identifier

from . import config
from ..lib.exceptions import DBOperationException


def connect():
    conn = psycopg2.connect(
        host=os.getenv("DB_POSTGRESQL_HOST"),
        user=os.getenv("DB_POSTGRESQL_USER"),
        password=os.getenv("DB_POSTGRESQL_PASSWORD"),
        dbname=os.getenv("DB_POSTGRESQL_NAME"),
        port=os.getenv("DB_POSTGRESQL_PORT"),
    )
    with conn.cursor() as cursor:
        cursor.execute(
            SQL("SET search_path TO {}, public").format(Identifier(config.DB_SCHEMA))
        )
    return conn


def run_atomic(work):
    conn = connect()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                return work(cursor)
    except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
        raise DBOperationException(ex)
    finally:
        conn.close()


def paginate(cursor, query: str, params, page: int, page_size: int):
    """Runs an already-filtered, already-ordered SELECT (no LIMIT/OFFSET)
    as one page, returning (rows, metadata). The query is wrapped as a
    subquery for the count so callers never duplicate their own
    WHERE-clause logic in a separate count query."""
    params = list(params)

    cursor.execute(f"SELECT COUNT(*) AS count FROM ({query}) AS _paginated", params)
    total_count = cursor.fetchone()["count"]

    offset = (page - 1) * page_size
    cursor.execute(f"{query} LIMIT %s OFFSET %s", params + [page_size, offset])
    rows = cursor.fetchall()

    total_pages = max(1, -(-total_count // page_size))
    metadata = {
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
    }
    return rows, metadata
