"""Resolving the gates and escalations a human holds.

Two gates stop the machine on its own: nothing is sent until a buyer approves
the shortlist, and nothing is agreed until a buyer approves the award. Four
escalations interrupt it: a certificate outside specification, a price the
product cannot carry, a question the agent cannot answer, and a negotiation
that has used its rounds without agreement.

Every decision here is recorded against the approval that raised it, so a run
can be read back afterwards as a sequence of who decided what.
"""

from __future__ import annotations

from . import copy as copytext, config, mail, negotiator, orchestrator, store


def resolve(*, approval_id: str, decision: str, note: str | None = None, decided_by: str = "buyer") -> dict:
    approval = store.one("select * from approvals where id = %s", (approval_id,))
    if not approval:
        raise LookupError("no such approval")
    if approval["status"] != "open":
        return {"already": approval["status"]}

    run_id = approval["run_id"]
    handler = {
        "gate_shortlist": _gate_shortlist,
        "gate_award": _gate_award,
        "coa_failed": _coa_failed,
        "price_ceiling": _price_ceiling,
        "rounds_exhausted": _price_ceiling,
        "supplier_question": _supplier_question,
    }[approval["kind"]]

    outcome = handler(approval, decision)

    store.execute(
        """
        update approvals set status = 'resolved', decision = %s, note = %s,
               decided_at = now()
        where id = %s
        """,
        (decision, note, approval_id),
    )
    store.log(
        run_id,
        "human",
        f"{decided_by} chose {decision} on: {approval['headline']}",
        {"kind": approval["kind"], "note": note},
    )
    return outcome


# ------------------------------------------------------------------- gates

def _gate_shortlist(approval: dict, decision: str) -> dict:
    run_id = approval["run_id"]

    if decision != "approve":
        store.execute("update runs set status = 'cancelled', closed_at = now() where id = %s", (run_id,))
        return {"cancelled": True}

    sent = 0
    for rs in store.run_suppliers(run_id, shortlisted_only=True):
        negotiator.send_rfq(run_supplier_id=rs["id"])
        sent += 1

    store.execute("update runs set status = 'negotiating' where id = %s", (run_id,))
    return {"rfqs_sent": sent}


def _gate_award(approval: dict, decision: str) -> dict:
    run_id = approval["run_id"]

    if decision != "approve":
        return {"held": True}

    winner_id = str(approval["subject_id"])
    reference = _reference_for(winner_id)
    negotiator.send_close(run_supplier_id=winner_id, reference=reference)

    declined = 0
    for rs in store.run_suppliers(run_id, shortlisted_only=True):
        if str(rs["id"]) == winner_id or rs["stage"] in ("rejected", "walked_away"):
            continue
        _decline(rs, "Another supplier came in lower on delivered cost per kilogram of active material.")
        declined += 1

    store.execute("update runs set status = 'closed', closed_at = now() where id = %s", (run_id,))
    return {"closed": True, "declined": declined}


# ------------------------------------------------------------- escalations

def _coa_failed(approval: dict, decision: str) -> dict:
    rs_id = str(approval["subject_id"])
    rs = store.run_supplier(rs_id)

    if decision == "reject":
        _decline(rs, "The Certificate of Analysis for the batch you sent falls outside our specification.")
        store.execute("update run_suppliers set stage = 'walked_away' where id = %s", (rs_id,))
        return {"rejected": True}

    if decision == "retest":
        _ask_for_retest(rs, approval["context"])
        return {"retest_requested": True}

    if decision == "waive":
        store.execute("update run_suppliers set stage = 'quoted' where id = %s", (rs_id,))
        store.execute(
            "update coas set verdict = 'pass' where run_supplier_id = %s",
            (rs_id,),
        )
        store.log(
            rs["run_id"],
            "human",
            f"Documented waiver recorded against {rs['name']}'s certificate",
            {"waived": True},
        )
        return {"waived": True}

    return {}


def _price_ceiling(approval: dict, decision: str) -> dict:
    rs_id = str(approval["subject_id"])
    rs = store.run_supplier(rs_id)
    run = store.run(rs["run_id"])

    if decision == "walk":
        _decline(rs, "We could not reach a price the finished product can carry.")
        store.execute("update run_suppliers set stage = 'walked_away' where id = %s", (rs_id,))
        return {"walked": True}

    if decision == "accept":
        delivered = float(approval["context"].get("delivered", 0))
        guardrails = dict(run["guardrails"])
        guardrails["ceiling_usd_per_kg_active"] = max(
            float(guardrails["ceiling_usd_per_kg_active"]), delivered
        )
        guardrails["ceiling_raised_by_buyer"] = True
        store.execute(
            "update runs set guardrails = %s where id = %s",
            (store.j(guardrails), run["id"]),
        )
        store.execute("update run_suppliers set stage = 'agreed' where id = %s", (rs_id,))
        return {"accepted": True, "ceiling": guardrails["ceiling_usd_per_kg_active"]}

    store.execute("update run_suppliers set stage = 'quoted' where id = %s", (rs_id,))
    return {"held": True}


def _supplier_question(approval: dict, decision: str) -> dict:
    rs_id = str(approval["subject_id"])
    rs = store.run_supplier(rs_id)

    if decision == "walk":
        _decline(rs, "We have closed this enquiry.")
        store.execute("update run_suppliers set stage = 'walked_away' where id = %s", (rs_id,))
        return {"walked": True}

    store.execute("update run_suppliers set stage = 'rfq_sent' where id = %s", (rs_id,))
    return {"kept": True}


# ------------------------------------------------------------------ helpers

def _reference_for(run_supplier_id: str) -> str:
    row = store.one(
        "select reference from messages where run_supplier_id = %s and reference is not null limit 1",
        (run_supplier_id,),
    )
    return row["reference"] if row else mail.new_reference()


def _decline(rs: dict, reason: str) -> None:
    run = store.run(rs["run_id"])
    ingredient = store.ingredient(run["ingredient_id"])
    reference = _reference_for(str(rs["id"]))

    draft = copytext.decline(
        supplier={"name": rs["name"]},
        ingredient=ingredient,
        reference=reference,
        reason=reason,
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
            "run_supplier_id": rs["id"],
            "direction": "outbound",
            "kind": "decline",
            "from_addr": config.buyer_address(),
            "to_addr": config.supplier_address(rs["email_local"]),
            "subject": draft.subject,
            "body": draft.body,
            "reference": reference,
            "message_id": message_id,
            "agent_note": store.j({"why": reason}),
        },
    )


def _ask_for_retest(rs: dict, context: dict) -> None:
    run = store.run(rs["run_id"])
    ingredient = store.ingredient(run["ingredient_id"])
    reference = _reference_for(str(rs["id"]))
    failing = ", ".join(context.get("failing", [])) or "one or more tests"

    subject = f"Certificate outside specification: {ingredient['name']} [{reference}]"
    body = f"""Dear {rs['name']} quality team,

We have read the Certificate of Analysis for batch {context.get('batch_no', 'the batch you sent')}
against our specification and it falls outside it on {failing}.

We are holding your quotation open. To stay in this enquiry, please send one
of the following.

  1. A Certificate of Analysis for a different batch that meets every line of
     the specification we sent with our enquiry.
  2. A retest of the same batch by an independent laboratory, with the
     laboratory named on the report.

We cannot release material into production against the certificate as it
stands, whatever the price.

Reference {reference}.

{copytext.SIGNATURE}

--
{copytext.DISCLOSURE}
"""

    message_id = mail.send(
        sender=config.buyer_address(),
        to=config.supplier_address(rs["email_local"]),
        subject=subject,
        body=body,
        display_name="Aonic Sourcing",
    )
    store.insert(
        "messages",
        {
            "run_id": rs["run_id"],
            "run_supplier_id": rs["id"],
            "direction": "outbound",
            "kind": "retest",
            "from_addr": config.buyer_address(),
            "to_addr": config.supplier_address(rs["email_local"]),
            "subject": subject,
            "body": body,
            "reference": reference,
            "message_id": message_id,
            "agent_note": store.j({"why": f"Certificate failed on {failing}. Buyer asked for a retest."}),
        },
    )
    store.execute("update run_suppliers set stage = 'rfq_sent' where id = %s", (rs["id"],))
