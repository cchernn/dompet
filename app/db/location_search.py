from ..utils.db import run_atomic, paginate, like_pattern


def search_locations(
    user_id, page: int, page_size: int, q: str = None, owner: str = None, location_type: str = None
) -> tuple[list[dict], dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.vw_locations WHERE 1=1"
        params = []
        if q:
            query += " AND name ILIKE %s"
            params.append(like_pattern(q))
        if owner:
            if owner.lower() == "null":
                query += " AND user_id IS NULL"
            else:
                query += " AND user_id = %s"
                params.append(owner)
        if location_type:
            query += " AND type = %s"
            params.append(location_type)
        query += " ORDER BY account_count DESC, name ASC"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)
