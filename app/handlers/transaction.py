from ..lib.params import Params
from ..models.transaction import Transaction
from ..db.transaction import TransactionDatabase
from ..db.transaction_group import TransactionGroupDatabase
from ..db.transaction_attachment import TransactionAttachmentDatabase
from ..utils.decorators import load_db
from ..lib.exceptions import InvalidDataException

@load_db(TransactionDatabase)
def list(params: Params, db: TransactionDatabase) -> list[Transaction]:
    if params.queryParams:
        query_params = params.queryParams
        query, vars = db.get_query(query_params=query_params)
    else:
        query, vars = db.get_query()
    data = db.execute_get(query=query, vars=vars)
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
    transaction_id = data.get("id", None)
    if transaction_id:
        edit_transaction_group(params=params, transaction_id=transaction_id)
        edit_transaction_attachment(params=params, transaction_id=transaction_id)
    else:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
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
    edit_transaction_group(params=params, transaction_id=transaction_id)
    edit_transaction_attachment(params=params, transaction_id=transaction_id)
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
def edit_transaction_group(params: Params, db: TransactionGroupDatabase, transaction_id: int) -> None:
    body = params.body
    if 'group' in body.keys():
        group = body["group"].split("|")
        group = [int(b) for b in group]
        delete_query, delete_vars = db.delete_query(transaction_id=transaction_id, group=group)
        db.execute_commit(query=delete_query, vars=delete_vars, is_return=False)
        insert_query, insert_vars = db.get_query(transaction_id=transaction_id, group=group)
        db.execute_commit(query=insert_query, vars=insert_vars, is_return=False)
    return 

@load_db(TransactionAttachmentDatabase)
def edit_transaction_attachment(params: Params, db: TransactionAttachmentDatabase, transaction_id: int) -> None:
    body = params.body
    if 'attachment' in body.keys():
        attachment = body["attachment"].split("|")
        attachment = [int(b) for b in attachment]
        delete_query, delete_vars = db.delete_query(transaction_id=transaction_id, attachment=attachment)
        db.execute_commit(query=delete_query, vars=delete_vars, is_return=False)
        insert_query, insert_vars = db.get_query(transaction_id=transaction_id, attachment=attachment)
        db.execute_commit(query=insert_query, vars=insert_vars, is_return=False)