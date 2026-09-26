import uuid
from datetime import date, datetime
from decimal import Decimal

from psycopg2.extras import Json


def row_to_dict(row) -> dict:
    """Converts a DB row into a JSON-serializable plain dict, for storing as
    before_data/after_data on an operations log entry."""
    def _jsonable(value):
        if isinstance(value, uuid.UUID):
            return str(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        return value

    return {k: _jsonable(v) for k, v in dict(row).items()}


def record_operation(
    cursor, entity_type: str, entity_id, user_id, operation_type: str,
    before_data: dict = None, after_data: dict = None, metadata: dict = None,
) -> str:
    cursor.execute(
        """
        INSERT INTO dompet.operations
            (entity_type, entity_id, user_id, operation_type, before_data, after_data, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            entity_type,
            str(entity_id),
            str(user_id),
            operation_type,
            Json(before_data) if before_data is not None else None,
            Json(after_data) if after_data is not None else None,
            Json(metadata) if metadata is not None else None,
        ),
    )
    return cursor.fetchone()["id"]
