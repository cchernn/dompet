import uuid
from typing import Optional

from ..lib.exceptions import InvalidDataException


def parse_owner_filter(value: Optional[str], allow_null: bool = True) -> Optional[str]:
    if not value:
        return None
    if allow_null and value.lower() == "null":
        return "null"
    try:
        return str(uuid.UUID(value))
    except ValueError:
        expected = "a UUID or 'null'" if allow_null else "a UUID"
        raise InvalidDataException(ValueError(f"user_id must be {expected}: {value}"))
