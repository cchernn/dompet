import psycopg2
from psycopg2 import sql
import os

def load_db(db_model):
    def load_db_func(func):
        def db_wrapper(params):
            db = db_model(params)
            result = func(params, db)
            db.close()
            return result
        return db_wrapper
    return load_db_func

class BaseDatabase():
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
    
    def close(self):
        self.conn.close()

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
            query = sql.SQL("""CREATE TABLE IF NOT EXISTS {table_name} (
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
    
    def createJunctionUser(self, table_name, left_id, left_table):
        try:
            query = sql.SQL("""CREATE TABLE IF NOT EXISTS {table_name} (
                {left_id} INT REFERENCES {left_table}({left_default_id}) ON DELETE NO ACTION,
                {user} UUID NOT NULL,
                PRIMARY KEY ({left_id}, {user})) """).format(
                    table_name=sql.Identifier(table_name),
                    left_id=sql.Identifier(left_id),
                    left_table=sql.Identifier(left_table),
                    left_default_id=sql.Identifier("id"),
                    user=sql.Identifier("user"),
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