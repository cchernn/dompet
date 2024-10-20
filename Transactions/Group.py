from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class TransactionGroup(BaseModel):
    id: int = Field(None)
    name: str = Field(...)
    is_active: Optional[bool] = Field(None)

    def serialize(self, method="GET", *args, **kwargs):
        data = super().dict(*args, **kwargs)
        return data

def list(params, db):
    data = db.list("transaction_groups")
    items = [TransactionGroup(**dat).serialize() for dat in data]
    return items

def create(params, db):
    body = params.body
    method = params.http_method
    
    item = TransactionGroup(**body)
    item = item.serialize(method=method, exclude_none=True)
    db.add("transaction_groups", item)
    
    return {
        "message": "Insert successful"
    }

def get(params, db):
    group_id = params.pathParams.get('group_id')
    data = db.list("transaction_groups", where=("id", group_id))
    if not data:
        return {}
    item = TransactionGroup(**data[0]).serialize()
    return item

def edit(params, db):
    body = params.body
    group_id = params.pathParams.get('group_id')
    db.edit("transaction_groups", item_id=group_id, item=body)

    return {
        "message": "Update successful"
    }

def delete(params, db):
    group_id = params.pathParams.get('group_id')
    db.delete("transaction_groups", item_id=group_id)
    return {
        "message": "Delete successful"
    }