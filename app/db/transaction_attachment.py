from .base import BaseDatabase
from ..lib.params import Params
from ..utils import config

from psycopg2.sql import SQL, Identifier, Placeholder, Composable, Literal, Composed

class TransactionAttachmentDatabase(BaseDatabase):
    def __init__(self, params: Params):
        super().__init__(params)
        self.table_name = config.TRANSACTION_ATTACHMENT_TABLE_NAME
    
    def get_query(self, transaction_id: int, attachment: list = []) -> Composable:
        query = SQL("""
            INSERT INTO {transaction_attachment_junction_table_name} ({transaction_id_title}, {attachment_id_title})
            SELECT {transaction_id}, attachment_id
            FROM unnest({attachment}::int[]) as attachment_id_table(attachment_id)
            WHERE NOT EXISTS (
                SELECT 1
                FROM {transaction_attachment_junction_table_name}
                WHERE {transaction_id_title} = {transaction_id}
                AND {attachment_id_title} = attachment_id_table.attachment_id
            )
        """).format(
            transaction_attachment_junction_table_name=Identifier(self.table_name),
            transaction_id_title=Identifier("transaction_id"),
            attachment_id_title=Identifier("attachment_id"),
            transaction_id=Placeholder("transaction_id"),
            attachment=Placeholder("attachment"),
        )

        return query, {"attachment": attachment, "transaction_id": transaction_id}