"""Apply SQL files to the Supabase database.

Usage:  python scripts/migrate.py supabase/schema.sql supabase/seed.sql
"""

import sys
import pathlib

import psycopg2

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_env() -> dict:
    env = {}
    path = ROOT / ".env"
    if not path.exists():
        raise SystemExit("No .env file. Copy .env.example and fill it in.")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def main() -> None:
    env = load_env()
    dsn = env.get("DATABASE_URL")
    if not dsn:
        raise SystemExit(
            "DATABASE_URL is not set. Supabase project settings, then Database, "
            "then Connection string, session pooler."
        )

    files = sys.argv[1:] or ["supabase/schema.sql", "supabase/seed.sql"]

    conn = psycopg2.connect(dsn, sslmode="require", connect_timeout=20)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for name in files:
                sql = (ROOT / name).read_text(encoding="utf-8")
                cur.execute(sql)
                print(f"applied {name}")
            cur.execute(
                """
                select table_name, (xpath('/row/c/text()',
                  query_to_xml(format('select count(*) as c from %I', table_name),
                  false, true, '')))[1]::text::int as rows
                from information_schema.tables
                where table_schema = 'public'
                order by table_name
                """
            )
            print()
            for table, rows in cur.fetchall():
                print(f"  {table:<22} {rows:>5} rows")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
