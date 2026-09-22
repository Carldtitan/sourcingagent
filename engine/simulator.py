"""The simulated suppliers.

Twelve companies that do not exist, each on its own email address, each with
a secret price floor, a house style and a habit of leaving something out.
They reply to our agents by real email, so the parser has to work on prose
written by someone else rather than on a payload it produced itself.

A supplier never sees another supplier's price. It only knows its own floor,
how hard it is willing to hold, and what we last offered.
"""

from __future__ import annotations

import datetime as dt
import random

from . import coa, config, copy as copytext, mail, store


def _sign_off(supplier: dict) -> str:
    style = supplier["reply_style"]
    name = {
        "formal": "Sales Department",
        "terse": "Sales",
        "chatty": "Sales Team",
    }[style]
    return f"{name}\n{supplier['name']}\n{supplier['country']}"


def _opening_price(supplier: dict) -> float:
    return float(supplier["list_price"])


def _concede(supplier: dict, current: float, asked: float) -> float:
    """How far a supplier moves when we counter.

    A stubborn supplier gives up a small share of the gap. Nobody goes below
    their floor, and a supplier whose floor sits above what we asked for will
    say so and hold.
    """
    floor = float(supplier["price_floor"])
    if asked >= current:
        return current

    rng = random.Random(f"{supplier['id']}:{current}:{asked}")
    give = (1.0 - float(supplier["stubbornness"])) * rng.uniform(0.55, 1.0)
    moved = current - (current - max(asked, floor)) * give
    return round(max(moved, floor), 2)


# ------------------------------------------------------------ reply writing

def _quote_body(
    *, supplier: dict, ingredient: dict, run: dict, price: float, reference: str, first: bool
) -> str:
    unit = supplier["price_unit"]
    currency = supplier["price_currency"]
    style = supplier["reply_style"]
    omits = set(supplier["omits_fields"] or [])

    lines: list[str] = []

    if style == "chatty":
        lines += [
            "Hi there,",
            "",
            f"Thanks for reaching out about {ingredient['name']}. Good timing, we "
            "have stock on the floor right now.",
            "",
        ]
    elif style == "formal":
        lines += [
            "Dear Sir or Madam,",
            "",
            f"Thank you for your enquiry regarding {ingredient['name']}. We are "
            "pleased to submit the following quotation for your consideration.",
            "",
        ]
    else:
        lines += [f"Quotation as requested.", ""]

    lines += [
        f"Product: {ingredient['name']}, {ingredient['chemical_form']}",
        f"Price: {currency} {price:,.2f} per {unit} {supplier['incoterm']}",
        f"Quantity: {float(run['quantity_kg']):,.0f} {'kg' if unit == 'kg' else 'kg (quoted per lb)'}",
        f"MOQ: {float(supplier['moq_kg']):,.0f} kg",
        f"Assay: {float(supplier['purity_pct']):.1f}% minimum",
        f"Origin: {supplier['country']}",
    ]

    if "lead_time" not in omits:
        lines.append(f"Lead time: {supplier['lead_time_days']} days after PO")
    if "payment_terms" not in omits:
        lines.append("Payment: 30% deposit, balance against copy of bill of lading")
    if "incoterm" not in omits:
        lines.append(f"Delivery term: {supplier['incoterm']}")

    lines.append("Validity: 30 days")
    lines.append("")

    if first:
        lines.append("Certificate of Analysis for our current batch is attached.")
        lines.append("")

    if style == "chatty":
        lines.append("Let me know if you want me to hold material against this.")
    elif style == "formal":
        lines.append(
            "We look forward to the opportunity of working with Aonic and remain "
            "at your disposal for any further information."
        )

    lines += ["", _sign_off(supplier), "", f"Ref {reference}"]
    return "\n".join(lines) + "\n"


def _revised_body(
    *, supplier: dict, ingredient: dict, old: float, new: float, asked: float, reference: str
) -> str:
    currency = supplier["price_currency"]
    unit = supplier["price_unit"]
    floor = float(supplier["price_floor"])
    holding = new <= floor + 0.001

    lines = ["Thank you for coming back to us.", ""]

    if new < old:
        lines += [
            f"We have reviewed the costing with our production team and can revise",
            f"our offer from {currency} {old:,.2f} to {currency} {new:,.2f} per {unit} "
            f"{supplier['incoterm']}.",
        ]
        if holding:
            lines += [
                "",
                "This is our floor on this material. Below it we would be selling "
                "under our own cost of goods, so we cannot follow you any further.",
            ]
        elif asked < new:
            lines += [
                "",
                f"We understand you are working to {currency} {asked:,.2f}. We are not "
                "able to reach that on this quantity. If you can increase the order "
                "we would look at it again.",
            ]
    else:
        lines += [
            f"We are holding at {currency} {old:,.2f} per {unit} {supplier['incoterm']}.",
            "",
            "Our raw material costs have not moved and this price already reflects "
            "our best terms for a first order of this size.",
        ]

    lines += ["", "All other terms as previously quoted.", "", _sign_off(supplier), "", f"Ref {reference}"]
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------- driving

def respond(*, run_supplier_id: str, inbound_kind: str, reference: str, in_reply_to: str) -> dict:
    """Write and send one supplier's reply to whatever we last sent them."""
    rs = store.run_supplier(run_supplier_id)
    run = store.run(rs["run_id"])
    ingredient = store.ingredient(run["ingredient_id"])
    spec = store.specification(run["ingredient_id"])

    supplier = {
        "id": rs["supplier_id"],
        "name": rs["name"],
        "country": rs["country"],
        "certs": rs["certs"],
        "reply_style": rs["reply_style"],
        "omits_fields": rs["omits_fields"],
        "stubbornness": float(rs["stubbornness"]),
        "list_price": float(rs["list_price"]),
        "price_floor": float(rs["price_floor"]),
        "price_currency": rs["price_currency"],
        "price_unit": rs["price_unit"],
        "incoterm": rs["incoterm"],
        "purity_pct": float(rs["purity_pct"]),
        "moq_kg": float(rs["moq_kg"]),
        "lead_time_days": int(rs["lead_time_days"]),
        "coa_fault": rs["coa_fault"],
    }

    previous = store.latest_quote(run_supplier_id)
    attachment = None

    if inbound_kind in ("rfq", "followup", "retest") or previous is None:
        price = _opening_price(supplier)
        body = _quote_body(
            supplier=supplier,
            ingredient=ingredient,
            run=run,
            price=price,
            reference=reference,
            first=True,
        )
        subject = f"Re: Quotation for {ingredient['name']} [{reference}]"

        # A retest is a different batch off the same line. The fault that
        # failed the first one usually does not repeat, so the supplier gets
        # one honest chance to clear it.
        retests = store.one(
            """
            select count(*) as n from messages
            where run_supplier_id = %s and direction = 'outbound' and kind = 'retest'
            """,
            (run_supplier_id,),
        )
        attempt = int(retests["n"]) if retests else 0
        seed = f"{run['id']}:{supplier['id']}:{attempt}"
        fault = None if attempt else supplier["coa_fault"]
        values = coa.measured_values(
            spec=spec, purity_pct=supplier["purity_pct"], fault=fault, seed=seed
        )
        batch_no = coa.batch_number(supplier["id"], seed)
        pdf = coa.build_pdf(
            supplier=supplier,
            ingredient=ingredient,
            spec=spec,
            values=values,
            batch_no=batch_no,
            issued_on=dt.date.today(),
        )
        attachment = (f"COA_{batch_no}.pdf", pdf)
    else:
        old = float(previous["price"])
        ask_row = store.one(
            """
            select agent_note from messages
            where run_supplier_id = %s and direction = 'outbound' and kind = 'counter'
            order by occurred_at desc limit 1
            """,
            (run_supplier_id,),
        )
        note = (ask_row or {}).get("agent_note") or {}
        asked = float(note.get("target_supplier_price") or old)
        price = _concede(supplier, old, asked)
        body = _revised_body(
            supplier=supplier,
            ingredient=ingredient,
            old=old,
            new=price,
            asked=asked,
            reference=reference,
        )
        subject = f"Re: Counter-offer for {ingredient['name']} [{reference}]"

    message_id = mail.send(
        sender=config.supplier_address(rs["email_local"]),
        to=config.buyer_address(),
        subject=subject,
        body=body,
        reply_to_message_id=in_reply_to,
        attachment=attachment,
        display_name=supplier["name"],
    )

    store.log(
        rs["run_id"],
        "supplier",
        f"{supplier['name']} replied with {supplier['price_currency']} "
        f"{price:,.2f} per {supplier['price_unit']} {supplier['incoterm']}",
        {"attachment": attachment[0] if attachment else None},
    )

    # Nothing is written to the messages table here. The reply is a real
    # email now, and it enters our records only when the tick reads it back
    # out of the mailbox, which is what makes the parser earn its place.
    return {"price": price, "message_id": message_id}
