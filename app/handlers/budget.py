from typing import List

from ..lib.params import Params
from ..models.budget import Budget
from ..models.transaction import Transaction
from ..db import budget as budget_db
from ..db import transaction_budget as transaction_budget_db


def _include_inactive(params: Params) -> bool:
    if not params.queryParams:
        return False
    return str(params.queryParams.get("include_inactive", "")).lower() == "true"


def list(params: Params) -> list[Budget]:
    rows = budget_db.list_budgets(params.user, include_inactive=_include_inactive(params))
    return [Budget(**row) for row in rows]


def get(params: Params) -> Budget:
    budget_id = params.pathParams.get("budget_id")
    row = budget_db.get_budget(params.user, budget_id)
    return Budget(**row)


def add(params: Params) -> Budget:
    body = params.body or {}
    row = budget_db.create_budget(params.user, body)
    return Budget(**row)


def edit(params: Params) -> Budget:
    budget_id = params.pathParams.get("budget_id")
    body = params.body or {}
    row = budget_db.update_budget(params.user, budget_id, body)
    return Budget(**row)


def delete(params: Params) -> Budget:
    budget_id = params.pathParams.get("budget_id")
    row = budget_db.delete_budget(params.user, budget_id)
    return Budget(**row)


def list_transactions(params: Params) -> List[Transaction]:
    budget_id = params.pathParams.get("budget_id")
    rows = transaction_budget_db.list_budget_transactions(params.user, budget_id)
    return [Transaction(**row) for row in rows]
