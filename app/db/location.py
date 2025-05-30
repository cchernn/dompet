from .base import BaseDatabase
from ..lib.params import Params
from ..utils import config

class LocationDatabase(BaseDatabase):
    def __init__(self, params: Params):
        super().__init__(params)
        self.table_name = config.LOCATIONS_TABLE_NAME
        self.valid_keys = [
            "name",
            "url",
            "google_page_link",
            "google_maps_link",
            "category",
            "access_type",
            "is_active",
        ]
