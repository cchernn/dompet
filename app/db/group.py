from .base import BaseDatabase
from ..lib.params import Params
from ..utils import config

class GroupDatabase(BaseDatabase):
    def __init__(self, params: Params):
        super().__init__(params)
        self.table_name = config.GROUPS_TABLE_NAME
        self.valid_keys = [
            "name",
            "is_active",
        ]
        self.filter_keys = {
            "user": {"t", "user"},
        }
