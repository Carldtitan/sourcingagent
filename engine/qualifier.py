"""Qualification: cutting the candidate list down, with a reason for every cut.

This step is deliberately not a language model. Whether a supplier holds a
Good Manufacturing Practice certificate, whether their minimum order quantity
fits our order, and whether their lead time beats our deadline are all matters
of fact. A buyer has to be able to audit every cut, and a rule can be audited.

The language model earns its place later, where the work is genuinely
ambiguous: reading a reply written in prose and deciding what to offer next.
"""

from __future__ import annotations

from . import store


def assess(*, supplier: dict, spec: dict, run: dict) -> tuple[bool, str]:
    """Return whether a supplier qualifies, and the reason either way."""
    reasons: list[str] = []

    missing = [c for c in spec["required_certs"] if c not in supplier["certs"]]
    if missing:
        reasons.append(f"holds no {' or '.join(missing)} certificate")

    if float(supplier["moq_kg"]) > float(run["quantity_kg"]):
        reasons.append(
            f"minimum order {float(supplier['moq_kg']):,.0f} kg is above our "
            f"{float(run['quantity_kg']):,.0f} kg order"
        )

    if float(supplier["moq_kg"]) > float(spec["max_moq_kg"]):
        reasons.append(
            f"minimum order {float(supplier['moq_kg']):,.0f} kg is above the "
            f"{float(spec['max_moq_kg']):,.0f} kg we will hold for this material"
        )

    if int(supplier["lead_time_days"]) > int(run["needed_by_days"]):
        reasons.append(
            f"lead time {supplier['lead_time_days']} days misses our "
            f"{run['needed_by_days']} day deadline"
        )

    if supplier["country"] not in spec["accepted_origins"]:
        reasons.append(f"{supplier['country']} is not an accepted origin for this material")

    if reasons:
        return False, "; ".join(reasons).capitalize()

    extra = [c for c in supplier["certs"] if c not in spec["required_certs"]]
    kept = (
        f"Holds {', '.join(spec['required_certs'])}. "
        f"Minimum order {float(supplier['moq_kg']):,.0f} kg, "
        f"lead time {supplier['lead_time_days']} days, {supplier['country']}."
    )
    if extra:
        kept += f" Also carries {', '.join(extra)}."
    return True, kept


def qualify_run(run_id: str) -> dict:
    """Score every candidate for a run and open the shortlist approval gate."""
    run = store.run(run_id)
    spec = store.specification(run["ingredient_id"])
    ingredient = store.ingredient(run["ingredient_id"])
    candidates = store.suppliers_for(run["ingredient_id"])

    kept: list[dict] = []
    dropped: list[dict] = []

    for supplier in candidates:
        ok, reason = assess(supplier=supplier, spec=spec, run=run)
        row = store.insert(
            "run_suppliers",
            {
                "run_id": run_id,
                "supplier_id": supplier["id"],
                "qualified": ok,
                "disqualify_reason": reason,
                "stage": "shortlisted" if ok else "rejected",
            },
        )
        (kept if ok else dropped).append({**row, "name": supplier["name"], "country": supplier["country"]})

    store.log(
        run_id,
        "qualifier",
        f"{len(kept)} of {len(candidates)} suppliers qualified for {ingredient['name']}",
        {
            "kept": [s["name"] for s in kept],
            "dropped": [{"name": s["name"], "reason": s["disqualify_reason"]} for s in dropped],
        },
    )

    store.insert(
        "approvals",
        {
            "run_id": run_id,
            "kind": "gate_shortlist",
            "headline": (
                f"{len(kept)} of {len(candidates)} suppliers qualified for "
                f"{ingredient['name']}"
            ),
            "context": store.j(
                {
                    "ingredient": ingredient["name"],
                    "quantity_kg": float(run["quantity_kg"]),
                    "kept": [
                        {
                            "name": s["name"],
                            "country": s["country"],
                            "reason": s["disqualify_reason"],
                        }
                        for s in kept
                    ],
                    "dropped": [
                        {
                            "name": s["name"],
                            "country": s["country"],
                            "reason": s["disqualify_reason"],
                        }
                        for s in dropped
                    ],
                }
            ),
            "options": store.j(
                [
                    {
                        "id": "approve",
                        "label": "Approve and send the RFQ",
                        "consequence": f"Sends a Request for Quotation to all {len(kept)} suppliers.",
                        "tone": "primary",
                    },
                    {
                        "id": "reject",
                        "label": "Cancel this run",
                        "consequence": "Nothing is sent and the run closes.",
                        "tone": "danger",
                    },
                ]
            ),
        },
    )

    store.execute(
        "update runs set status = 'awaiting_shortlist' where id = %s", (run_id,)
    )

    return {"kept": len(kept), "dropped": len(dropped)}
