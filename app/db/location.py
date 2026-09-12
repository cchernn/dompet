from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic

LOCATION_TYPES = ("physical", "online")


def list_locations(include_inactive: bool = False) -> list[dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.locations"
        if not include_inactive:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY name"
        cursor.execute(query)
        return cursor.fetchall()

    return run_atomic(work)


def get_location(location_id) -> dict:
    def work(cursor):
        cursor.execute("SELECT * FROM dompet.locations WHERE id = %s", (str(location_id),))
        row = cursor.fetchone()
        if not row:
            raise InvalidDataException(ValueError(f"Location not found: {location_id}"))
        return row

    return run_atomic(work)


def create_location(body: dict) -> dict:
    loc_type = body.get("type")
    name = body.get("name")
    if loc_type not in LOCATION_TYPES:
        raise InvalidDataException(ValueError(f"Invalid location type: {loc_type}"))
    if not name:
        raise InvalidDataException(ValueError("name is required"))

    google_maps_url = body.get("google_maps_url")
    url = body.get("url")
    if loc_type == "physical" and not google_maps_url:
        raise InvalidDataException(ValueError("google_maps_url is required for physical locations"))
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
        return cursor.fetchone()

    return run_atomic(work)
