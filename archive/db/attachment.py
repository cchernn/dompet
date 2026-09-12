from .base import BaseDatabase
from ..lib.params import Params
from ..utils import config

class AttachmentDatabase(BaseDatabase):
    def __init__(self, params: Params):
        super().__init__(params)
        self.table_name = config.ATTACHMENTS_TABLE_NAME
        self.valid_keys = [
            "date",
            "name",
            "filename",
            "url",
            "type",
            "is_active",
        ]
        self.filter_keys = {
            "user": ("t", "user", "="),
            "date": ("t", "date", "="),
            "date_from": ("t", "date", ">="),
            "date_to": ("t", "date", "<="),
        }
