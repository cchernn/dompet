from ..lib.params import Params
from ..models.notification import Notification
from ..db import notification as notification_db
from ..utils.pagination import PaginatedResult, parse_pagination


def list(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params)
    rows, metadata = notification_db.list_notifications(params.user, page, page_size)
    return PaginatedResult([Notification(**row) for row in rows], metadata)


def add(params: Params) -> Notification:
    body = params.body or {}
    row = notification_db.create_notification(params.user, body)
    return Notification(**row)


def mark_read(params: Params) -> Notification:
    notification_id = params.pathParams.get("notification_id")
    row = notification_db.mark_read(params.user, notification_id)
    return Notification(**row)


def mark_all_read(params: Params) -> dict:
    count = notification_db.mark_all_read(params.user)
    return {"marked_read": count}


def delete(params: Params) -> dict:
    notification_id = params.pathParams.get("notification_id")
    notification_db.delete_notification(params.user, notification_id)
    return {"deleted": True}
