from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from .Database import load_db, TransactionGroupDatabase

class TransactionGroup(BaseModel):
    id: int = Field(None)
    name: str = Field(...)
    is_active: Optional[bool] = Field(None)

    def serialize(self, method="GET", *args, **kwargs):
        data = super().dict(*args, **kwargs)
        return data

@load_db(TransactionGroupDatabase)
def list(params, db):
    data = db.list()
    items = [TransactionGroup(**dat).serialize() for dat in data]
    return items

@load_db(TransactionGroupDatabase)
def create(params, db):
    body = params.body
    method = params.http_method
    
    item = TransactionGroup(**body)
    item = item.serialize(method=method, exclude_none=True)
    db.add(item)
    
    return {
        "message": "Insert successful"
    }

@load_db(TransactionGroupDatabase)
def get(params, db):
    group_id = params.pathParams.get('group_id')
    data = db.list(item_id=group_id)
    if not data:
        return {}
    item = TransactionGroup(**data[0]).serialize()
    return item

@load_db(TransactionGroupDatabase)
def edit(params, db):
    body = params.body
    group_id = params.pathParams.get('group_id')
    if 'user' in body.keys():
        user_ids = body.get('user')
        user_ids = user_ids.split("|")
        db.editUser(item_id=group_id, user_ids=user_ids)
    else:
        db.edit(item_id=group_id, item=body)

    return {
        "message": "Update successful"
    }

@load_db(TransactionGroupDatabase)
def delete(params, db):
    group_id = params.pathParams.get('group_id')
    db.delete(item_id=group_id)
    return {
        "message": "Delete successful"
    }