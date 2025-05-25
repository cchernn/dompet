from .base import BaseDatabase
from ..lib.params import Params
from ..utils import config

from psycopg2.sql import SQL, Identifier, Placeholder, Composable

class TransactionGroupDatabase(BaseDatabase):
    def __init__(self, params: Params):
        super().__init__(params)
        self.table_name = config.TRANSACTION_GROUP_TABLE_NAME
    
    def get_query(self, transaction_id: int, group: list = []) -> Composable:
        query = SQL("""
            INSERT INTO {transaction_group_junction_table_name} ({transaction_id_title}, {group_id_title})
            SELECT {transaction_id}, group_id
            FROM unnest({group}::int[]) as group_id_table(group_id)
            WHERE NOT EXISTS (
                SELECT 1
                FROM {transaction_group_junction_table_name}
                WHERE {transaction_id_title} = {transaction_id}
                AND {group_id_title} = group_id_table.group_id
            )
        """).format(
            transaction_group_junction_table_name=Identifier(self.table_name),
            transaction_id_title=Identifier("transaction_id"),
            group_id_title=Identifier("transaction_group_id"),
            transaction_id=Placeholder("transaction_id"),
            group=Placeholder("group"),
        )

        return query, {"group": group, "transaction_id": transaction_id}