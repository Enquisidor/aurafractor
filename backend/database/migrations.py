"""
Database migration helpers.

Applies schema.sql and tracks applied migrations in a migrations table.
Run with: python -m database.migrations
"""

import os
import logging
from pathlib import Path

import psycopg2

logger = logging.getLogger(__name__)

SCHEMA_FILE = Path(__file__).parent.parent / 'schema.sql'


def get_conn():
    """Return a direct psycopg2 connection for migration use."""
    return psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://localhost/music_separation'))


def ensure_migrations_table(conn) -> None:
    """Create migrations tracking table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()


def has_migration(conn, name: str) -> bool:
    """Check if a migration has already been applied."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM schema_migrations WHERE name = %s", (name,))
        return cur.fetchone() is not None


def apply_schema(conn) -> None:
    """Apply the base schema.sql if not yet applied."""
    migration_name = 'base_schema'
    if has_migration(conn, migration_name):
        logger.info('Migration %s already applied, skipping.', migration_name)
        return

    logger.info('Applying base schema from %s', SCHEMA_FILE)
    sql = SCHEMA_FILE.read_text()
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute(
            "INSERT INTO schema_migrations (name) VALUES (%s)",
            (migration_name,),
        )
    conn.commit()
    logger.info('Base schema applied successfully.')


def run_migrations() -> None:
    """Entry point: apply all pending migrations."""
    logging.basicConfig(level=logging.INFO)
    conn = get_conn()
    try:
        ensure_migrations_table(conn)
        apply_schema(conn)
    finally:
        conn.close()


if __name__ == '__main__':
    run_migrations()
