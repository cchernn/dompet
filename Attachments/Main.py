from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from .Database import AttachmentDatabase
from Database import load_db

class Attachment(BaseModel):
    id: int = Field(None)
    name: str = Field(...)
    filename: str = Field(...)
    date: datetime = Field(...)
    url: str = Field(...)
    type: str = Field(...)
    is_active: Optional[bool] = Field(None)

    def serialize(self, method="GET", *args, **kwargs):
        data = super().dict(*args, **kwargs)
        if method=="GET":
            data['date'] = data['date'].strftime("%Y-%m-%d")
        return data

@load_db(AttachmentDatabase)
def list(params, db):
    data = db.list()
    items = [Attachment(**dat).serialize() for dat in data]
    return items

@load_db(AttachmentDatabase)
def create(params, db):
    body = params.body
    method = params.http_method
    
    ### WIP convert decoded to s3 url
    item = Attachment(**body)
    item = item.serialize(method=method, exclude_none=True)
    db.add(item)
    
    return {
        "message": "Insert successful"
    }

@load_db(AttachmentDatabase)
def get(params, db):
    attachment_id = params.pathParams.get('attachment_id')
    data = db.list(item_id=attachment_id)
    if not data:
        return {}
    item = Attachment(**data[0]).serialize()
    return item

@load_db(AttachmentDatabase)
def edit(params, db):
    body = params.body
    attachment_id = params.pathParams.get('attachment_id')
    ### WIP convert decoded to s3 url
    db.edit(item_id=attachment_id, item=body)

    return {
        "message": "Update successful"
    }

@load_db(AttachmentDatabase)
def delete(params, db):
    attachment_id = params.pathParams.get('attachment_id')
    db.delete(item_id=attachment_id)
    return {
        "message": "Delete successful"
    }