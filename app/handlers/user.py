from ..lib.params import Params
from ..models.user import User
from ..db import user as user_db
from ..utils import s3


def _to_user(row: dict) -> User:
    row = dict(row)
    storage_key = row.pop("avatar_storage_key", None)
    row["avatar_url"] = s3.generate_download_url(storage_key) if storage_key else None
    return User(**row)


def _with_avatar_upload(user_id, body: dict, row: dict) -> dict:
    """create/edit (unlike a plain GET) can also hand back a presigned PUT
    URL for the caller to upload new picture bytes to -- mirrors
    attachment.add's {"attachment":..., "upload_url":...} shape, just on
    both create and edit here since a profile picture can be replaced,
    unlike an attachment's metadata-only edit."""
    content_type = body.get("avatar_content_type")
    upload_url = s3.generate_upload_url(user_db.avatar_storage_key(user_id), content_type) if content_type else None
    return {"user": _to_user(row), "avatar_upload_url": upload_url}


def get_me(params: Params) -> User:
    row = user_db.get_profile(params.user)
    return _to_user(row)


def add(params: Params) -> dict:
    body = params.body or {}
    row = user_db.create_profile(params.user, body)
    return _with_avatar_upload(params.user, body, row)


def edit_me(params: Params) -> dict:
    body = params.body or {}
    row = user_db.update_profile(params.user, body)
    return _with_avatar_upload(params.user, body, row)
