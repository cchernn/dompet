from .base import BaseDatabase
from ..lib.params import Params
from ..utils import config

from psycopg2.sql import SQL, Identifier, Composable, Literal

class TransactionDatabase(BaseDatabase):
    def __init__(self, params: Params):
        super().__init__(params)
        self.page_size = config.PAGE_SIZE

    def get_query(self, page: int = 1) -> Composable:
        offset = (page - 1) * self.page_size

        # get all transaction data
        query = SQL("""
            SELECT t.*, lt.name AS {location_name} FROM {table_name} t
        """).format(
            table_name=Identifier(config.TRANSACTIONS_TABLE_NAME),
            location_name=Identifier("location_name"),
        )

        # join locations
        query += SQL("""
            LEFT JOIN {location_table_name} AS lt ON t.{location_id} = lt.{location_table_id}
        """).format(
            location_table_name=Identifier(config.LOCATIONS_TABLE_NAME),
            location_id=Identifier("location"),
            location_table_id=Identifier("id"),
        )

        # sort and paginate
        query += SQL("""
            ORDER BY t.date DESC, t.id DESC
            LIMIT {limit} OFFSET {offset}
        """).format(
            limit=Literal(self.page_size),
            offset=Literal(offset),
        )
    
        return query
