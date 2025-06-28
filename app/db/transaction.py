from .base import BaseDatabase
from ..lib.params import Params
from ..utils import config

from psycopg2.sql import SQL, Identifier, Placeholder, Composable, Literal, Composed

class TransactionDatabase(BaseDatabase):
    def __init__(self, params: Params):
        super().__init__(params)
        self.table_name = config.TRANSACTIONS_TABLE_NAME
        self.locations_table_name = config.LOCATIONS_TABLE_NAME
        self.group_table_name = config.GROUPS_TABLE_NAME
        self.transaction_group_junction_table_name = config.TRANSACTION_GROUP_TABLE_NAME
        self.attachment_table_name = config.ATTACHMENTS_TABLE_NAME
        self.transaction_attachment_junction_table_name = config.TRANSACTION_ATTACHMENT_TABLE_NAME
        self.valid_keys = [
            "date",
            "name",
            "location",
            "type",
            "amount",
            "currency",
            "payment_method",
            "category",
            "is_active",
        ]
        self.filter_keys = {
            "user": ("t", "user"),
            "date": ("t", "date"),
            "name": ("t", "name"),
            "payment_method": ("t", "payment_method"),
            "category": ("t", "category"),
            "location": ("t", "location"),
            "group": ("ttgroup", "transaction_group_id"),
        }

    def get_query_filter(self, transaction_id: int = None, query_params: dict = {}) -> Composable:
        query = None
        filters = {k: v for k, v in query_params.items() if k in self.filter_keys}
        if transaction_id:
            filters.update({"id": transaction_id})
        if filters:
            query_parts = []
            for k in filters.keys():
                table_alias, column_name = self.filter_keys[k]
                query_parts.append(
                    Composed([Identifier(table_alias, column_name), SQL(" = "), Placeholder(k)])
                )
            query = SQL("WHERE ") + SQL(" AND ").join(query_parts)
        return query, filters

    def get_query(self, transaction_id: int = None, query_params: dict = {}, page: int = None) -> Composable:
        filter_query, filter_vars = self.get_query_filter(transaction_id=transaction_id, query_params=query_params)
        page = query_params.get("page", page)
        if page:
            offset = (int(page) - 1) * self.page_size
        vars = {}

        # get all transaction data
        query = SQL("""
            SELECT 
                t.*, 
                lt.name AS {location_name},
                COALESCE(
                    JSONB_AGG(
                        DISTINCT to_jsonb(tgroup)
                    ) FILTER (WHERE tgroup.id IS NOT NULL),
                    '[]'::jsonb
                ) AS {groups},
                COALESCE(
                    JSONB_AGG(
                        DISTINCT to_jsonb(at)
                    ) FILTER (WHERE at.id IS NOT NULL),
                    '[]'::jsonb
                ) AS {attachments}
            FROM {table_name} t
        """).format(
            table_name=Identifier(self.table_name),
            location_name=Identifier("location_name"),
            groups=Identifier("groups"),
            attachments=Identifier("attachments"),
        )

        # join locations
        query += SQL("""
            LEFT JOIN {location_table_name} AS lt ON t.{location_id} = lt.{location_table_id}
        """).format(
            location_table_name=Identifier(self.locations_table_name),
            location_id=Identifier("location"),
            location_table_id=Identifier("id"),
        )

        # join groups
        query += SQL("""
            LEFT JOIN {transaction_group_junction_table_name} AS ttgroup ON t.{id} = ttgroup.{transaction_id}
            LEFT JOIN {group_table_name} AS tgroup ON tgroup.{group_table_id} = ttgroup.{group_junction_table_id}
        """).format(
            group_table_name=Identifier(self.group_table_name),
            transaction_group_junction_table_name=Identifier(self.transaction_group_junction_table_name),
            id=Identifier("id"),
            transaction_id=Identifier("transaction_id"),
            group_table_id=Identifier("id"),
            group_junction_table_id=Identifier("transaction_group_id"),
        )

        # join attachment
        query += SQL("""
            LEFT JOIN {transaction_attachment_junction_table_name} AS att ON t.{id} = att.{attachment_junction_table_transaction_id}
            LEFT JOIN {attachment_table_name} AS at ON at.{attachment_table_id} = att.{attachment_junction_table_id}
        """).format(
            attachment_table_name=Identifier(self.attachment_table_name),
            transaction_attachment_junction_table_name=Identifier(self.transaction_attachment_junction_table_name),
            id=Identifier("id"),
            attachment_junction_table_transaction_id=Identifier("transaction_id"),
            attachment_table_id=Identifier("id"),
            attachment_junction_table_id=Identifier("attachment_id"),
        )

        # filter by params
        if filter_query:
            query += filter_query
            vars.update(**filter_vars)

        # aggregate and sort
        query += SQL("""
            GROUP BY t.id, lt.name
            ORDER BY t.date DESC, t.id DESC
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

    def add_query(self, body: dict, user: str) -> Composable:
        transaction_body = {k: v for k, v in body.items() if k in self.valid_keys}
        transaction_body.update({'user': str(user)})
        transaction_columns = list(transaction_body.keys())
        transaction_values = list(transaction_body.values())

        query = SQL("""
            INSERT INTO {table_name} ({transaction_columns}) VALUES ({transaction_values}) RETURNING *
        """).format(
            table_name=Identifier(self.table_name),
            transaction_columns=SQL(", ").join(map(Identifier, transaction_columns)),
            transaction_values=SQL(", ").join(Placeholder() for _ in transaction_values)
        )
            
        return query, transaction_values
    
    def edit_query(self, transaction_id: int, body: dict) -> Composable:
        transaction_body = {k: v for k, v in body.items() if k in self.valid_keys}
        set_clause = SQL(", ").join(Composed([Identifier(col), SQL(" = "), Placeholder(col)]) for col in transaction_body.keys())
        if not set_clause.seq:
            set_clause = Composed([Identifier("id"), SQL(" = "), Placeholder("transaction_id")])

        query = SQL("""
            UPDATE {table_name} SET {set_clause} WHERE {id} = {transaction_id} RETURNING *
        """).format(
            table_name=Identifier(self.table_name),
            set_clause=set_clause,
            id=Identifier("id"),
            transaction_id=Placeholder("transaction_id")
        )

        return query, {**transaction_body, "transaction_id": transaction_id}
    
    def delete_query(self, transaction_id: int) -> Composable:
        query = SQL("""
            DELETE FROM {table_name} WHERE {id} = {transaction_id} RETURNING *
        """).format(
            table_name=Identifier(self.table_name),
            id=Identifier("id"),
            transaction_id=Placeholder("transaction_id")
        )

        return query, {"transaction_id": transaction_id}