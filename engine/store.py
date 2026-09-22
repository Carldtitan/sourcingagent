"""Database access. One connection helper and a set of small readers and writers."""

from __future__ import annotations

import json
import contextlib
import threading
import time
from typing import Any, Iterable

import psycopg2
import psycopg2.extras

from . import config

psycopg2.extras.register_uuid()


_local = threading.local()

# Supabase's pooler drops idle or busy connections now and then. Each thread
# keeps one connection, and a statement that hits a dropped link reconnects
# and runs again rather than failing the negotiation it belongs to.
RETRYABLE = (psycopg2.OperationalError, psycopg2.InterfaceError)


def _connect():
    c = psycopg2.connect(
        config.need("DATABASE_URL"),
        sslmode="require",
        connect_timeout=20,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
    )
    c.autocommit = True
    return c


def _connection():
    c = getattr(_local, "conn", None)
    if c is None or c.closed:
        c = _connect()
        _local.conn = c
    return c


def _drop() -> None:
    c = getattr(_local, "conn", None)
    if c is not None:
        try:
            c.close()
        except Exception:
            pass
    _local.conn = None


def _run(fn):
    last: Exception | None = None
    for attempt in range(4):
        try:
            return fn(_connection())
        except RETRYABLE as error:
            last = error
            _drop()
            time.sleep(0.6 * (attempt + 1))
    raise last  # type: ignore[misc]


@contextlib.contextmanager
def conn():
    """A connection for callers that need one directly."""
    yield _connection()


def query(sql: str, args: Iterable[Any] = ()) -> list[dict]:
    def go(c):
        with c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, tuple(args))
            if cur.description is None:
                return []
            return [dict(r) for r in cur.fetchall()]

    return _run(go)


def one(sql: str, args: Iterable[Any] = ()) -> dict | None:
    rows = query(sql, args)
    return rows[0] if rows else None


def execute(sql: str, args: Iterable[Any] = ()) -> None:
    def go(c):
        with c.cursor() as cur:
            cur.execute(sql, tuple(args))

    _run(go)


def j(value: Any) -> str:
    return json.dumps(value, default=str)


# ------------------------------------------------------------------ readers

def ingredient(ingredient_id: str) -> dict:
    row = one("select * from ingredients where id = %s", (ingredient_id,))
    if not row:
        raise LookupError(f"no ingredient {ingredient_id}")
    return row


def specification(ingredient_id: str) -> dict:
    row = one("select * from specifications where ingredient_id = %s", (ingredient_id,))
    if not row:
        raise LookupError(f"no specification for {ingredient_id}")
    return row


def run(run_id: str) -> dict:
    row = one("select * from runs where id = %s", (run_id,))
    if not row:
        raise LookupError(f"no run {run_id}")
    return row


def suppliers_for(ingredient_id: str) -> list[dict]:
    return query(
        """
        select s.*, si.list_price, si.price_floor, si.price_currency, si.price_unit,
               si.incoterm, si.purity_pct, si.moq_kg, si.lead_time_days, si.coa_fault
        from suppliers s
        join supplier_ingredients si on si.supplier_id = s.id
        where si.ingredient_id = %s
        order by s.name
        """,
        (ingredient_id,),
    )


def run_supplier(run_supplier_id: str) -> dict:
    row = one(
        """
        select rs.*, s.name, s.country, s.kind, s.email_local, s.certs,
               s.stubbornness, s.reply_delay_s, s.reply_style, s.omits_fields,
               si.list_price, si.price_floor, si.price_currency, si.price_unit,
               si.incoterm, si.purity_pct, si.moq_kg, si.lead_time_days, si.coa_fault,
               r.ingredient_id, r.quantity_kg, r.needed_by_days, r.guardrails
        from run_suppliers rs
        join runs r on r.id = rs.run_id
        join suppliers s on s.id = rs.supplier_id
        join supplier_ingredients si
          on si.supplier_id = rs.supplier_id and si.ingredient_id = r.ingredient_id
        where rs.id = %s
        """,
        (run_supplier_id,),
    )
    if not row:
        raise LookupError(f"no run supplier {run_supplier_id}")
    return row


def run_suppliers(run_id: str, shortlisted_only: bool = False) -> list[dict]:
    clause = "and rs.qualified is true" if shortlisted_only else ""
    return query(
        f"""
        select rs.*, s.name, s.country, s.kind, s.email_local, s.certs,
               s.stubbornness, s.reply_delay_s, s.reply_style, s.omits_fields,
               si.list_price, si.price_floor, si.price_currency, si.price_unit,
               si.incoterm, si.purity_pct, si.moq_kg, si.lead_time_days, si.coa_fault
        from run_suppliers rs
        join runs r on r.id = rs.run_id
        join suppliers s on s.id = rs.supplier_id
        join supplier_ingredients si
          on si.supplier_id = rs.supplier_id and si.ingredient_id = r.ingredient_id
        where rs.run_id = %s {clause}
        order by s.name
        """,
        (run_id,),
    )


def latest_quote(run_supplier_id: str) -> dict | None:
    return one(
        "select * from quotes where run_supplier_id = %s order by round desc limit 1",
        (run_supplier_id,),
    )


def quotes_for_run(run_id: str) -> list[dict]:
    return query(
        """
        select q.*, rs.supplier_id, rs.stage, rs.round as rs_round, s.name, s.country
        from quotes q
        join run_suppliers rs on rs.id = q.run_supplier_id
        join suppliers s on s.id = rs.supplier_id
        where rs.run_id = %s
        order by q.created_at
        """,
        (run_id,),
    )


def open_approvals(run_id: str) -> list[dict]:
    return query(
        "select * from approvals where run_id = %s and status = 'open' order by opened_at",
        (run_id,),
    )


def thread(run_supplier_id: str) -> list[dict]:
    return query(
        "select * from messages where run_supplier_id = %s order by occurred_at",
        (run_supplier_id,),
    )


def message_by_reference(reference: str) -> dict | None:
    return one(
        "select * from messages where reference = %s order by occurred_at limit 1",
        (reference,),
    )


# ------------------------------------------------------------------ writers

def log(run_id: str, actor: str, summary: str, detail: dict | None = None) -> None:
    execute(
        "insert into events (run_id, actor, summary, detail) values (%s, %s, %s, %s)",
        (run_id, actor, summary, j(detail) if detail else None),
    )


def insert(table: str, values: dict) -> dict:
    """Insert one row and return it."""
    cols = list(values)
    placeholders = ", ".join(f"%({c})s" for c in cols)
    sql = (
        f"insert into {table} ({', '.join(cols)}) values ({placeholders}) returning *"
    )
    def go(c):
        with c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, values)
            return dict(cur.fetchone())

    return _run(go)


def update(table: str, row_id: Any, values: dict) -> None:
    sets = ", ".join(f"{k} = %({k})s" for k in values)
    args = dict(values)
    args["__id"] = row_id
    execute_named(f"update {table} set {sets} where id = %(__id)s", args)


def execute_named(sql: str, args: dict) -> None:
    def go(c):
        with c.cursor() as cur:
            cur.execute(sql, args)

    _run(go)
