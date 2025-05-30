from ..lib.params import Params
from ..models.location import Location
from ..db.location import LocationDatabase
from ..utils.decorators import load_db
from ..lib.exceptions import InvalidDataException

@load_db(LocationDatabase)
def list(params: Params, db: LocationDatabase) -> list[Location]:
    query, _ = db.get_query()
    data = db.execute_get(query=query)
    locations = [Location(**t) for t in data]
    return locations

@load_db(LocationDatabase)
def get(params: Params, db: LocationDatabase) -> Location:
    location_id = int(params.pathParams.get("location_id"))
    query, vars = db.get_query(id=location_id)
    data = db.execute_get(query=query, vars=vars, many=False)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    location = Location(**data)
    return location

@load_db(LocationDatabase)
def add(params: Params, db: LocationDatabase) -> Location:
    body = params.body
    query, vars = db.add_query(body=body)
    data = db.execute_commit(query=query, vars=vars)
    location = Location(**data)
    return location

@load_db(LocationDatabase)
def edit(params: Params, db: LocationDatabase) -> Location:
    body = params.body
    location_id = int(params.pathParams.get("location_id"))
    query, vars = db.edit_query(id=location_id, body=body)
    data = db.execute_commit(query=query, vars=vars)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    location = Location(**data)
    return location

@load_db(LocationDatabase)
def delete(params: Params, db: LocationDatabase) -> Location:
    location_id = int(params.pathParams.get("location_id"))
    query, vars = db.delete_query(id=location_id)
    data = db.execute_commit(query=query, vars=vars)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    location = Location(**data)
    return location