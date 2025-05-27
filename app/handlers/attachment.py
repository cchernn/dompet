from ..lib.params import Params
from ..models.attachment import Attachment
from ..db.attachment import AttachmentDatabase
from ..utils.decorators import load_db

@load_db(AttachmentDatabase)
def list(params: Params, db: AttachmentDatabase) -> list[Attachment]:
    query, _ = db.get_query()
    data = db.get_data(query=query)
    attachments = [Attachment(**t) for t in data]
    return attachments