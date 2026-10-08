from ..lib.params import Params
from ..models.user import User
from ..db import user as user_db


def get_me(params: Params) -> User:
    row = user_db.get_profile(params.user)
    return User(**row)


def add(params: Params) -> User:
    body = params.body or {}
    row = user_db.create_profile(params.user, body)
    return User(**row)


def edit_me(params: Params) -> User:
    body = params.body or {}
    row = user_db.update_profile(params.user, body)
    return User(**row)
