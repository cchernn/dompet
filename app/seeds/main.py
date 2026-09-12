from pathlib import Path

from ..utils.db import connect
from ..utils.env import load_local_env

SEEDS_DIR = Path(__file__).parent / "versions"
SEED_VERSIONS_TABLE = "seed_versions"


def ensure_seed_versions_table(cursor) -> None:
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {SEED_VERSIONS_TABLE} (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def get_applied_versions(cursor) -> set[str]:
    cursor.execute(f"SELECT version FROM {SEED_VERSIONS_TABLE}")
    return {row[0] for row in cursor.fetchall()}


def get_pending_seeds(applied: set[str]) -> list[Path]:
    seeds = sorted(SEEDS_DIR.glob("*.sql"))
    return [path for path in seeds if path.stem not in applied]


def run_seed(cursor, path: Path) -> None:
    sql = path.read_text()
    cursor.execute(sql)
    cursor.execute(
        f"INSERT INTO {SEED_VERSIONS_TABLE} (version) VALUES (%s)",
        (path.stem,),
    )


def seed() -> None:
    load_local_env()
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cursor:
                ensure_seed_versions_table(cursor)
                applied = get_applied_versions(cursor)
                pending = get_pending_seeds(applied)

                if not pending:
                    print("No pending seeds.")
                    return

                for path in pending:
                    print(f"Applying seed: {path.name}")
                    run_seed(cursor, path)
                    print(f"Applied seed: {path.name}")

        print("Seeds complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
