"""Reading supplier replies and deciding what to send back.

Two jobs live here, and they are deliberately split.

Reading is a language model's job. A quotation arrives as prose written by a
person who answered four of the six questions we asked, in their own order,
in their own units. Nothing regular enough to match with a pattern.

Deciding is shared. The model proposes a move and writes the reasoning a
buyer will read. The guardrails then bind that move: the engine never accepts
a price above the ceiling, never runs past the round limit and never commits
more than the order value allows, whatever the model returns. A model that
argues for breaking a guardrail simply loses.
"""

from __future__ import annotations

import json
import re

from . import config, copy as copytext, jsonio, mail, normalise, store


# ----------------------------------------------------------------- reading

PARSE_PROMPT = """You are reading a raw material supplier's email reply to a
Request for Quotation. Pull out the commercial terms.

Return one JSON object and nothing else:

  price              number, the unit price, digits only
  currency           string, three letters, for example USD or EUR
  unit               string, exactly "kg" or "lb"
  incoterm           string, for example EXW, FOB, CIF or DDP, or null
  quantity_kg        number the price applies to, or null
  moq_kg             number, their minimum order quantity, or null
  lead_time_days     number of days from order to shipment, or null
  payment_terms      string as written, or null
  purity_pct         number, the assay percentage they guarantee, or null
  valid_days         number of days the price holds, or null
  holding_firm       true when they say they cannot go lower, otherwise false
  questions          array of strings, anything they asked us that needs an answer
  missing            array of strings, naming any of the six items above they did not give

Rules. Read only what the supplier states. Never carry a number over from
one field to another. A price written "per lb" stays per lb. If the email
gives no price at all, set price to null.

Email follows.

---
{body}
---
"""


def _json_reply(prompt: str, max_tokens: int = 1400) -> dict:
    return jsonio.ask(prompt, max_tokens=max_tokens)


def parse_reply(body: str) -> dict:
    return _json_reply(PARSE_PROMPT.format(body=body[:8000]))


# ---------------------------------------------------------------- deciding

DECIDE_PROMPT = """You are a sourcing agent negotiating one raw material for a
nutrition company. Decide the next move on this supplier.

THE MATERIAL
  {ingredient}, {quantity_kg:,.0f} kg, needed within {needed_by_days} days.

THIS SUPPLIER
  {supplier_name}, {country}.
  Quoted {currency} {price:,.2f} per {unit} {incoterm}.
  Normalised to ${delivered:,.2f} per kg of active material delivered.
  Lead time {lead_time}.
  Certificate verdict: {coa_verdict}.
  Negotiation round {round_number} of {max_rounds}.
  {holding_note}

WHAT WE CAN PAY
  Ceiling ${ceiling:,.2f} per kg delivered. This comes from the cost the
  finished product can carry, so it cannot be exceeded for any reason.

THE OTHER OFFERS ON THIS ENQUIRY
{rivals}

CHOOSE ONE
  accept    their delivered price is at or under the ceiling and competitive.
  counter   ask for a better price, inside the guardrails.
  escalate  a human has to decide this one.
  walk      close the file on this supplier.

Return one JSON object and nothing else:

  move            one of accept, counter, escalate, walk
  target_price    when countering, the unit price to ask for in THEIR currency
                  and THEIR unit, as a number. Otherwise null.
  reasoning       one or two plain sentences a buyer will read. State the
                  numbers you used. No jargon, no hedging.
  escalate_reason when escalating, one sentence naming what a human must decide.
                  Otherwise null.
"""


def _rival_block(rivals: list[dict]) -> str:
    if not rivals:
        return "  No other supplier has quoted yet."
    lines = []
    for r in sorted(rivals, key=lambda x: x["delivered"]):
        lines.append(
            f"  {r['name']}: ${r['delivered']:,.2f} per kg delivered, "
            f"certificate {r['coa_verdict']}"
        )
    return "\n".join(lines)


def decide(
    *,
    rs: dict,
    run: dict,
    ingredient: dict,
    quote: dict,
    delivered: float,
    ceiling: float,
    coa_verdict: str,
    rivals: list[dict],
    holding_firm: bool,
) -> dict:
    guardrails = run["guardrails"]
    max_rounds = int(guardrails["max_rounds"])
    round_number = int(rs["round"])

    prompt = DECIDE_PROMPT.format(
        ingredient=ingredient["name"],
        quantity_kg=float(run["quantity_kg"]),
        needed_by_days=int(run["needed_by_days"]),
        supplier_name=rs["name"],
        country=rs["country"],
        currency=quote["currency"],
        price=float(quote["price"]),
        unit=quote["unit"],
        incoterm=quote["incoterm"],
        delivered=delivered,
        lead_time=(
            f"{quote['lead_time_days']} days" if quote.get("lead_time_days") else "not stated"
        ),
        coa_verdict=coa_verdict,
        round_number=round_number,
        max_rounds=max_rounds,
        holding_note=(
            "They say they are at their floor and cannot go lower."
            if holding_firm
            else ""
        ),
        ceiling=ceiling,
        rivals=_rival_block(rivals),
    )

    proposed = _json_reply(prompt)
    move = proposed.get("move", "escalate")
    bound: list[str] = []

    # --- the guardrails bind the model, not the other way round ------------

    if coa_verdict == "fail" and move == "accept":
        move = "escalate"
        bound.append("a failed certificate cannot be accepted without a human")

    if move == "accept" and delivered > ceiling:
        move = "escalate"
        bound.append(
            f"${delivered:,.2f} per kg is above the ${ceiling:,.2f} ceiling"
        )

    order_value = delivered * float(run["quantity_kg"])
    if move == "accept" and order_value > float(guardrails["max_order_value_usd"]):
        move = "escalate"
        bound.append(
            f"an order of ${order_value:,.0f} is above the "
            f"${float(guardrails['max_order_value_usd']):,.0f} limit"
        )

    lead = quote.get("lead_time_days")
    if move == "accept" and lead and int(lead) > int(guardrails["max_lead_time_days"]):
        move = "escalate"
        bound.append(f"a {lead} day lead time misses the deadline")

    if move == "counter" and round_number >= max_rounds:
        move = "escalate"
        bound.append(f"round {round_number} of {max_rounds} is the last one")

    target = proposed.get("target_price")
    if move == "counter" and not target:
        move = "escalate"
        bound.append("the agent proposed a counter without naming a price")

    return {
        "move": move,
        "proposed_move": proposed.get("move"),
        "target_supplier_price": float(target) if target else None,
        "reasoning": proposed.get("reasoning", ""),
        "escalate_reason": proposed.get("escalate_reason"),
        "guardrails_applied": bound,
        "delivered": delivered,
        "ceiling": ceiling,
    }


# ----------------------------------------------------------------- sending

def send_rfq(*, run_supplier_id: str) -> str:
    rs = store.run_supplier(run_supplier_id)
    run = store.run(rs["run_id"])
    ingredient = store.ingredient(run["ingredient_id"])
    spec = store.specification(run["ingredient_id"])

    reference = mail.new_reference()
    draft = copytext.rfq(
        supplier={"name": rs["name"]},
        ingredient=ingredient,
        spec=spec,
        run=run,
        reference=reference,
    )

    message_id = mail.send(
        sender=config.buyer_address(),
        to=config.supplier_address(rs["email_local"]),
        subject=draft.subject,
        body=draft.body,
        display_name="Aonic Sourcing",
    )

    store.insert(
        "messages",
        {
            "run_id": rs["run_id"],
            "run_supplier_id": run_supplier_id,
            "direction": "outbound",
            "kind": "rfq",
            "from_addr": config.buyer_address(),
            "to_addr": config.supplier_address(rs["email_local"]),
            "subject": draft.subject,
            "body": draft.body,
            "reference": reference,
            "message_id": message_id,
            "agent_note": store.j(
                {
                    "why": "Opening Request for Quotation, sent after the buyer approved the shortlist.",
                    "specification_sent": True,
                }
            ),
        },
    )

    store.execute(
        "update run_suppliers set stage = 'rfq_sent', last_contact_at = now() where id = %s",
        (run_supplier_id,),
    )
    store.log(run["id"], "negotiator", f"Request for Quotation sent to {rs['name']}")
    return reference


def send_followup(*, run_supplier_id: str, reference: str, days_quiet: int) -> None:
    rs = store.run_supplier(run_supplier_id)
    run = store.run(rs["run_id"])
    ingredient = store.ingredient(run["ingredient_id"])

    draft = copytext.followup(
        supplier={"name": rs["name"]},
        ingredient=ingredient,
        run=run,
        reference=reference,
        days_quiet=days_quiet,
    )

    message_id = mail.send(
        sender=config.buyer_address(),
        to=config.supplier_address(rs["email_local"]),
        subject=draft.subject,
        body=draft.body,
        display_name="Aonic Sourcing",
    )

    store.insert(
        "messages",
        {
            "run_id": rs["run_id"],
            "run_supplier_id": run_supplier_id,
            "direction": "outbound",
            "kind": "followup",
            "from_addr": config.buyer_address(),
            "to_addr": config.supplier_address(rs["email_local"]),
            "subject": draft.subject,
            "body": draft.body,
            "reference": reference,
            "message_id": message_id,
            "agent_note": store.j(
                {"why": f"No reply after {days_quiet} days. One chase before closing the file."}
            ),
        },
    )

    store.execute(
        "update run_suppliers set stage = 'silent', last_contact_at = now() where id = %s",
        (run_supplier_id,),
    )
    store.log(run["id"], "chaser", f"Followed up with {rs['name']} after {days_quiet} days of silence")


def send_counter(*, run_supplier_id: str, reference: str, decision: dict, quote: dict, rivals: list[dict]) -> None:
    rs = store.run_supplier(run_supplier_id)
    run = store.run(rs["run_id"])
    ingredient = store.ingredient(run["ingredient_id"])

    target_delivered = normalise.normalise(
        price=decision["target_supplier_price"],
        currency=quote["currency"],
        unit=quote["unit"],
        incoterm=quote["incoterm"],
        purity_pct=quote.get("purity_pct"),
        origin=rs["country"],
    )["usd_per_kg_active"]

    best_rival = min((r["delivered"] for r in rivals), default=None)

    gaps = []
    for field, label in [
        ("lead_time_days", "Lead time in days from purchase order to shipment."),
        ("payment_terms", "Your payment terms."),
        ("incoterm", "The delivery term your price is quoted on."),
    ]:
        if not quote.get(field):
            gaps.append(label)

    draft = copytext.counter(
        supplier={"name": rs["name"]},
        ingredient=ingredient,
        run=run,
        reference=reference,
        their_delivered=decision["delivered"],
        target_delivered=target_delivered,
        ceiling=decision["ceiling"],
        best_rival_delivered=best_rival,
        rival_count=len(rivals),
        round_number=int(rs["round"]) + 1,
        gaps=gaps,
    )

    message_id = mail.send(
        sender=config.buyer_address(),
        to=config.supplier_address(rs["email_local"]),
        subject=draft.subject,
        body=draft.body,
        display_name="Aonic Sourcing",
    )

    store.insert(
        "messages",
        {
            "run_id": rs["run_id"],
            "run_supplier_id": run_supplier_id,
            "direction": "outbound",
            "kind": "counter",
            "from_addr": config.buyer_address(),
            "to_addr": config.supplier_address(rs["email_local"]),
            "subject": draft.subject,
            "body": draft.body,
            "reference": reference,
            "message_id": message_id,
            "agent_note": store.j(decision),
        },
    )

    store.execute(
        """
        update run_suppliers
        set stage = 'countered', round = round + 1, last_contact_at = now()
        where id = %s
        """,
        (run_supplier_id,),
    )
    store.log(
        run["id"],
        "negotiator",
        f"Countered {rs['name']} at {quote['currency']} "
        f"{decision['target_supplier_price']:,.2f} per {quote['unit']}",
        decision,
    )


def send_close(*, run_supplier_id: str, reference: str) -> None:
    rs = store.run_supplier(run_supplier_id)
    run = store.run(rs["run_id"])
    ingredient = store.ingredient(run["ingredient_id"])
    spec = store.specification(run["ingredient_id"])
    quote = store.latest_quote(run_supplier_id)
    certificate = store.one(
        "select * from coas where run_supplier_id = %s order by created_at desc limit 1",
        (run_supplier_id,),
    )

    draft = copytext.close(
        supplier={"name": rs["name"]},
        ingredient=ingredient,
        spec=spec,
        run=run,
        reference=reference,
        agreed_price=float(quote["price"]),
        currency=quote["currency"],
        unit=quote["unit"],
        incoterm=quote["incoterm"],
        delivered=float(quote["usd_per_kg_active"]),
        lead_time_days=int(quote["lead_time_days"] or rs["lead_time_days"]),
        batch_no=certificate["batch_no"] if certificate else None,
    )

    message_id = mail.send(
        sender=config.buyer_address(),
        to=config.supplier_address(rs["email_local"]),
        subject=draft.subject,
        body=draft.body,
        display_name="Aonic Sourcing",
    )

    store.insert(
        "messages",
        {
            "run_id": rs["run_id"],
            "run_supplier_id": run_supplier_id,
            "direction": "outbound",
            "kind": "close",
            "from_addr": config.buyer_address(),
            "to_addr": config.supplier_address(rs["email_local"]),
            "subject": draft.subject,
            "body": draft.body,
            "reference": reference,
            "message_id": message_id,
            "agent_note": store.j({"why": "Buyer approved the award at the second gate."}),
        },
    )

    store.execute("update run_suppliers set stage = 'agreed' where id = %s", (run_supplier_id,))
    store.log(run["id"], "negotiator", f"Closed with {rs['name']}")
