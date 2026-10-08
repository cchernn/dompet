from ..lib.params import Params
from ..lib.exceptions import InvalidDataException
from ..models.budget_member import BudgetMember
from ..db import budget_member as budget_member_db
from ..utils.pagination import PaginatedResult, parse_pagination


def list(params: Params) -> PaginatedResult:
    budget_id = params.pathParams.get("budget_id")
    page, page_size = parse_pagination(params)
    rows, metadata = budget_member_db.list_members(params.user, budget_id, page, page_size)
    return PaginatedResult([BudgetMember(**row) for row in rows], metadata)


def add(params: Params) -> BudgetMember:
    budget_id = params.pathParams.get("budget_id")
    body = params.body or {}
    username = body.get("username")
    if not username:
        raise InvalidDataException(ValueError("username is required in the request body"))
    row = budget_member_db.add_member(params.user, budget_id, username)
    return BudgetMember(**row)


def delete(params: Params) -> dict:
    budget_id = params.pathParams.get("budget_id")
    member_user_id = params.pathParams.get("member_user_id")
    budget_member_db.remove_member(params.user, budget_id, member_user_id)
    return {"removed": True}
