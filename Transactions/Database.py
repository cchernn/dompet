import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from Database import BaseDatabase

class TransactionDatabase(BaseDatabase):
    def __init__(self, params):
        super().__init__(params)
        self.table_name = "transactions"
        self.t_tgroup_junction_table_name = "transaction_transaction_group" # DEPRECATE
        self.transaction_transaction_group_junction_table_name = "transaction_transaction_group"
        self.transaction_group_table_name = "transaction_groups"
        self.user_tgroup_junction_table_name = "user_transaction_group"
        self.t_attachment_junction_table_name = "transaction_attachment"
        self.location_table_name = "locations"
        self.transaction_attachment_junction_table_name = "transaction_attachment"
        self.attachment_table_name = "attachments"
        self.array_maxsize=25
    
    def list(self, item_id=None, group=None, n=0):
        if n <= 0:
            n=self.array_maxsize
        
        try:
            query = sql.SQL("""
                SELECT t.*, lt.name AS {location_name}, 
                COALESCE(
                    JSONB_AGG(
                        DISTINCT to_jsonb(at)
                    ) FILTER (WHERE at.id IS NOT NULL),
                    '[]'::jsonb
                ) AS {attachments},
                COALESCE(
                    JSONB_AGG(
                        DISTINCT to_jsonb(tgroup)
                    ) FILTER (WHERE tgroup.id IS NOT NULL),
                    '[]'::jsonb
                ) AS {groups}
                FROM {table_name} AS t
            """).format(
                table_name=sql.Identifier(self.table_name),
                location_name=sql.Identifier("location_name"),
                attachments=sql.Identifier("attachments"),
                groups=sql.Identifier("groups"),
            )

            vars = {
                "user": self.user,
            }

            query += sql.SQL("""
                LEFT JOIN {location_table_name} AS lt ON t.{location_id} = lt.{location_table_id}
            """).format(
                location_table_name=sql.Identifier(self.location_table_name),
                location_id=sql.Identifier("location"),
                location_table_id=sql.Identifier("id"),
            )

            query += sql.SQL("""
                LEFT JOIN {transaction_attachment_junction_table_name} AS att ON t.{id} = att.{attachment_junction_table_transaction_id}
                LEFT JOIN {attachment_table_name} AS at ON at.{attachment_table_id} = att.{attachment_junction_table_id}
            """).format(
                transaction_attachment_junction_table_name=sql.Identifier(self.transaction_attachment_junction_table_name),
                attachment_table_name=sql.Identifier(self.attachment_table_name),
                id=sql.Identifier("id"),
                attachment_junction_table_transaction_id=sql.Identifier("transaction_id"),
                attachment_table_id=sql.Identifier("id"),
                attachment_junction_table_id=sql.Identifier("attachment_id"),
            )

            query += sql.SQL("""
                LEFT JOIN {transaction_transaction_group_junction_table_name} AS ttgroup ON t.{id} = ttgroup.{transaction_id}
                LEFT JOIN {transaction_group_table_name} AS tgroup ON tgroup.{transaction_group_table_id} = ttgroup.{transaction_group_junction_table_id}
            """).format(
                transaction_transaction_group_junction_table_name=sql.Identifier(self.transaction_transaction_group_junction_table_name),
                transaction_group_table_name=sql.Identifier(self.transaction_group_table_name),
                id=sql.Identifier("id"),
                transaction_id=sql.Identifier("transaction_id"),
                transaction_group_table_id=sql.Identifier("id"),
                transaction_group_junction_table_id=sql.Identifier("transaction_group_id"),
            )

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
                    WHERE utgroup.{transaction_group_id} = {group} AND utgroup.{user_id} = {user}
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
                GROUP BY t.id, lt.name
            """)

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
        new_id = None

        transaction_items = {c: v for c, v in item.items() if c not in ['attachments', 'groups']}
        transaction_columns = list(transaction_items.keys())
        transaction_values = list(transaction_items.values())
        group_ids = item.get("groups")
        attachment_ids = item.get("attachments")
        
        try:
            query = sql.SQL("INSERT INTO {table_name} ({transaction_columns}) VALUES ({transaction_values}) RETURNING {id}").format(
                table_name=sql.Identifier(self.table_name),
                transaction_columns=sql.SQL(", ").join(map(sql.Identifier, transaction_columns)),
                transaction_values=sql.SQL(", ").join(sql.Placeholder() for _ in transaction_values),
                id=sql.Identifier("id")
            )
            
            with self.conn.cursor() as cur:
                print("transaction_query", query.as_string(self.conn))
                cur.execute(query, transaction_values)
                new_id = cur.fetchone()[0]
            self.conn.commit()
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            print(ex)
            self.conn.rollback()

        if new_id:
            if group_ids:
                self.editGroup(new_id, group_ids)
            if attachment_ids:
                self.editAttachment(new_id, attachment_ids)
    
    def edit(self, item_id, item):
        transaction_item = {c: v for c, v in item.items() if c not in ['attachments', 'groups']}
        set_clause = sql.SQL(", ").join(sql.Composed([sql.Identifier(col), sql.SQL(" = "), sql.Placeholder(col)]) for col in transaction_item.keys())
        group_ids = item.get("groups")
        attachment_ids = item.get("attachments")

        try:
            query = sql.SQL("UPDATE {table_name} SET {set_clause} WHERE {id} = {item_id}").format(
                table_name=sql.Identifier(self.table_name),
                set_clause=set_clause,
                id=sql.Identifier("id"),
                item_id=sql.Placeholder('item_id')
            )
            
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                print("query", query.as_string(self.conn))
                print({**transaction_item, 'item_id': item_id})
                cur.execute(query, {**transaction_item, 'item_id': item_id})
            self.conn.commit()
        except (psycopg2.DatabaseError, psycopg2.IntegrityError) as ex:
            print(ex)
            self.conn.rollback()
        
        if group_ids:
            self.editGroup(item_id, group_ids)
        if attachment_ids:
            self.editAttachment(item_id, attachment_ids)
    
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
    
    def editAttachment(self, item_id, attachment_ids=[]):
        try:
            query = sql.SQL("""
                INSERT INTO {t_attachment_junction_table_name} ({transaction_id}, {attachment}) 
                SELECT {item_id}, {attachment_id} 
                FROM unnest({attachment_ids}::int[]) as {attachment_id} 
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM {t_attachment_junction_table_name}
                    WHERE {transaction_id} = {item_id}
                    AND {attachment} = {attachment_id}
                )
            """).format(
                t_attachment_junction_table_name=sql.Identifier(self.t_attachment_junction_table_name),
                transaction_id=sql.Identifier("transaction_id"),
                attachment=sql.Identifier("attachment_id"),
                attachment_id = sql.Identifier("attachment_id"),
                attachment_ids = sql.Placeholder("attachment_ids"),
                item_id=sql.Placeholder('item_id')
            )
            
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                print("query", query.as_string(self.conn))
                print({'attachment_ids': attachment_ids, 'item_id': item_id})
                cur.execute(query, {"attachment_ids": attachment_ids, 'item_id': item_id})
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