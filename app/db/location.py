from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic, paginate
from .operations import row_to_dict, record_operation

LOCATION_TYPES = ("physical", "online")
UPDATABLE_FIELDS = ("name", "google_maps_url", "url")


def list_locations(page: int, page_size: int, include_inactive: bool = False) -> tuple[list[dict], dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.locations"
        if not include_inactive:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY name"
        return paginate(cursor, query, [], page, page_size)

    return run_atomic(work)


def get_location(location_id) -> dict:
    def work(cursor):
        cursor.execute("SELECT * FROM dompet.locations WHERE id = %s", (str(location_id),))
        row = cursor.fetchone()
        if not row:
            raise InvalidDataException(ValueError(f"Location not found: {location_id}"))
        return row

    return run_atomic(work)


def create_location(user_id, body: dict) -> dict:
    loc_type = body.get("type")
    name = body.get("name")
    if loc_type not in LOCATION_TYPES:
        raise InvalidDataException(ValueError(f"Invalid location type: {loc_type}"))
    if not name:
        raise InvalidDataException(ValueError("name is required"))

    google_maps_url = body.get("google_maps_url")
    url = body.get("url")
    if loc_type == "online" and not url:
        raise InvalidDataException(ValueError("url is required for online locations"))

    def work(cursor):
        cursor.execute(
            """
            INSERT INTO dompet.locations (type, name, google_maps_url, url)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (
                loc_type, name,
                google_maps_url if loc_type == "physical" else None,
                url if loc_type == "online" else None,
            ),
        )
        row = cursor.fetchone()
        record_operation(cursor, "location", row["id"], user_id, "CREATE", None, row_to_dict(row))
        return row

    return run_atomic(work, user_id=user_id)


def update_location(user_id, location_id, body: dict) -> dict:
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        cursor.execute("SELECT * FROM dompet.locations WHERE id = %s FOR UPDATE", (str(location_id),))
        existing = cursor.fetchone()
        if not existing:
            raise InvalidDataException(ValueError(f"Location not found: {location_id}"))

        if existing["type"] == "online" and not patch.get("url", existing["url"]):
            raise InvalidDataException(ValueError("url is required for online locations"))

        set_clause = ", ".join(f"{field} = %s" for field in patch)
        cursor.execute(
            f"UPDATE dompet.locations SET {set_clause}, updated_at = NOW() WHERE id = %s RETURNING *",
            (*patch.values(), str(location_id)),
        )
        after = cursor.fetchone()
        record_operation(cursor, "location", location_id, user_id, "UPDATE", row_to_dict(existing), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)


def delete_location(user_id, location_id) -> dict:
    def work(cursor):
        cursor.execute("SELECT * FROM dompet.locations WHERE id = %s FOR UPDATE", (str(location_id),))
        before = cursor.fetchone()
        if not before:
            raise InvalidDataException(ValueError(f"Location not found: {location_id}"))

        cursor.execute(
            "UPDATE dompet.locations SET is_active = FALSE, updated_at = NOW() WHERE id = %s RETURNING *",
            (str(location_id),),
        )
        after = cursor.fetchone()
        record_operation(cursor, "location", location_id, user_id, "DEACTIVATE", row_to_dict(before), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)
