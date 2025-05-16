from ..lib.exceptions import InvalidParamsException, DBConnectionException, DBOperationException
from ..lib.params import Params
from ..utils import config

import os
import psycopg2
from psycopg2.sql import SQL, Identifier, Composable, Literal
from psycopg2.extras import RealDictCursor
from abc import ABC

class BaseDatabase(ABC):
    def __init__(self, params: Params):
        self.conn = self.connect()
        self.set_user(params)
        self.table_name = None
        self.page_size = config.PAGE_SIZE

    def connect(self):
        conn = None
        try:
            conn = psycopg2.connect(
                host=os.getenv('DB_POSTGRESQL_HOST'),
                user=os.getenv('DB_POSTGRESQL_USER'),
                password=os.getenv('DB_POSTGRESQL_PASSWORD'),
                dbname=os.getenv('DB_POSTGRESQL_NAME'),
                port=os.getenv('DB_POSTGRESQL_PORT'),
            )
            print("Connection successful")
        except psycopg2.Error as ex:
            raise DBConnectionException(ex)
        
        return conn
    
    def close(self):
        self.conn.close()
        print("Connection closed")

    def set_user(self, params: Params):
        try:
            self.user = params.user
        except psycopg2.Error as ex:
            raise InvalidParamsException(ex)

    def get_user_query(self):
        try:
            query = SQL("""
                SET app.current_user_id = {user_id}
            """).format(
                user_id=Identifier(str(self.user))
            )
            print("user_query", query.as_string(self.conn))
            return query
        except psycopg2.Error as ex:
            raise DBOperationException(ex)
    
    def get_query(self, page: int = 1) -> Composable:
        offset = (page - 1) * self.page_size

        # get all location data
        query = SQL("""
            SELECT * FROM {table_name}
        """).format(
            table_name=Identifier(self.table_name),
        )

        # sort and paginate
        query += SQL("""
            ORDER BY id DESC
            LIMIT {limit} OFFSET {offset}
        """).format(
            limit=Literal(self.page_size),
            offset=Literal(offset),
        )
    
        return query

    def get_data(self, query: Composable, vars: dict = {}, many: bool = True) -> list:
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(self.get_user_query())
                print("query", query.as_string(self.conn))
                cursor.execute(query, vars)
                if many:
                    data = cursor.fetchall()
                else:
                    data = cursor.fetchone()
                return data
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            raise DBOperationException(ex)
        
    def get_metadata(self) -> dict:
        metadata = {}
        return metadata
