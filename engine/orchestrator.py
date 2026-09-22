"""The loop that drives a run forward.

Everything is event driven through the mailbox. A tick does four things:
it lets any simulated supplier whose reply is due write back, it reads the
mailbox and advances every negotiation a reply belongs to, it chases anyone
who has gone quiet, and it opens the award gate once nothing is still moving.

A tick is safe to call at any time and does nothing when there is nothing
to do, which is what lets the interface poll it and a scheduler call it.
"""

from __future__ import annotations

import concurrent.futures
import os
import time

from . import config, graph, mail, negotiator, normalise, qualifier, simulator, store


DEFAULT_GUARDRAILS = {
    "max_rounds": 3,
    "max_order_value_usd": 250_000,
    "followup_after_seconds": 90,
}


# -------------------------------------------------------------- starting up

def start_run(*, ingredient_id: str, quantity_kg: float, needed_by_days: int) -> str:
    ingredient = store.ingredient(ingredient_id)
    spec = store.specification(ingredient_id)
    cost_model = store.one("select * from cost_model where id = 'aonic-complete'")

    ceiling = normalise.ceiling_for(ingredient, cost_model)

    guardrails = dict(DEFAULT_GUARDRAILS)
    guardrails["ceiling_usd_per_kg_active"] = ceiling
    guardrails["max_lead_time_days"] = min(
        int(needed_by_days), int(spec["max_lead_time_days"])
    )

    run = store.insert(
        "runs",
        {
            "ingredient_id": ingredient_id,
            "quantity_kg": quantity_kg,
            "needed_by_days": needed_by_days,
            "status": "qualifying",
            "guardrails": store.j(guardrails),
        },
    )

    store.log(
        run["id"],
        "human",
        f"Brief opened: {quantity_kg:,.0f} kg of {ingredient['name']} within {needed_by_days} days",
        {
            "ceiling_usd_per_kg_active": ceiling,
            "ceiling_derivation": (
                f"${float(ingredient['cost_budget_usd_per_pouch']):.5f} of ingredient cost "
                f"per pouch divided by "
                f"{float(ingredient['dose_mg']) * int(cost_model['servings_per_pouch']) / 1000:.3f} g "
                f"of {ingredient['name']} in a pouch"
            ),
        },
    )

    qualifier.qualify_run(run["id"])
    return run["id"]


# -------------------------------------------------------------- inbound mail

def _is_ours(inbound: mail.Inbound) -> bool:
    """A reply we should handle: addressed to the buyer, carrying a known reference."""
    if config.address_tag(inbound.to_addr) != "sourcing" or not inbound.reference:
        return False
    known = store.one(
        "select 1 as ok from messages where reference = %s and direction = 'outbound' limit 1",
        (inbound.reference,),
    )
    if not known:
        return False
    already = store.one(
        "select 1 as ok from messages where message_id = %s and direction = 'inbound'",
        (inbound.message_id,),
    )
    return not already


# ---------------------------------------------------------------- the tick

# A serverless function on Vercel's free plan is stopped at 60 seconds. A tick
# stops starting new work once it has spent this long, and anything it did not
# reach waits for the next tick. Locally there is no such limit.
TICK_BUDGET_SECONDS = float(os.environ.get("TICK_BUDGET_SECONDS", "40"))


def tick(run_id: str | None = None) -> dict:
    started = time.monotonic()
    did = {"replies_triggered": 0, "inbound_processed": 0, "followups": 0, "gates_opened": 0}

    def out_of_time() -> bool:
        return time.monotonic() - started > TICK_BUDGET_SECONDS

    # 1. let any simulated supplier whose reply is due write back
    for row in store.query(
        """
        select rs.id, rs.run_id, s.reply_delay_s, m.reference, m.message_id, m.kind,
               extract(epoch from (now() - m.occurred_at)) as waited
        from messages m
        join run_suppliers rs on rs.id = m.run_supplier_id
        join suppliers s on s.id = rs.supplier_id
        where m.direction = 'outbound'
          and m.kind in ('rfq', 'followup', 'counter', 'retest')
          and (%s::uuid is null or rs.run_id = %s::uuid)
          and not exists (
            select 1 from messages r
            where r.run_supplier_id = rs.id and r.direction = 'inbound'
              and r.occurred_at > m.occurred_at
          )
        order by m.occurred_at
        """,
        (run_id, run_id),
    ):
        if out_of_time():
            break
        if float(row["waited"]) < float(row["reply_delay_s"]):
            continue
        # a supplier answers each of our messages once
        simulator.respond(
            run_supplier_id=row["id"],
            inbound_kind=row["kind"],
            reference=row["reference"],
            in_reply_to=row["message_id"],
        )
        did["replies_triggered"] += 1

    # 2. read the mailbox and run every reply through the LangGraph reply graph.
    #    Replies from different suppliers are independent, so they run side by
    #    side. Each is marked read only once the graph has finished with it.
    if not out_of_time():
        unread = mail.fetch_unread(limit=40)
        ours = [m for m in unread if _is_ours(m)]
        handled = [m.uid for m in unread if m not in ours]

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(graph.handle_reply, m): m for m in ours[:8]}
            for future in concurrent.futures.as_completed(futures):
                inbound = futures[future]
                try:
                    future.result()
                    handled.append(inbound.uid)
                    did["inbound_processed"] += 1
                except Exception as error:  # leave it unread and try again next tick
                    store.log(
                        store.one(
                            "select run_id from messages where reference = %s limit 1",
                            (inbound.reference,),
                        )["run_id"],
                        "negotiator",
                        f"Could not process a reply yet, will retry: {type(error).__name__}",
                        {"error": str(error)[:400]},
                    )
        mail.mark_seen(handled)

    # 3. chase anyone who has gone quiet
    for row in store.query(
        """
        select rs.id, rs.run_id, m.reference,
               extract(epoch from (now() - m.occurred_at)) as waited,
               r.guardrails
        from messages m
        join run_suppliers rs on rs.id = m.run_supplier_id
        join runs r on r.id = rs.run_id
        where m.direction = 'outbound' and m.kind = 'rfq'
          and rs.stage = 'rfq_sent'
          and (%s::uuid is null or rs.run_id = %s::uuid)
          and not exists (
            select 1 from messages f
            where f.run_supplier_id = rs.id and f.kind = 'followup'
          )
        """,
        (run_id, run_id),
    ):
        if out_of_time():
            break
        window = float(row["guardrails"].get("followup_after_seconds", 90))
        if float(row["waited"]) < window:
            continue
        negotiator.send_followup(
            run_supplier_id=row["id"],
            reference=row["reference"],
            days_quiet=2,
        )
        did["followups"] += 1

    # 4. open the award gate once nothing is still moving
    for row in store.query(
        "select id from runs where status = 'negotiating' and (%s::uuid is null or id = %s::uuid)",
        (run_id, run_id),
    ):
        if _maybe_open_award(row["id"]):
            did["gates_opened"] += 1

    return did


def _maybe_open_award(run_id: str) -> bool:
    moving = store.one(
        """
        select count(*) as n from run_suppliers
        where run_id = %s and stage in ('rfq_sent', 'countered', 'silent')
        """,
        (run_id,),
    )
    if int(moving["n"]) > 0:
        return False

    open_gates = store.one(
        "select count(*) as n from approvals where run_id = %s and status = 'open'",
        (run_id,),
    )
    if int(open_gates["n"]) > 0:
        return False

    table = comparison(run_id)
    if not table:
        return False

    already = store.one(
        "select id from approvals where run_id = %s and kind = 'gate_award'",
        (run_id,),
    )
    if already:
        return False

    winner = table[0]
    store.insert(
        "approvals",
        {
            "run_id": run_id,
            "kind": "gate_award",
            "subject_id": winner["run_supplier_id"],
            "headline": (
                f"Recommend {winner['supplier']} at ${winner['delivered']:,.2f} per kg delivered"
            ),
            "context": store.j({"table": table}),
            "options": store.j(
                [
                    {"id": "approve", "label": "Approve and send the close", "consequence": "Sends the closing email and ends the run.", "tone": "primary"},
                    {"id": "hold", "label": "Hold", "consequence": "Leaves the run open with nothing agreed.", "tone": "plain"},
                ]
            ),
        },
    )
    store.execute("update runs set status = 'awaiting_award' where id = %s", (run_id,))
    store.log(run_id, "normaliser", f"Ranked {len(table)} offers. {winner['supplier']} leads.")
    return True


# ------------------------------------------------------------- comparison

def comparison(run_id: str) -> list[dict]:
    """The ranked table of offers for one run."""
    run = store.run(run_id)
    spec = store.specification(run["ingredient_id"])
    rows = store.query(
        """
        select distinct on (rs.id)
               rs.id as run_supplier_id, rs.stage, rs.round,
               s.name, s.country, s.kind, s.certs,
               q.price, q.currency, q.unit, q.incoterm, q.lead_time_days,
               q.purity_pct, q.payment_terms, q.usd_per_kg_active,
               q.freight_usd_per_kg, q.duty_usd_per_kg, q.normalisation_note,
               c.verdict as coa_verdict, c.batch_no, c.findings
        from run_suppliers rs
        join suppliers s on s.id = rs.supplier_id
        join quotes q on q.run_supplier_id = rs.id
        left join coas c on c.run_supplier_id = rs.id
        where rs.run_id = %s
        order by rs.id, q.round desc
        """,
        (run_id,),
    )
    if not rows:
        return []

    best = min(float(r["usd_per_kg_active"]) for r in rows)
    out = []
    for r in rows:
        delivered = float(r["usd_per_kg_active"])
        scored = normalise.score(
            delivered=delivered,
            best_delivered=best,
            lead_time_days=r["lead_time_days"],
            max_lead_time_days=int(run["guardrails"]["max_lead_time_days"]),
            coa_verdict=r["coa_verdict"] or "not_received",
            certs=r["certs"],
            required_certs=spec["required_certs"],
        )
        out.append(
            {
                "run_supplier_id": str(r["run_supplier_id"]),
                "supplier": r["name"],
                "country": r["country"],
                "kind": r["kind"],
                "quoted": f"{r['currency']} {float(r['price']):,.2f} per {r['unit']} {r['incoterm']}",
                "delivered": delivered,
                "lead_time_days": r["lead_time_days"],
                "purity_pct": float(r["purity_pct"]) if r["purity_pct"] else None,
                "payment_terms": r["payment_terms"],
                "coa_verdict": r["coa_verdict"] or "not_received",
                "batch_no": r["batch_no"],
                "rounds": int(r["round"]),
                "stage": r["stage"],
                "score": scored,
                "normalisation": r["normalisation_note"],
            }
        )

    out.sort(key=lambda x: (x["stage"] == "walked_away", -x["score"]["total"], x["delivered"]))
    return out
