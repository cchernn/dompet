from ..lib.params import Params
from ..models.location import Location
from ..db.location import LocationDatabase
from ..utils.decorators import load_db

@load_db(LocationDatabase)
def list(params: Params, db: LocationDatabase) -> list[Location]:
    query = db.get_query()
    data = db.get_data(query=query)
    locations = [Location(**t) for t in data]
    return locations