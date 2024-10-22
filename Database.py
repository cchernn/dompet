import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import os

class Database():
    def __init__(self, params):
        self.conn = self.connect()
        self.user = params.user

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
        except psycopg2.Error as ex:
            print(ex)
        
        return conn
    
    def create(self, table_name, columns): 
        try:
            columns = self.addDefaultColumns(columns)
            query = sql.SQL("CREATE TABLE IF NOT EXISTS {table_name} ({columns})").format(
                table_name=sql.Identifier(table_name),
                columns=sql.SQL(", ").join(sql.SQL("{column_name} {column_type}").format(
                    column_name=sql.Identifier(col), 
                    column_type=sql.SQL(dtype)
                    ) for col, dtype in columns
                )
            )

            with self.conn.cursor() as cur:
                print("query", query.as_string(self.conn))
                cur.execute(query)
                self.addUpdateTimestamp(table_name, cur)
            self.conn.commit()
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            print(ex)
            self.conn.rollback()

    def createJunction(self, table_name, left_id, left_table, right_id, right_table):
        try:
            query = sql.SQL("""CREATE TABLE {table_name} (
                {left_id} INT REFERENCES {left_table}({left_default_id}) ON DELETE NO ACTION,
                {right_id} INT REFERENCES {right_table}({right_default_id}) ON DELETE NO ACTION,
                PRIMARY KEY ({left_id}, {right_id})) """).format(
                    table_name=sql.Identifier(table_name),
                    left_id=sql.Identifier(left_id),
                    left_table=sql.Identifier(left_table),
                    left_default_id=sql.Identifier("id"),
                    right_id=sql.Identifier(right_id),
                    right_table=sql.Identifier(right_table),
                    right_default_id=sql.Identifier("id"),
                )

            with self.conn.cursor() as cur:
                print("query", query.as_string(self.conn))
                cur.execute(query)
            self.conn.commit()
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            print(ex)
            self.conn.rollback()

    @classmethod
    def addDefaultColumns(cls, columns):
        if ("id", "SERIAL PRIMARY KEY") not in columns:
            columns.append(("id", "SERIAL PRIMARY KEY"))
        columns.append(("inserted_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
        columns.append(("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
        return columns
    
    @classmethod
    def addUpdateTimestamp(cls, table_name, cursor):
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_timestamp()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """)
        trigger_name = f"update_timestamp_{table_name}"
        cursor.execute(sql.SQL("""
            CREATE TRIGGER {trigger_name}
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW
            EXECUTE PROCEDURE update_timestamp();
        """).format(
            trigger_name=sql.Identifier(trigger_name), 
            table_name=sql.Identifier(table_name)
        ))

    def list(self, table_name, **kwargs):
        try:
            if "query" in kwargs:
                query = kwargs.get("query")
            else:
                query = sql.SQL("SELECT * FROM {table_name}").format(table_name=sql.Identifier(table_name))
                if "where" in kwargs:
                    where_clause = kwargs.get('where')
                    query_id = where_clause[0]
                    query_value = where_clause[1]
                    query += sql.SQL(" WHERE {user} = {user_id} AND {query_id} = {query_value}").format(
                        user=sql.Identifier('user'),
                        user_id=sql.Placeholder('user'),
                        query_id=sql.Identifier(query_id),
                        query_value=sql.Placeholder('query_value')
                    )
                else:
                    query += sql.SQL(" WHERE {user} = {user_id}").format(
                        user=sql.Identifier('user'),
                        user_id=sql.Placeholder('user'),
                    )
                if "order" in kwargs:
                    query += sql.SQL(f" ORDER BY {kwargs.get('order')} DESC")
            
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                print("query", query.as_string(self.conn))
                vars={'user': self.user}
                if "where" in kwargs: vars.update({'query_value': query_value})
                cur.execute(query, vars)
                rows = cur.fetchall()
                return rows
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            print(ex)

        return rows

    def add(self, table_name, item):
        if item:
            item['user'] = self.user
        columns = list(item.keys())
        values = list(item.values())
        
        try:
            query = sql.SQL("INSERT INTO {table_name} ({columns}) VALUES ({values})").format(
                table_name=sql.Identifier(table_name),
                columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
                values=sql.SQL(", ").join(sql.Placeholder() for _ in values)
            )
            
            with self.conn.cursor() as cur:
                print("query", query.as_string(self.conn))
                cur.execute(query, values)
            self.conn.commit()
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            print(ex)
            self.conn.rollback()

    def edit(self, table_name, item_id, item):
        set_clause = sql.SQL(", ").join(sql.Composed([sql.Identifier(col), sql.SQL(" = "), sql.Placeholder(col)]) for col in item.keys())

        try:
            query = sql.SQL("UPDATE {table_name} SET {set_clause} WHERE {id} = {item_id}").format(
                table_name=sql.Identifier(table_name),
                set_clause=set_clause,
                id=sql.Identifier("id"),
                item_id=sql.Placeholder('item_id')
            )
            
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                print("query", query.as_string(self.conn))
                print({**item, 'item_id': item_id})
                cur.execute(query, {**item, 'item_id': item_id})
            self.conn.commit()
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            print(ex)
            self.conn.rollback()
    
    def delete(self, table_name, item_id):
        try:
            query = sql.SQL("DELETE FROM {table_name} WHERE {id} = {item_id}").format(
                table_name=sql.Identifier(table_name),
                id=sql.Identifier("id"),
                item_id=sql.Placeholder('item_id')
            )

            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                print("query", query.as_string(self.conn))
                cur.execute(query, {'item_id': item_id})
            self.conn.commit()
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            print(ex)
            self.conn.rollback()