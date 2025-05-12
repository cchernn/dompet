from .base import BaseDatabase
from ..lib.params import Params
from ..utils import config

class LocationDatabase(BaseDatabase):
    def __init__(self, params: Params):
        super().__init__(params)
        self.page_size = config.PAGE_SIZE
        self.table_name = config.LOCATIONS_TABLE_NAME
