from ..lib.params import Params
from ..models.transaction import Transaction
from ..db.transaction import TransactionDatabase
from ..db.transaction_group import TransactionGroupDatabase
from ..db.transaction_attachment import TransactionAttachmentDatabase
from ..utils.decorators import load_db
from ..lib.exceptions import InvalidDataException

@load_db(TransactionDatabase)
def list(params: Params, db: TransactionDatabase) -> list[Transaction]:
    page = int(params.queryParams.get("page", 1))
    query, _ = db.get_query(page=page)
    data = db.execute_get(query=query)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    transactions = [Transaction(**t) for t in data]
    return transactions

@load_db(TransactionDatabase)
def get(params: Params, db: TransactionDatabase) -> Transaction:
    transaction_id = int(params.pathParams.get("transaction_id"))
    query, vars = db.get_query(transaction_id=transaction_id)
    data = db.execute_get(query=query, vars=vars, many=False)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    transaction = Transaction(**data)
    return transaction

@load_db(TransactionDatabase)
def add(params: Params, db: TransactionDatabase) -> Transaction:
    body = params.body
    user = params.user
    query, vars = db.add_query(body=body, user=user)
    data = db.execute_commit(query=query, vars=vars)
    transaction = Transaction(**data)
    return transaction

@load_db(TransactionDatabase)
def edit(params: Params, db: TransactionDatabase) -> Transaction:
    body = params.body
    transaction_id = int(params.pathParams.get("transaction_id"))
    query, vars = db.edit_query(transaction_id=transaction_id, body=body)
    data = db.execute_commit(query=query, vars=vars)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    # edit_transaction_group(params=params)
    # edit_transaction_attachment(params=params)
    transaction = Transaction(**data)
    return transaction

@load_db(TransactionDatabase)
def delete(params: Params, db: TransactionDatabase) -> Transaction:
    transaction_id = int(params.pathParams.get("transaction_id"))
    query, vars = db.delete_query(transaction_id=transaction_id)
    data = db.execute_commit(query=query, vars=vars)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    transaction = Transaction(**data)
    return transaction

@load_db(TransactionGroupDatabase)
def edit_transaction_group(params: Params, db: TransactionGroupDatabase) -> None:
    body = params.body
    transaction_id = int(params.pathParams.get("transaction_id"))
    if 'group' in body.keys():
        group = body["group"].split("|")
        group = [int(b) for b in group]
        query, vars = db.get_query(transaction_id=transaction_id, group=group)
        db.execute_commit(query=query, vars=vars, is_return=False)
    return 

@load_db(TransactionAttachmentDatabase)
def edit_transaction_attachment(params: Params, db: TransactionAttachmentDatabase) -> None:
    body = params.body
    transaction_id = int(params.pathParams.get("transaction_id"))
    if 'attachment' in body.keys():
        attachment = body["attachment"].split("|")
        attachment = [int(b) for b in attachment]
        query, vars = db.get_query(transaction_id=transaction_id, attachment=attachment)
        db.execute_commit(query=query, vars=vars, is_return=False)