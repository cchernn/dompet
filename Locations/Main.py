from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from .Database import LocationDatabase
from Database import load_db

class Location(BaseModel):
    id: int = Field(None)
    name: str = Field(...)
    url: Optional[str] = Field(None)
    google_page_link: Optional[str] = Field(None)
    google_maps_link: Optional[str] = Field(None)
    category: Optional[str] = Field(None)
    access_type: str = Field(...)
    is_active: Optional[bool] = Field(None)

    def serialize(self, method="GET", *args, **kwargs):
        data = super().dict(*args, **kwargs)
        if method=="GET":
            data['date'] = data['date'].strftime("%Y-%m-%d")
        return data

@load_db(LocationDatabase)
def list(params, db):
    data = db.list()
    items = [Location(**dat).serialize() for dat in data]
    return items

@load_db(LocationDatabase)
def create(params, db):
    body = params.body
    method = params.http_method
    
    ### WIP convert decoded to s3 url
    item = Location(**body)
    item = item.serialize(method=method, exclude_none=True)
    db.add(item)
    
    return {
        "message": "Insert successful"
    }

@load_db(LocationDatabase)
def get(params, db):
    location_id = params.pathParams.get('location_id')
    data = db.list(item_id=location_id)
    if not data:
        return {}
    item = Location(**data[0]).serialize()
    return item

@load_db(LocationDatabase)
def edit(params, db):
    body = params.body
    location_id = params.pathParams.get('location_id')
    db.edit(item_id=location_id, item=body)

    return {
        "message": "Update successful"
    }

@load_db(LocationDatabase)
def delete(params, db):
    location_id = params.pathParams.get('location_id')
    db.delete(item_id=location_id)
    return {
        "message": "Delete successful"
    }