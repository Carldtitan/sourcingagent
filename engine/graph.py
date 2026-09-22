"""The reply graph: what happens when a supplier writes back.

Every supplier reply runs through this LangGraph state graph. Each node does
one job and writes its result into the shared state, and the edges route on
what the earlier nodes found.

    load ─> parse ─> read_certificate ─> record ─┬─> no price ──────> escalate_question
                                                  ├─> certificate fail ─> escalate_certificate
                                                  └─> normalise ─> decide ─> act

Two nodes call a language model: parse, which reads the supplier's prose, and
read_certificate, which reads the PDF. The decide node asks the model for a
move and then lets the guardrails overrule it. Everything else is fixed code,
so the parts of a run that must be exact are exact.
"""

from __future__ import annotations

from typing import Any, TypedDict

import psycopg2
from langgraph.graph import END, START, StateGraph

from . import coa, mail, negotiator, normalise, store


class ReplyState(TypedDict, total=False):
    inbound: mail.Inbound
    reference: str
    rs: dict
    run: dict
    ingredient: dict
    spec: dict
    parsed: dict
    certificate: dict | None
    message: dict
    quote: dict
    normalised: dict
    rivals: list[dict]
    decision: dict
    outcome: str


# ----------------------------------------------------------------- nodes

def load(state: ReplyState) -> ReplyState:
    row = store.one(
        """
        select rs.id from messages m
        join run_suppliers rs on rs.id = m.run_supplier_id
        where m.reference = %s
        order by m.occurred_at limit 1
        """,
        (state["reference"],),
    )
    rs = store.run_supplier(row["id"])
    run = store.run(rs["run_id"])
    return {
        "rs": rs,
        "run": run,
        "ingredient": store.ingredient(run["ingredient_id"]),
        "spec": store.specification(run["ingredient_id"]),
    }


def parse(state: ReplyState) -> ReplyState:
    return {"parsed": negotiator.parse_reply(state["inbound"].body)}


def read_certificate(state: ReplyState) -> ReplyState:
    inbound = state["inbound"]
    if not inbound.attachments:
        return {"certificate": None}

    name, data = inbound.attachments[0]
    file_row = store.one(
        "insert into files (name, data) values (%s, %s) returning id",
        (name, psycopg2.Binary(data)),
    )
    measured = coa.read_certificate(data)
    verdict, findings = coa.judge(measured, state["spec"])
    return {
        "certificate": {
            "name": name,
            "file_id": file_row["id"],
            "measured": measured,
            "verdict": verdict,
            "findings": findings,
            "batch_no": measured.get("batch_no") or "unknown",
        }
    }


def record(state: ReplyState) -> ReplyState:
    inbound, rs, parsed = state["inbound"], state["rs"], state["parsed"]
    certificate = state.get("certificate")

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
            "reference": state["reference"],
            "message_id": inbound.message_id,
            "raw_headers": store.j(inbound.headers),
            "parsed": store.j(parsed),
            "attachment_path": certificate["name"] if certificate else None,
            "attachment_file_id": certificate["file_id"] if certificate else None,
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
                "file_id": certificate["file_id"],
            },
        )
        failing = [f["line"] for f in certificate["findings"] if f["verdict"] == "fail"]
        store.log(
            rs["run_id"],
            "coa_reader",
            f"{rs['name']} certificate {certificate['batch_no']} "
            + ("passed every line" if not failing else f"failed on {', '.join(failing)}"),
            {"verdict": certificate["verdict"]},
        )

    return {"message": message}


def normalise_quote(state: ReplyState) -> ReplyState:
    rs, parsed = state["rs"], state["parsed"]

    currency = parsed.get("currency") or rs["price_currency"]
    unit = parsed.get("unit") or rs["price_unit"]
    incoterm = parsed.get("incoterm") or rs["incoterm"]
    purity = parsed.get("purity_pct") or float(rs["purity_pct"])

    result = normalise.normalise(
        price=float(parsed["price"]),
        currency=currency,
        unit=unit,
        incoterm=incoterm,
        purity_pct=purity,
        origin=rs["country"],
    )

    quote = store.insert(
        "quotes",
        {
            "run_supplier_id": rs["id"],
            "message_id": state["message"]["id"],
            "round": int(rs["round"]),
            "price": float(parsed["price"]),
            "currency": currency,
            "unit": unit,
            "quantity_kg": parsed.get("quantity_kg"),
            "incoterm": incoterm,
            "lead_time_days": parsed.get("lead_time_days"),
            "payment_terms": parsed.get("payment_terms"),
            "purity_pct": purity,
            "valid_days": parsed.get("valid_days"),
            "usd_per_kg_active": result["usd_per_kg_active"],
            "freight_usd_per_kg": result["freight_usd_per_kg"],
            "duty_usd_per_kg": result["duty_usd_per_kg"],
            "normalisation_note": store.j(result["note"]),
        },
    )
    store.execute("update run_suppliers set stage = 'quoted' where id = %s", (rs["id"],))
    return {"normalised": result, "quote": quote}


def decide(state: ReplyState) -> ReplyState:
    rs, run, quote = state["rs"], state["run"], state["quote"]
    certificate = state.get("certificate")

    rivals = _rivals(run["id"], exclude=rs["id"])
    decision = negotiator.decide(
        rs=rs,
        run=run,
        ingredient=state["ingredient"],
        quote={
            "price": float(quote["price"]),
            "currency": quote["currency"],
            "unit": quote["unit"],
            "incoterm": quote["incoterm"],
            "lead_time_days": quote["lead_time_days"],
            "purity_pct": quote["purity_pct"],
            "payment_terms": quote["payment_terms"],
        },
        delivered=state["normalised"]["usd_per_kg_active"],
        ceiling=float(run["guardrails"]["ceiling_usd_per_kg_active"]),
        coa_verdict=certificate["verdict"] if certificate else _latest_verdict(rs["id"]),
        rivals=rivals,
        holding_firm=bool(state["parsed"].get("holding_firm")),
    )
    store.log(
        rs["run_id"], "negotiator", f"{rs['name']}: {decision['move']}. {decision['reasoning']}", decision
    )
    return {"decision": decision, "rivals": rivals}


def act(state: ReplyState) -> ReplyState:
    rs, run, quote, decision = state["rs"], state["run"], state["quote"], state["decision"]
    move = decision["move"]

    if move == "counter":
        negotiator.send_counter(
            run_supplier_id=rs["id"],
            reference=state["reference"],
            decision=decision,
            quote={
                "currency": quote["currency"],
                "unit": quote["unit"],
                "incoterm": quote["incoterm"],
                "purity_pct": quote["purity_pct"],
                "lead_time_days": quote["lead_time_days"],
                "payment_terms": quote["payment_terms"],
            },
            rivals=state["rivals"],
        )
    elif move == "walk":
        store.execute("update run_suppliers set stage = 'walked_away' where id = %s", (rs["id"],))
    elif move == "accept":
        store.execute("update run_suppliers set stage = 'agreed' where id = %s", (rs["id"],))
    else:
        ceiling = float(run["guardrails"]["ceiling_usd_per_kg_active"])
        delivered = state["normalised"]["usd_per_kg_active"]
        kind = (
            "rounds_exhausted"
            if int(rs["round"]) >= int(run["guardrails"]["max_rounds"])
            else "price_ceiling"
        )
        escalate(
            rs=rs,
            kind=kind,
            headline=f"{rs['name']} at ${delivered:,.2f} per kg, ceiling ${ceiling:,.2f}",
            context={
                "supplier": rs["name"],
                "delivered": delivered,
                "ceiling": ceiling,
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
    return {"outcome": move}


def escalate_question(state: ReplyState) -> ReplyState:
    rs = state["rs"]
    escalate(
        rs=rs,
        kind="supplier_question",
        headline=f"{rs['name']} replied without a price",
        context={
            "supplier": rs["name"],
            "asked": state["parsed"].get("questions") or [],
            "body": state["inbound"].body[:1200],
        },
        options=[
            {"id": "answer", "label": "Answer and keep them in", "consequence": "Sends a reply and waits for a quotation.", "tone": "primary"},
            {"id": "walk", "label": "Close this supplier", "consequence": "Stops chasing them on this enquiry.", "tone": "danger"},
        ],
    )
    return {"outcome": "escalated_question"}


def escalate_certificate(state: ReplyState) -> ReplyState:
    rs, certificate = state["rs"], state["certificate"]
    failing = [f for f in certificate["findings"] if f["verdict"] == "fail"]
    escalate(
        rs=rs,
        kind="coa_failed",
        headline=f"{rs['name']} certificate {certificate['batch_no']} failed specification",
        context={
            "supplier": rs["name"],
            "batch_no": certificate["batch_no"],
            "findings": certificate["findings"],
            "failing": [f["line"] for f in failing],
            "delivered": state["normalised"]["usd_per_kg_active"],
        },
        options=[
            {"id": "reject", "label": "Reject this supplier", "consequence": "Closes the file and tells them why.", "tone": "danger"},
            {"id": "retest", "label": "Ask for a retest", "consequence": "Keeps them in and requests a fresh certificate.", "tone": "primary"},
            {"id": "waive", "label": "Accept with a waiver", "consequence": "Records a documented exception against the specification.", "tone": "plain"},
        ],
    )
    return {"outcome": "escalated_certificate"}


# ----------------------------------------------------------------- routing

def after_record(state: ReplyState) -> str:
    if not state["parsed"].get("price"):
        return "escalate_question"
    return "normalise"


def after_normalise(state: ReplyState) -> str:
    certificate = state.get("certificate")
    if certificate and certificate["verdict"] == "fail":
        return "escalate_certificate"
    return "decide"


# ----------------------------------------------------------------- helpers

def escalate(*, rs: dict, kind: str, headline: str, context: dict, options: list[dict]) -> None:
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


def _latest_verdict(run_supplier_id: Any) -> str:
    row = store.one(
        "select verdict from coas where run_supplier_id = %s order by created_at desc limit 1",
        (run_supplier_id,),
    )
    return row["verdict"] if row else "not_received"


def _rivals(run_id: Any, exclude: Any) -> list[dict]:
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
        {"name": r["name"], "delivered": float(r["usd_per_kg_active"]), "coa_verdict": r["coa_verdict"]}
        for r in rows
        if r["usd_per_kg_active"] is not None
    ]


# ----------------------------------------------------------------- the graph

def build():
    graph = StateGraph(ReplyState)

    graph.add_node("load", load)
    graph.add_node("parse", parse)
    graph.add_node("read_certificate", read_certificate)
    graph.add_node("record", record)
    graph.add_node("normalise", normalise_quote)
    graph.add_node("decide", decide)
    graph.add_node("act", act)
    graph.add_node("escalate_question", escalate_question)
    graph.add_node("escalate_certificate", escalate_certificate)

    graph.add_edge(START, "load")
    graph.add_edge("load", "parse")
    graph.add_edge("parse", "read_certificate")
    graph.add_edge("read_certificate", "record")
    graph.add_conditional_edges("record", after_record, ["normalise", "escalate_question"])
    graph.add_conditional_edges("normalise", after_normalise, ["decide", "escalate_certificate"])
    graph.add_edge("decide", "act")
    graph.add_edge("act", END)
    graph.add_edge("escalate_question", END)
    graph.add_edge("escalate_certificate", END)

    return graph.compile()


REPLY_GRAPH = build()


def handle_reply(inbound: mail.Inbound) -> ReplyState:
    return REPLY_GRAPH.invoke({"inbound": inbound, "reference": inbound.reference})
