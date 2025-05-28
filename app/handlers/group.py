from ..lib.params import Params
from ..models.group import Group
from ..db.group import GroupDatabase
from ..utils.decorators import load_db
from ..lib.exceptions import InvalidDataException

@load_db(GroupDatabase)
def list(params: Params, db: GroupDatabase) -> list[Group]:
    query, _ = db.get_query()
    data = db.execute_get(query=query)
    groups = [Group(**t) for t in data]
    return groups

@load_db(GroupDatabase)
def get(params: Params, db: GroupDatabase) -> Group:
    group_id = int(params.pathParams.get("group_id"))
    query, vars = db.get_query(id=group_id)
    data = db.execute_get(query=query, vars=vars, many=False)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    group = Group(**data)
    return group

@load_db(GroupDatabase)
def add(params: Params, db: GroupDatabase) -> Group:
    body = params.body
    user = params.user
    query, vars = db.add_query(body=body, user=user)
    data = db.execute_commit(query=query, vars=vars)
    group = Group(**data)
    return group

@load_db(GroupDatabase)
def edit(params: Params, db: GroupDatabase) -> Group:
    body = params.body
    group_id = int(params.pathParams.get("group_id"))
    query, vars = db.edit_query(id=group_id, body=body)
    data = db.execute_commit(query=query, vars=vars)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    group = Group(**data)
    return group

@load_db(GroupDatabase)
def delete(params: Params, db: GroupDatabase) -> Group:
    group_id = int(params.pathParams.get("group_id"))
    query, vars = db.delete_query(id=group_id)
    data = db.execute_commit(query=query, vars=vars)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    group = Group(**data)
    return group