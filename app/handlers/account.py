from ..lib.params import Params
from ..models.account import Account
from ..db import account as account_db


def _include_inactive(params: Params) -> bool:
    if not params.queryParams:
        return False
    return str(params.queryParams.get("include_inactive", "")).lower() == "true"


def list(params: Params) -> list[Account]:
    rows = account_db.list_accounts(params.user, include_inactive=_include_inactive(params))
    return [Account(**row) for row in rows]


def get(params: Params) -> Account:
    account_id = params.pathParams.get("account_id")
    row = account_db.get_account(params.user, account_id)
    return Account(**row)


def add(params: Params) -> Account:
    body = params.body or {}
    row = account_db.create_account(params.user, body)
    return Account(**row)


def edit(params: Params) -> Account:
    account_id = params.pathParams.get("account_id")
    body = params.body or {}
    row = account_db.update_account(params.user, account_id, body)
    return Account(**row)


def deactivate(params: Params) -> Account:
    account_id = params.pathParams.get("account_id")
    row = account_db.deactivate_account(params.user, account_id)
    return Account(**row)


def reactivate(params: Params) -> Account:
    account_id = params.pathParams.get("account_id")
    row = account_db.reactivate_account(params.user, account_id)
    return Account(**row)
