import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from Database import BaseDatabase

class TransactionDatabase(BaseDatabase):
    def __init__(self, params):
        super().__init__(params)
        self.table_name = "transactions"
        self.t_tgroup_junction_table_name = "transaction_transaction_group"
        self.user_tgroup_junction_table_name = "user_transaction_group"
        self.array_maxsize=25
    
    def list(self, item_id=None, group=None, n=0):
        if n <= 0:
            n=self.array_maxsize
        
        try:
            query = sql.SQL("""
                SELECT t.* FROM {table_name} AS t
            """).format(
                table_name=sql.Identifier(self.table_name),
            )

            vars = {
                "user": self.user,
            }
            if item_id:
                query += sql.SQL("""
                    WHERE t.{id} = {item_id} AND t.{user_id} = {user}
                """).format(
                    id=sql.Identifier("id"),
                    user_id=sql.Identifier("user"),
                    item_id=sql.Placeholder("item_id"),
                    user=sql.Placeholder("user"),
                )
                vars.update({
                    "item_id": item_id
                })
            elif group:
                query += sql.SQL("""
                    JOIN {transaction_transaction_group} AS ttgroup ON t.{id} = ttgroup.{transaction_id}
                    JOIN {user_tgroup_junction_table_name} AS utgroup ON ttgroup.{transaction_group_id} = utgroup.{transaction_group_id}
                    WHERE utgr)oup.{transaction_group_id} = {group} AND utgroup.{user_id} = {user}
                """).format(
                    transaction_transaction_group=sql.Identifier(self.t_tgroup_junction_table_name),
                    user_tgroup_junction_table_name=sql.Identifier(self.user_tgroup_junction_table_name),
                    id=sql.Identifier("id"),
                    transaction_id=sql.Identifier("transaction_id"),
                    transaction_group_id=sql.Identifier("transaction_group_id"),
                    user_id=sql.Identifier("user"),
                    user=sql.Placeholder("user"),
                    group=sql.Placeholder("group"),
                )
                vars.update({
                    "group": group
                })
            else:
                query += sql.SQL("""
                    WHERE t.{user_id} = {user}
                """).format(
                    user_id=sql.Identifier("user"),
                    user=sql.Placeholder("user"),
                )

            query += sql.SQL("""
                ORDER BY t.id DESC
            """)

            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                print("query", query.as_string(self.conn))
                cur.execute(query, vars)
                rows = cur.fetchmany(size=self.array_maxsize)

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
            query = sql.SQL("UPDATE {table_name} SET {set_clause} WHERE {id} = {item_id}").format(
                table_name=sql.Identifier(self.table_name),
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
    
    def editGroup(self, item_id, group_ids=[]):
        try:
            query = sql.SQL("""
                INSERT INTO {t_tgroup_junction_table_name} ({transaction_id}, {transaction_group_id}) 
                SELECT {item_id}, {group_id} 
                FROM unnest({group_ids}::int[]) as {group_id} 
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM {t_tgroup_junction_table_name}
                    WHERE {transaction_id} = {item_id}
                    AND {transaction_group_id} = {group_id}
                )
            """).format(
                t_tgroup_junction_table_name=sql.Identifier(self.t_tgroup_junction_table_name),
                transaction_id=sql.Identifier("transaction_id"),
                transaction_group_id=sql.Identifier("transaction_group_id"),
                group_id = sql.Identifier("group_id"),
                group_ids = sql.Placeholder("group_ids"),
                item_id=sql.Placeholder('item_id')
            )
            
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                print("query", query.as_string(self.conn))
                print({'group_ids': group_ids, 'item_id': item_id})
                cur.execute(query, {"group_ids": group_ids, 'item_id': item_id})
            self.conn.commit()
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            print(ex)
            self.conn.rollback()

    def delete(self, item_id):
        try:
            query = sql.SQL("DELETE FROM {table_name} WHERE {id} = {item_id}").format(
                table_name=sql.Identifier(self.table_name),
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


class TransactionGroupDatabase(BaseDatabase):
    def __init__(self, params):
        super().__init__(params)
        self.table_name = "transaction_groups"
        self.user_tgroup_junction_table_name = "user_transaction_group"
        self.array_maxsize=25

    def list(self, item_id=None, n=0):
        if n <= 0:
            n=self.array_maxsize
        
        try:
            query = sql.SQL("""
                SELECT tgroup.* FROM {table_name} AS tgroup
            """).format(
                table_name=sql.Identifier(self.table_name),
            )

            vars = {
                "user": self.user,
            }
            if item_id:
                query += sql.SQL("""
                     JOIN {user_tgroup_junction_table_name} AS utgroup ON tgroup.{id} = utgroup.{transaction_group_id}
                    WHERE utgroup.{transaction_group_id} = {group_id} AND utgroup.{user_id} = {user}
                """).format(
                    user_tgroup_junction_table_name=sql.Identifier(self.user_tgroup_junction_table_name),
                    id=sql.Identifier("id"),
                    transaction_group_id=sql.Identifier("transaction_group_id"),
                    user_id=sql.Identifier("user"),
                    group_id=sql.Placeholder("group_id"),
                    user=sql.Placeholder("user"),
                )
                vars.update({
                    "group_id": item_id
                })
            else:
                query += sql.SQL("""
                     JOIN {user_tgroup_junction_table_name} AS utgroup ON tgroup.{id} = utgroup.{transaction_group_id}
                    WHERE utgroup.{user_id} = {user}
                """).format(
                    user_tgroup_junction_table_name=sql.Identifier(self.user_tgroup_junction_table_name),
                    id=sql.Identifier("id"),
                    transaction_group_id=sql.Identifier("transaction_group_id"),
                    user_id=sql.Identifier("user"),
                    user=sql.Placeholder("user"),
                )

            query += sql.SQL("""
                ORDER BY tgroup.id DESC
            """)

            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                print("query", query.as_string(self.conn))
                cur.execute(query, vars)
                rows = cur.fetchmany(size=self.array_maxsize)

                return rows
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            print(ex)
    
    def add(self, item):
        if item:
            item['user'] = self.user
        columns = list(item.keys())
        values = list(item.values())
        
        try:
            tgroup_query = sql.SQL("INSERT INTO {table_name} ({columns}) VALUES ({values}) RETURNING {tgroup_id}").format(
                table_name=sql.Identifier(self.table_name),
                columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
                values=sql.SQL(", ").join(sql.Placeholder(col) for col in columns),
                tgroup_id=sql.Identifier("id"),
            )
            
            query = sql.SQL("""
                WITH new_transaction_group AS ({tgroup_query})
                INSERT INTO {user_tgroup_junction_table_name} ({transaction_group_id}, {user_id})
                SELECT new_transaction_group.{tgroup_id}, {user}
                FROM new_transaction_group
            """).format(
                tgroup_query=tgroup_query,
                tgroup_id=sql.Identifier("id"),
                user_tgroup_junction_table_name=sql.Identifier(self.user_tgroup_junction_table_name),
                transaction_group_id=sql.Identifier("transaction_group_id"),
                user_id=sql.Identifier("user"),
                user=sql.Placeholder("user"),
            )

            with self.conn.cursor() as cur:
                print("query", query.as_string(self.conn))
                cur.execute(query, {"user": self.user, **item})
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

    def editUser(self, item_id, user_ids):
        try:
            query = sql.SQL("""
                INSERT INTO {user_tgroup_junction_table_name} ({transaction_group_id}, {user}) 
                SELECT {item_id}, {user_id} 
                FROM unnest({user_ids}::uuid[]) as {user_id} 
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM {user_tgroup_junction_table_name}
                    WHERE {transaction_group_id} = {item_id}
                    AND {user} = {user_id}
                )
            """).format(
                user_tgroup_junction_table_name=sql.Identifier(self.user_tgroup_junction_table_name),
                transaction_group_id=sql.Identifier("transaction_group_id"),
                user=sql.Identifier("user"),
                user_id=sql.Identifier("user_id"),
                user_ids = sql.Placeholder("user_ids"),
                item_id=sql.Placeholder('item_id')
            )
            
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                print("query", query.as_string(self.conn))
                print({'user_ids': user_ids, 'item_id': item_id})
                cur.execute(query, {"user_ids": user_ids, 'item_id': item_id})
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