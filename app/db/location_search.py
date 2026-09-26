from ..utils.db import run_atomic, paginate, like_pattern


def search_locations(user_id, page: int, page_size: int, q: str = None) -> tuple[list[dict], dict]:
    """Locations themselves are global/unowned (RLS policy is USING (true)),
    but the view's usage_count subquery counts dompet.account_locations,
    which IS RLS-scoped by ownership -- user_id is still needed here purely
    to set app.current_user_id for that nested RLS check, same reasoning as
    app/db/location.py's own create/update/delete functions."""
    def work(cursor):
        query = "SELECT * FROM dompet.vw_locations WHERE 1=1"
        params = []
        if q:
            query += " AND name ILIKE %s"
            params.append(like_pattern(q))
        query += " ORDER BY usage_count DESC, name ASC"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)
