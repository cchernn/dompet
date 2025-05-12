from ..lib.params import Params
from ..models.transaction import Transaction
from ..db.transaction import TransactionDatabase
from ..utils.decorators import load_db

@load_db(TransactionDatabase)
def list(params: Params, db: TransactionDatabase) -> list[Transaction]:
    query = db.get_query()
    data = db.get_data(query=query)
    transactions = [Transaction(**t) for t in data]
    return transactions