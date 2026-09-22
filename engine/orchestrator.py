"""The loop that drives a run forward.

Everything is event driven through the mailbox. A tick does four things:
it lets any simulated supplier whose reply is due write back, it reads the
mailbox and advances every negotiation a reply belongs to, it chases anyone
who has gone quiet, and it opens the award gate once nothing is still moving.

A tick is safe to call at any time and does nothing when there is nothing
to do, which is what lets the interface poll it and a scheduler call it.
"""

from __future__ import annotations

import datetime as dt

import psycopg2

from . import coa, config, copy as copytext, mail, negotiator, normalise, qualifier, simulator, store


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

def _run_supplier_for_reference(reference: str) -> dict | None:
    return store.one(
        """
        select rs.* from messages m
        join run_suppliers rs on rs.id = m.run_supplier_id
        where m.reference = %s
        order by m.occurred_at limit 1
        """,
        (reference,),
    )


def _save_file(name: str, data: bytes) -> str:
    row = store.one(
        "insert into files (name, data) values (%s, %s) returning id",
        (name, psycopg2.Binary(data)),
    )
    return row["id"]


def _handle_supplier_reply(inbound: mail.Inbound) -> bool:
    reference = inbound.reference
    if not reference:
        return False

    rs_row = _run_supplier_for_reference(reference)
    if not rs_row:
        return False

    already = store.one(
        "select id from messages where message_id = %s and direction = 'inbound'",
        (inbound.message_id,),
    )
    if already:
        return False

    rs = store.run_supplier(rs_row["id"])
    run = store.run(rs["run_id"])
    ingredient = store.ingredient(run["ingredient_id"])
    spec = store.specification(run["ingredient_id"])

    # 1. read the commercial terms out of the prose
    parsed = negotiator.parse_reply(inbound.body)

    # 2. read and judge any certificate that came with it
    certificate = None
    file_id = None
    if inbound.attachments:
        name, data = inbound.attachments[0]
        file_id = _save_file(name, data)
        measured = coa.read_certificate(data)
        verdict, findings = coa.judge(measured, spec)
        certificate = {
            "measured": measured,
            "verdict": verdict,
            "findings": findings,
            "batch_no": measured.get("batch_no") or "unknown",
            "file_id": file_id,
            "name": name,
        }

    message = store.insert(
        "messages",
        {
            "run_id": rs["run_id"],
            "run_supplier_id": rs["id"],
            "direction": "inbound",
            "kind": "quote" if parsed.get("price") else "question",
            "from_addr": inbound.from_addr,
            "to_addr": inbound.to_addr,
            "subject": inbound.subject,
            "body": inbound.body,
            "reference": reference,
            "message_id": inbound.message_id,
            "raw_headers": store.j(inbound.headers),
            "parsed": store.j(parsed),
            "attachment_path": certificate["name"] if certificate else None,
            "attachment_file_id": file_id,
        },
    )

    if certificate:
        store.insert(
            "coas",
            {
                "run_supplier_id": rs["id"],
                "message_id": message["id"],
                "batch_no": certificate["batch_no"],
                "issued_on": certificate["measured"].get("issued_on"),
                "measured": store.j(certificate["measured"]),
                "findings": store.j(certificate["findings"]),
                "verdict": certificate["verdict"],
                "file_id": file_id,
            },
        )
        failing = [f["line"] for f in certificate["findings"] if f["verdict"] == "fail"]
        store.log(
            rs["run_id"],
            "coa_reader",
            (
                f"{rs['name']} certificate {certificate['batch_no']} "
                + ("passed every line" if not failing else f"failed on {', '.join(failing)}")
            ),
            {"verdict": certificate["verdict"]},
        )

    if not parsed.get("price"):
        _escalate(
            rs=rs,
            kind="supplier_question",
            headline=f"{rs['name']} replied without a price",
            context={
                "supplier": rs["name"],
                "asked": parsed.get("questions") or [],
                "body": inbound.body[:1200],
            },
            options=[
                {"id": "answer", "label": "Answer and keep them in", "consequence": "Sends a reply and waits for a quotation.", "tone": "primary"},
                {"id": "walk", "label": "Close this supplier", "consequence": "Stops chasing them on this enquiry.", "tone": "danger"},
            ],
        )
        return True

    # 3. normalise, so the price can sit beside the others
    normalised = normalise.normalise(
        price=float(parsed["price"]),
        currency=parsed.get("currency") or rs["price_currency"],
        unit=parsed.get("unit") or rs["price_unit"],
        incoterm=parsed.get("incoterm") or rs["incoterm"],
        purity_pct=parsed.get("purity_pct") or float(rs["purity_pct"]),
        origin=rs["country"],
    )

    quote = store.insert(
        "quotes",
        {
            "run_supplier_id": rs["id"],
            "message_id": message["id"],
            "round": int(rs["round"]),
            "price": float(parsed["price"]),
            "currency": parsed.get("currency") or rs["price_currency"],
            "unit": parsed.get("unit") or rs["price_unit"],
            "quantity_kg": parsed.get("quantity_kg"),
            "incoterm": parsed.get("incoterm") or rs["incoterm"],
            "lead_time_days": parsed.get("lead_time_days"),
            "payment_terms": parsed.get("payment_terms"),
            "purity_pct": parsed.get("purity_pct") or float(rs["purity_pct"]),
            "valid_days": parsed.get("valid_days"),
            "usd_per_kg_active": normalised["usd_per_kg_active"],
            "freight_usd_per_kg": normalised["freight_usd_per_kg"],
            "duty_usd_per_kg": normalised["duty_usd_per_kg"],
            "normalisation_note": store.j(normalised["note"]),
        },
    )

    store.execute("update run_suppliers set stage = 'quoted' where id = %s", (rs["id"],))

    # 4. decide the next move
    coa_verdict = certificate["verdict"] if certificate else "not_received"

    if coa_verdict == "fail":
        failing = [f for f in certificate["findings"] if f["verdict"] == "fail"]
        _escalate(
            rs=rs,
            kind="coa_failed",
            headline=f"{rs['name']} certificate {certificate['batch_no']} failed specification",
            context={
                "supplier": rs["name"],
                "batch_no": certificate["batch_no"],
                "findings": certificate["findings"],
                "failing": [f["line"] for f in failing],
                "delivered": normalised["usd_per_kg_active"],
            },
            options=[
                {"id": "reject", "label": "Reject this supplier", "consequence": "Closes the file and tells them why.", "tone": "danger"},
                {"id": "retest", "label": "Ask for a retest", "consequence": "Keeps them in and requests a fresh certificate.", "tone": "primary"},
                {"id": "waive", "label": "Accept with a waiver", "consequence": "Records a documented exception against the specification.", "tone": "plain"},
            ],
        )
        return True

    rivals = _rivals(run["id"], exclude=rs["id"])
    decision = negotiator.decide(
        rs=rs,
        run=run,
        ingredient=ingredient,
        quote={
            "price": float(parsed["price"]),
            "currency": quote["currency"],
            "unit": quote["unit"],
            "incoterm": quote["incoterm"],
            "lead_time_days": quote["lead_time_days"],
            "purity_pct": quote["purity_pct"],
            "payment_terms": quote["payment_terms"],
        },
        delivered=normalised["usd_per_kg_active"],
        ceiling=float(run["guardrails"]["ceiling_usd_per_kg_active"]),
        coa_verdict=coa_verdict,
        rivals=rivals,
        holding_firm=bool(parsed.get("holding_firm")),
    )

    store.log(rs["run_id"], "negotiator", f"{rs['name']}: {decision['move']}. {decision['reasoning']}", decision)

    if decision["move"] == "counter":
        negotiator.send_counter(
            run_supplier_id=rs["id"],
            reference=reference,
            decision=decision,
            quote={
                "currency": quote["currency"],
                "unit": quote["unit"],
                "incoterm": quote["incoterm"],
                "purity_pct": quote["purity_pct"],
                "lead_time_days": quote["lead_time_days"],
                "payment_terms": quote["payment_terms"],
            },
            rivals=rivals,
        )
    elif decision["move"] == "walk":
        store.execute("update run_suppliers set stage = 'walked_away' where id = %s", (rs["id"],))
    elif decision["move"] == "escalate":
        kind = "rounds_exhausted" if int(rs["round"]) >= int(run["guardrails"]["max_rounds"]) else "price_ceiling"
        _escalate(
            rs=rs,
            kind=kind,
            headline=(
                f"{rs['name']} at ${normalised['usd_per_kg_active']:,.2f} per kg, "
                f"ceiling ${float(run['guardrails']['ceiling_usd_per_kg_active']):,.2f}"
            ),
            context={
                "supplier": rs["name"],
                "delivered": normalised["usd_per_kg_active"],
                "ceiling": float(run["guardrails"]["ceiling_usd_per_kg_active"]),
                "round": int(rs["round"]),
                "reasoning": decision["reasoning"],
                "escalate_reason": decision.get("escalate_reason"),
                "guardrails_applied": decision["guardrails_applied"],
            },
            options=[
                {"id": "accept", "label": "Accept their price", "consequence": "Marks this offer agreed and raises the ceiling for this run.", "tone": "plain"},
                {"id": "walk", "label": "Walk away", "consequence": "Closes the file on this supplier.", "tone": "danger"},
                {"id": "hold", "label": "Hold for now", "consequence": "Leaves the offer on the table without agreeing to it.", "tone": "primary"},
            ],
        )
    else:  # accept
        store.execute("update run_suppliers set stage = 'agreed' where id = %s", (rs["id"],))

    return True


def _rivals(run_id: str, exclude: str) -> list[dict]:
    rows = store.query(
        """
        select distinct on (rs.id) rs.id, s.name, q.usd_per_kg_active,
               coalesce(c.verdict, 'not_received') as coa_verdict
        from run_suppliers rs
        join suppliers s on s.id = rs.supplier_id
        join quotes q on q.run_supplier_id = rs.id
        left join coas c on c.run_supplier_id = rs.id
        where rs.run_id = %s and rs.id <> %s
        order by rs.id, q.round desc
        """,
        (run_id, exclude),
    )
    return [
        {
            "name": r["name"],
            "delivered": float(r["usd_per_kg_active"]),
            "coa_verdict": r["coa_verdict"],
        }
        for r in rows
        if r["usd_per_kg_active"] is not None
    ]


def _escalate(*, rs: dict, kind: str, headline: str, context: dict, options: list[dict]) -> None:
    open_already = store.one(
        "select id from approvals where run_id = %s and subject_id = %s and kind = %s and status = 'open'",
        (rs["run_id"], rs["id"], kind),
    )
    if open_already:
        return

    store.insert(
        "approvals",
        {
            "run_id": rs["run_id"],
            "kind": kind,
            "subject_id": rs["id"],
            "headline": headline,
            "context": store.j(context),
            "options": store.j(options),
        },
    )
    store.log(rs["run_id"], "negotiator", f"Escalated to a human: {headline}", {"kind": kind})


# ---------------------------------------------------------------- the tick

def tick(run_id: str | None = None) -> dict:
    did = {"replies_triggered": 0, "inbound_processed": 0, "followups": 0, "gates_opened": 0}

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

    # 2. read the mailbox and advance whatever arrived
    for inbound in mail.fetch_unread():
        tag = config.address_tag(inbound.to_addr)
        if tag != "sourcing":
            continue
        if _handle_supplier_reply(inbound):
            did["inbound_processed"] += 1

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
        where rs.run_id = %s and rs.stage <> 'walked_away'
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

    out.sort(key=lambda x: (-x["score"]["total"], x["delivered"]))
    return out
