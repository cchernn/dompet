from ..lib.params import Params
from ..models.transaction import Transaction
from ..db.transaction import TransactionDatabase
from ..utils.decorators import load_db

@load_db(TransactionDatabase)
def list(params: Params, db: TransactionDatabase) -> list[Transaction]:
    page = int(params.queryParams.get("page", 1))
    query = db.get_query(page=page)
    data = db.get_data(query=query)
    transactions = [Transaction(**t) for t in data]
    return transactions

@load_db(TransactionDatabase)
def get(params: Params, db: TransactionDatabase) -> Transaction:
    transaction = None
    return transaction