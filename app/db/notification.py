from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic, paginate

MAX_NOTIFICATIONS_PER_USER = 200


def list_notifications(user_id, page: int, page_size: int) -> tuple[list[dict], dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.notifications WHERE user_id = %s ORDER BY created_at DESC"
        return paginate(cursor, query, [str(user_id)], page, page_size)

    return run_atomic(work, user_id=user_id)


def create_notification(user_id, body: dict) -> dict:
    notification_type = body.get("type")
    message = body.get("message")
    if notification_type not in ("success", "error", "warning", "info"):
        raise InvalidDataException(ValueError(f"Invalid notification type: {notification_type}"))
    if not message:
        raise InvalidDataException(ValueError("message is required"))

    def work(cursor):
        cursor.execute(
            """
            INSERT INTO dompet.notifications (user_id, type, message, description, entity_type, entity_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                str(user_id), notification_type, message,
                body.get("description"), body.get("entity_type"), body.get("entity_id"),
            ),
        )
        row = cursor.fetchone()

        # Keep the table from growing unbounded -- trim anything beyond the
        # most recent MAX_NOTIFICATIONS_PER_USER for this user, same cap the
        # frontend's local version already enforces.
        cursor.execute(
            """
            DELETE FROM dompet.notifications
            WHERE user_id = %s AND id NOT IN (
                SELECT id FROM dompet.notifications WHERE user_id = %s
                ORDER BY created_at DESC LIMIT %s
            )
            """,
            (str(user_id), str(user_id), MAX_NOTIFICATIONS_PER_USER),
        )
        return row

    return run_atomic(work, user_id=user_id)


def mark_read(user_id, notification_id) -> dict:
    def work(cursor):
        cursor.execute(
            "UPDATE dompet.notifications SET is_read = TRUE WHERE id = %s AND user_id = %s RETURNING *",
            (str(notification_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise InvalidDataException(ValueError(f"Notification not found: {notification_id}"))
        return row

    return run_atomic(work, user_id=user_id)


def mark_all_read(user_id) -> int:
    def work(cursor):
        cursor.execute(
            "UPDATE dompet.notifications SET is_read = TRUE WHERE user_id = %s AND is_read = FALSE",
            (str(user_id),),
        )
        return cursor.rowcount

    return run_atomic(work, user_id=user_id)


def delete_notification(user_id, notification_id) -> dict:
    def work(cursor):
        cursor.execute(
            "DELETE FROM dompet.notifications WHERE id = %s AND user_id = %s RETURNING *",
            (str(notification_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise InvalidDataException(ValueError(f"Notification not found: {notification_id}"))
        return row

    return run_atomic(work, user_id=user_id)
