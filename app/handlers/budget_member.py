from ..lib.params import Params
from ..lib.exceptions import InvalidDataException
from ..models.budget_member import BudgetMember
from ..db import budget_member as budget_member_db


def list(params: Params) -> list[BudgetMember]:
    budget_id = params.pathParams.get("budget_id")
    rows = budget_member_db.list_members(params.user, budget_id)
    return [BudgetMember(**row) for row in rows]


def add(params: Params) -> BudgetMember:
    budget_id = params.pathParams.get("budget_id")
    body = params.body or {}
    member_user_id = body.get("user_id")
    if not member_user_id:
        raise InvalidDataException(ValueError("user_id is required in the request body"))
    row = budget_member_db.add_member(params.user, budget_id, member_user_id)
    return BudgetMember(**row)


def delete(params: Params) -> dict:
    budget_id = params.pathParams.get("budget_id")
    member_user_id = params.pathParams.get("member_user_id")
    budget_member_db.remove_member(params.user, budget_id, member_user_id)
    return {"removed": True}
