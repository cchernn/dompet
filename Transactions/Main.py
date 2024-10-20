from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

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
    attachment: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)

    def serialize(self, method="GET", *args, **kwargs):
        data = super().dict(*args, **kwargs)
        if method=="GET":
            data['date'] = data['date'].strftime("%Y-%m-%d")
        return data


def list(params, db):
    data = db.list("transactions")
    items = [Transaction(**dat).serialize() for dat in data]
    return items

def create(params, db):
    body = params.body
    method = params.http_method
    
    item = Transaction(**body)
    item = item.serialize(method=method, exclude_none=True)
    db.add("transactions", item)
    
    return {
        "message": "Insert successful"
    }

def get(params, db):
    transaction_id = params.pathParams.get('transaction_id')
    data = db.list("transactions", where=("id", transaction_id))
    if not data:
        return {}
    item = Transaction(**data[0]).serialize()
    return item

def edit(params, db):
    body = params.body
    transaction_id = params.pathParams.get('transaction_id')
    db.edit("transactions", item_id=transaction_id, item=body)

    return {
        "message": "Update successful"
    }

def delete(params, db):
    transaction_id = params.pathParams.get('transaction_id')
    db.delete("transactions", item_id=transaction_id)
    return {
        "message": "Delete successful"
    }