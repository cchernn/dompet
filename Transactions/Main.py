from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from .Database import TransactionDatabase
from Database import load_db

class Transaction(BaseModel):
    id: int = Field(None)
    date: datetime = Field(...)
    name: str = Field(...)
    location: str = Field(...)
    type: Optional[str] = Field(None)
    amount: Optional[float] = Field(0)
    currency: Optional[str] = Field(None)
    payment_method: str = Field(...)
    category: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)

    def serialize(self, method="GET", *args, **kwargs):
        data = super().dict(*args, **kwargs)
        if method=="GET":
            data['date'] = data['date'].strftime("%Y-%m-%d")
        return data

@load_db(TransactionDatabase)
def list(params, db):
    data = db.list()
    items = [Transaction(**dat).serialize() for dat in data]
    return items

@load_db(TransactionDatabase)
def create(params, db):
    body = params.body
    method = params.http_method
    
    item = Transaction(**body)
    item = item.serialize(method=method, exclude_none=True)
    db.add(item)
    
    return {
        "message": "Insert successful"
    }

@load_db(TransactionDatabase)
def get(params, db):
    transaction_id = params.pathParams.get('transaction_id')
    data = db.list(item_id=transaction_id)
    if not data:
        return {}
    item = Transaction(**data[0]).serialize()
    return item

@load_db(TransactionDatabase)
def edit(params, db):
    body = params.body
    transaction_id = params.pathParams.get('transaction_id')
    if 'group' in body.keys():
        group_ids = body.get('group')
        group_ids = group_ids.split("|")
        db.editGroup(item_id=transaction_id, group_ids=group_ids)
    elif 'attachment' in body.keys():
        attachment_ids = body.get('attachment')
        attachment_ids = attachment_ids.split("|")
        db.editAttachment(item_id=transaction_id, attachment_ids=attachment_ids)
    else:
        db.edit(item_id=transaction_id, item=body)

    return {
        "message": "Update successful"
    }

@load_db(TransactionDatabase)
def delete(params, db):
    transaction_id = params.pathParams.get('transaction_id')
    db.delete(item_id=transaction_id)
    return {
        "message": "Delete successful"
    }