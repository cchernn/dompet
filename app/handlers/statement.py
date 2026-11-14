from ..lib.params import Params
from ..models.statement import Statement
from ..db import statement as statement_db
from ..utils.pagination import PaginatedResult, parse_pagination


def _include_inactive(params: Params) -> bool:
    if not params.queryParams:
        return False
    return str(params.queryParams.get("include_inactive", "")).lower() == "true"


def list(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params)
    rows, metadata = statement_db.list_statements(params.user, page, page_size, include_inactive=_include_inactive(params))
    return PaginatedResult([Statement(**row) for row in rows], metadata)


def get(params: Params) -> Statement:
    statement_id = params.pathParams.get("statement_id")
    row = statement_db.get_statement(params.user, statement_id)
    return Statement(**row)


def add(params: Params) -> Statement:
    body = params.body or {}
    row = statement_db.create_statement(params.user, body)
    return Statement(**row)


def edit(params: Params) -> Statement:
    statement_id = params.pathParams.get("statement_id")
    body = params.body or {}
    row = statement_db.update_statement(params.user, statement_id, body)
    return Statement(**row)


def delete(params: Params) -> Statement:
    statement_id = params.pathParams.get("statement_id")
    row = statement_db.deactivate_statement(params.user, statement_id)
    return Statement(**row)
