import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from Database import BaseDatabase

class AttachmentDatabase(BaseDatabase):
    def __init__(self, params):
        super().__init__(params)
        self.table_name = "attachments"
        self.t_att_junction_table_name = "transaction_attachment"
        self.array_maxsize=25
    
    def list(self, item_id=None, n=0):
        # if n <= 0:
        #     n=self.array_maxsize
        
        try:
            query = sql.SQL("""
                SELECT a.* FROM {table_name} AS a
            """).format(
                table_name=sql.Identifier(self.table_name),
            )

            vars = {
                "user": self.user,
            }
            if item_id:
                query += sql.SQL("""
                    WHERE a.{id} = {item_id} AND a.{user_id} = {user}
                """).format(
                    id=sql.Identifier("id"),
                    user_id=sql.Identifier("user"),
                    item_id=sql.Placeholder("item_id"),
                    user=sql.Placeholder("user"),
                )
                vars.update({
                    "item_id": item_id
                })
            else:
                query += sql.SQL("""
                    WHERE a.{user_id} = {user}
                """).format(
                    user_id=sql.Identifier("user"),
                    user=sql.Placeholder("user"),
                )

            query += sql.SQL("""
                ORDER BY a.id DESC
            """)

            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                print("query", query.as_string(self.conn))
                cur.execute(query, vars)
                if n > 0:
                    rows = cur.fetchmany(size=self.array_maxsize)
                else:
                    rows = cur.fetchall()

                return rows
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            print(ex)
    
    def add(self, item):
        if item:
            item['user'] = self.user
        columns = list(item.keys())
        values = list(item.values())
        
        try:
            query = sql.SQL("INSERT INTO {table_name} ({columns}) VALUES ({values})").format(
                table_name=sql.Identifier(self.table_name),
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
    
    def edit(self, item_id, item):
        set_clause = sql.SQL(", ").join(sql.Composed([sql.Identifier(col), sql.SQL(" = "), sql.Placeholder(col)]) for col in item.keys())

        try:
            query = sql.SQL("UPDATE {table_name} SET {set_clause} WHERE {id} = {item_id} AND {user_id} = {user}").format(
                table_name=sql.Identifier(self.table_name),
                set_clause=set_clause,
                id=sql.Identifier("id"),
                item_id=sql.Placeholder('item_id'),
                user_id=sql.Identifier("user"),
                user=sql.Placeholder("user"),
            )
            
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                print("query", query.as_string(self.conn))
                print({**item, 'item_id': item_id})
                cur.execute(query, {**item, 'item_id': item_id, "user": self.user})
            self.conn.commit()
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            print(ex)
            self.conn.rollback()
    
    def delete(self, item_id):
        try:
            query = sql.SQL("DELETE FROM {table_name} WHERE {id} = {item_id} AND {user_id} = {user}").format(
                table_name=sql.Identifier(self.table_name),
                id=sql.Identifier("id"),
                item_id=sql.Placeholder('item_id'),
                user_id=sql.Identifier("user"),
                user=sql.Placeholder("user"),
            )

            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                print("query", query.as_string(self.conn))
                cur.execute(query, {'item_id': item_id, "user": self.user})
            self.conn.commit()
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            print(ex)
            self.conn.rollback()