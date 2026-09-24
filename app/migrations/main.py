from pathlib import Path

from ..utils.db import connect
from ..utils.env import load_local_env

MIGRATIONS_DIR = Path(__file__).parent / "versions"
SCHEMA_MIGRATIONS_TABLE = "schema_migrations"


def ensure_migrations_table(cursor) -> None:
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA_MIGRATIONS_TABLE} (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def get_applied_versions(cursor) -> set[str]:
    cursor.execute(f"SELECT version FROM {SCHEMA_MIGRATIONS_TABLE}")
    return {row[0] for row in cursor.fetchall()}


def get_pending_migrations(applied: set[str]) -> list[Path]:
    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
    return [path for path in migrations if path.stem not in applied]


def run_migration(cursor, path: Path) -> None:
    sql = path.read_text()
    cursor.execute(sql)
    cursor.execute(
        f"INSERT INTO {SCHEMA_MIGRATIONS_TABLE} (version) VALUES (%s)",
        (path.stem,),
    )


def migrate() -> None:
    load_local_env()
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cursor:
                ensure_migrations_table(cursor)
                applied = get_applied_versions(cursor)
                pending = get_pending_migrations(applied)

                if not pending:
                    print("No pending migrations.")
                    return

                for path in pending:
                    print(f"Applying migration: {path.name}")
                    run_migration(cursor, path)
                    print(f"Applied migration: {path.name}")

        print("Migrations complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
