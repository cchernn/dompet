from ..lib.params import Params
from ..models.transaction import Transaction
from ..db.transaction import TransactionDatabase
from ..utils.decorators import load_db
from ..lib.exceptions import InvalidDataException

@load_db(TransactionDatabase)
def list(params: Params, db: TransactionDatabase) -> list[Transaction]:
    page = int(params.queryParams.get("page", 1))
    query = db.get_query(page=page)
    data = db.get_data(query=query)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    transactions = [Transaction(**t) for t in data]
    return transactions

@load_db(TransactionDatabase)
def get(params: Params, db: TransactionDatabase) -> Transaction:
    transaction_id = int(params.pathParams.get("transaction_id"))
    query = db.get_query(transaction_id=transaction_id)
    data = db.get_data(query=query, vars={'transaction_id': transaction_id}, many=False)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    transaction = Transaction(**data)
    return transaction