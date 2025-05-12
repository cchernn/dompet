from .base import BaseDatabase
from ..lib.params import Params
from ..utils import config

from psycopg2.sql import SQL, Identifier, Composable, Literal

class TransactionDatabase(BaseDatabase):
    def __init__(self, params: Params):
        super().__init__(params)
        self.page_size = config.PAGE_SIZE
        self.table_name = config.TRANSACTIONS_TABLE_NAME
        self.locations_table_name = config.LOCATIONS_TABLE_NAME
        self.transaction_group_table_name = config.GROUPS_TABLE_NAME
        self.transaction_transaction_group_junction_table_name = config.TRANSACTION_TRANSACTION_GROUP_TABLE_NAME
        self.attachment_table_name = config.ATTACHMENTS_TABLE_NAME
        self.transaction_attachment_junction_table_name = config.TRANSACTION_ATTACHMENT_TABLE_NAME

    def get_query(self, page: int = 1) -> Composable:
        offset = (page - 1) * self.page_size

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
            LEFT JOIN {transaction_transaction_group_junction_table_name} AS ttgroup ON t.{id} = ttgroup.{transaction_id}
            LEFT JOIN {transaction_group_table_name} AS tgroup ON tgroup.{transaction_group_table_id} = ttgroup.{transaction_group_junction_table_id}
        """).format(
            transaction_group_table_name=Identifier(self.transaction_group_table_name),
            transaction_transaction_group_junction_table_name=Identifier(self.transaction_transaction_group_junction_table_name),
            id=Identifier("id"),
            transaction_id=Identifier("transaction_id"),
            transaction_group_table_id=Identifier("id"),
            transaction_group_junction_table_id=Identifier("transaction_group_id"),
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

        # aggregate, sort and paginate
        query += SQL("""
            GROUP BY t.id, lt.name
            ORDER BY t.date DESC, t.id DESC
            LIMIT {limit} OFFSET {offset}
        """).format(
            limit=Literal(self.page_size),
            offset=Literal(offset),
        )
    
        return query
