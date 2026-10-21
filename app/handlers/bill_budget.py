from ..lib.params import Params
from ..lib.exceptions import InvalidDataException
from ..models.budget import Budget
from ..models.bill_budget import BillBudgetLink
from ..db import bill_budget as bill_budget_db
from ..utils.pagination import PaginatedResult, parse_pagination


def list(params: Params) -> PaginatedResult:
    bill_id = params.pathParams.get("bill_id")
    page, page_size = parse_pagination(params)
    rows, metadata = bill_budget_db.list_bill_budgets(params.user, bill_id, page, page_size)
    return PaginatedResult([Budget(**row) for row in rows], metadata)


def add(params: Params) -> BillBudgetLink:
    bill_id = params.pathParams.get("bill_id")
    body = params.body or {}
    budget_id = body.get("budget_id")
    if not budget_id:
        raise InvalidDataException(ValueError("budget_id is required in the request body"))
    row = bill_budget_db.link_budget(params.user, bill_id, budget_id)
    return BillBudgetLink(**row)


def delete(params: Params) -> dict:
    bill_id = params.pathParams.get("bill_id")
    budget_id = params.pathParams.get("budget_id")
    bill_budget_db.unlink_budget(params.user, bill_id, budget_id)
    return {"unlinked": True}
