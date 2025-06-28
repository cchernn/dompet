from ..lib.exceptions import InvalidParamsException, DBConnectionException, DBOperationException
from ..lib.params import Params
from ..utils import config

import os
import psycopg2
from psycopg2.sql import SQL, Identifier, Composable, Literal, Placeholder, Composed
from psycopg2.extras import RealDictCursor
from abc import ABC

class BaseDatabase(ABC):
    def __init__(self, params: Params):
        self.conn = self.connect()
        self.set_user(params)
        self.table_name = None
        self.page_size = config.PAGE_SIZE
        self.valid_keys = []

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
    
    def get_query_filter(self, id: int = None, query_params: dict = {}) -> Composable:
        query = None
        filters = {k: v for k, v in query_params.items() if k in self.filter_keys}
        if id:
            filters.update({"id": id})
            self.filter_keys.update({"id": {"t", "id"}})
        if filters:
            query_parts = []
            for k in filters.keys():
                table_alias, column_name = self.filter_keys[k]
                query_parts.append(
                    Composed([Identifier(table_alias, column_name), SQL(" = "), Placeholder(k)])
                )
            query = SQL("WHERE ") + SQL(" AND ").join(query_parts)
        return query, filters

    def get_query(self, id: int = None, query_params: dict = {}, page: int = None) -> Composable:
        filter_query, filter_vars = self.get_query_filter(id=id, query_params=query_params)
        page = query_params.get("page", page)
        if page:
            offset = (page - 1) * self.page_size
        vars = {}

        # get all location data
        query = SQL("""
            SELECT * FROM {table_name} t
        """).format(
            table_name=Identifier(self.table_name),
        )

        # filter by params
        if filter_query:
            query += filter_query
            vars.update(**filter_vars)

        # sort
        query += SQL("""
            ORDER BY t.id DESC
        """)

        # paginate
        if page:
            query += SQL("""
                LIMIT {limit} OFFSET {offset}
            """).format(
                limit=Literal(self.page_size),
                offset=Literal(offset),
            )
    
        return query, vars

    def add_query(self, body: dict, user: str = None) -> Composable:
        item_body = {k:v for k, v in body.items() if k in self.valid_keys}
        if user:
            item_body.update({'user': str(user)})
        item_columns = list(item_body.keys())
        item_values = list(item_body.values())

        query = SQL("""
            INSERT INTO {table_name} ({item_columns}) VALUES ({item_values}) RETURNING *
        """).format(
            table_name=Identifier(self.table_name),
            item_columns=SQL(", ").join(map(Identifier, item_columns)),
            item_values=SQL(", ").join(Placeholder() for _ in item_values)
        )
            
        return query, item_values

    def edit_query(self, id: int, body: dict) -> Composable:
        item_body = item_body = {k: v for k, v in body.items() if k in self.valid_keys}
        set_clause = SQL(", ").join(Composed([Identifier(col), SQL(" = "), Placeholder(col)]) for col in item_body.keys())

        query = SQL("""
            UPDATE {table_name} SET {set_clause} WHERE {id_title} = {id} RETURNING *
        """).format(
            table_name=Identifier(self.table_name),
            set_clause=set_clause,
            id_title=Identifier("id"),
            id=Placeholder("id"),
        )

        return query, {**item_body, "id": id}

    def delete_query(self, id: int) -> Composable:
        query = SQL("""
            DELETE FROM {table_name} WHERE {id_title} = {id} RETURNING *
        """).format(
            table_name=Identifier(self.table_name),
            id_title=Identifier("id"),
            id=Placeholder("id")
        )

        return query, {"id": id}

    def execute_get(self, query: Composable, vars: dict = {}, many: bool = True) -> list | dict:
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
        
    def execute_commit(self, query: Composable, vars: dict = {}, is_return: bool = True) -> dict:
        try:
            data = None
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(self.get_user_query())
                print("query", query.as_string(self.conn))
                cursor.execute(query, vars)
                if is_return:
                    data = cursor.fetchone()
            self.conn.commit()
            return data
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            raise DBOperationException(ex)
        
    def get_metadata(self) -> dict:
        metadata = {}
        return metadata
