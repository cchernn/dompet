import os

import psycopg2
from psycopg2.sql import SQL, Identifier

from . import config


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
