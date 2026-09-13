from ..lib.params import Params
from ..lib.exceptions import InvalidDataException
from ..models.budget import Budget
from ..models.transaction_budget import TransactionBudgetLink
from ..db import transaction_budget as transaction_budget_db


def list(params: Params) -> list[Budget]:
    transaction_id = params.pathParams.get("transaction_id")
    rows = transaction_budget_db.list_transaction_budgets(params.user, transaction_id)
    return [Budget(**row) for row in rows]


def add(params: Params) -> TransactionBudgetLink:
    transaction_id = params.pathParams.get("transaction_id")
    body = params.body or {}
    budget_id = body.get("budget_id")
    if not budget_id:
        raise InvalidDataException(ValueError("budget_id is required in the request body"))
    row = transaction_budget_db.link_budget(params.user, transaction_id, budget_id)
    return TransactionBudgetLink(**row)


def delete(params: Params) -> dict:
    transaction_id = params.pathParams.get("transaction_id")
    budget_id = params.pathParams.get("budget_id")
    transaction_budget_db.unlink_budget(params.user, transaction_id, budget_id)
    return {"unlinked": True}
