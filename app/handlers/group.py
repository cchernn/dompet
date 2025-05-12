from ..lib.params import Params
from ..models.group import Group
from ..db.group import GroupDatabase
from ..utils.decorators import load_db

@load_db(GroupDatabase)
def list(params: Params, db: GroupDatabase) -> list[Group]:
    query = db.get_query()
    data = db.get_data(query=query)
    groups = [Group(**t) for t in data]
    return groups