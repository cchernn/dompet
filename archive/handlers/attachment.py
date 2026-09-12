from ..lib.params import Params
from ..models.attachment import Attachment
from ..db.attachment import AttachmentDatabase
from ..utils.decorators import load_db
from ..lib.exceptions import InvalidDataException

@load_db(AttachmentDatabase)
def list(params: Params, db: AttachmentDatabase) -> list[Attachment]:
    if params.queryParams:
        query_params = params.queryParams
        query, vars = db.get_query(query_params=query_params)
    else:
        query, vars = db.get_query()
    data = db.execute_get(query=query, vars=vars)
    attachments = [Attachment(**t) for t in data]
    return attachments

@load_db(AttachmentDatabase)
def get(params: Params, db: AttachmentDatabase) -> Attachment:
    attachment_id = int(params.pathParams.get("attachment_id"))
    query, vars = db.get_query(id=attachment_id)
    data = db.execute_get(query=query, vars=vars, many=False)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    attachment = Attachment(**data)
    return attachment

@load_db(AttachmentDatabase)
def add(params: Params, db: AttachmentDatabase) -> Attachment:
    body = params.body
    user = params.user
    query, vars = db.add_query(body=body, user=user)
    data = db.execute_commit(query=query, vars=vars)
    attachment = Attachment(**data)
    return attachment

@load_db(AttachmentDatabase)
def edit(params: Params, db: AttachmentDatabase) -> Attachment:
    body = params.body
    attachment_id = int(params.pathParams.get("attachment_id"))
    query, vars = db.edit_query(id=attachment_id, body=body)
    data = db.execute_commit(query=query, vars=vars)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    attachment = Attachment(**data)
    return attachment

@load_db(AttachmentDatabase)
def delete(params: Params, db: AttachmentDatabase) -> Attachment:
    attachment_id = int(params.pathParams.get("attachment_id"))
    query, vars = db.delete_query(id=attachment_id)
    data = db.execute_commit(query=query, vars=vars)
    if not data:
        raise InvalidDataException("Data not available or user does not have authorization to access the data")
    attachment = Attachment(**data)
    return attachment