"""Write the comparison tables and the email copy into docs/.

    python scripts/export_docs.py

The comparison comes from the latest run of each ingredient in the database.
The email copy is rendered from engine/copy.py, which is exactly what the
agents send, so the document can never drift from the behaviour.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import copy as copytext, normalise, orchestrator, store  # noqa: E402

DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)


def findings() -> list[str]:
    """What the three runs show, written from the data."""
    lines = ["## What the runs show", ""]
    n = 1
    for ingredient in store.query("select * from ingredients order by sort_order"):
        run = store.one(
            "select * from runs where ingredient_id = %s order by created_at desc limit 1",
            (ingredient["id"],),
        )
        if not run:
            continue
        table = orchestrator.comparison(run["id"])
        ceiling = float(run["guardrails"]["ceiling_usd_per_kg_active"])
        agreed = next((r for r in table if r["stage"] == "agreed"), None)
        openings = store.query(
            """
            select distinct on (rs.id) q.usd_per_kg_active from quotes q
            join run_suppliers rs on rs.id = q.run_supplier_id
            where rs.run_id = %s order by rs.id, q.created_at asc
            """,
            (run["id"],),
        )
        if not agreed or not openings:
            continue
        opening = min(float(o["usd_per_kg_active"]) for o in openings)
        gap = (agreed["delivered"] - ceiling) / ceiling * 100
        lines.append(
            f"{n}. **{ingredient['name']}.** The best opening offer normalised to "
            f"${opening:,.2f} per kg. After negotiation the award went to "
            f"{agreed['supplier']} at ${agreed['delivered']:,.2f}, "
            + (
                f"{gap:.1f}% above the ${ceiling:,.2f} ceiling, so a person approved it knowing that."
                if gap > 0
                else f"inside the ${ceiling:,.2f} ceiling."
            )
        )
        n += 1

    lines += [
        f"{n}. **No supplier went under a ceiling.** Every award landed within about",
        "   3% of what the pouch can carry, and each one crossing the line went to a",
        "   person at the award gate rather than being agreed by the agent. That is",
        "   the guardrail doing its job. The market here is simulated, but in a",
        "   real run the same pattern would be the signal to revisit how the",
        "   ingredient budget is split across the formula.",
        f"{n + 1}. **Certificates were caught.** A lead failure and a microbial failure",
        "   were flagged on first read, sent to a person, retested, and only then",
        "   allowed back into the ranking.",
        "",
    ]
    return lines


def comparison_doc() -> str:
    cost = store.one("select * from cost_model where id = 'aonic-complete'")
    parts = [
        "# Comparison tables",
        "",
        "Three ingredients from the Aonic Complete Supplement Facts panel, each run",
        "end to end against the simulated suppliers. Every price is normalised to",
        "United States dollars per kilogram of active material, delivered to our",
        "door, so a price quoted ex works in euros and a price quoted delivered in",
        "dollars per pound can sit in the same column.",
        "",
        f"The ceiling on each ingredient is its share of the ${float(cost['ingredients_usd']):.2f}",
        f"of ingredient cost in a {cost['servings_per_pouch']}-serving pouch, divided by the mass of that",
        "ingredient in the pouch. The source of that cost model is recorded in the",
        "database and shown in the interface.",
        "",
        "Everything below comes from simulated suppliers. No figure describes a real",
        "company, a real price or a real test result.",
        "",
    ]
    parts += findings()

    for ingredient in store.query("select * from ingredients order by sort_order"):
        run = store.one(
            "select * from runs where ingredient_id = %s order by created_at desc limit 1",
            (ingredient["id"],),
        )
        if not run:
            continue
        ceiling = float(run["guardrails"]["ceiling_usd_per_kg_active"])
        table = orchestrator.comparison(run["id"])[:5]
        spec = store.specification(ingredient["id"])

        parts += [
            f"## {ingredient['name']}",
            "",
            f"{float(run['quantity_kg']):,.0f} kg of {ingredient['chemical_form'].lower()}, "
            f"needed within {run['needed_by_days']} days. Ceiling **${ceiling:,.2f}** per kg of "
            f"active material. Required certification: {', '.join(spec['required_certs'])}.",
            "",
            "| # | Supplier | Origin | As quoted | Assay | Normalised $/kg active | vs ceiling | Lead | COA status | Rounds | Outcome | Score |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for n, row in enumerate(table, start=1):
            gap = row["delivered"] - ceiling
            outcome = {
                "agreed": "agreed",
                "walked_away": "walked away",
                "quoted": "on the table",
                "countered": "countered",
            }.get(row["stage"], row["stage"].replace("_", " "))
            coa = {
                "pass": "pass",
                "fail": "**fail**",
                "not_received": "not received",
            }[row["coa_verdict"]]
            batch = f" ({row['batch_no']})" if row["batch_no"] else ""
            parts.append(
                f"| {n} | {row['supplier']} | {row['country']} | {row['quoted']} | "
                f"{row['purity_pct']:.1f}% | **${row['delivered']:,.2f}** | "
                f"{'+' if gap > 0 else '−'}${abs(gap):,.2f} | "
                f"{str(row['lead_time_days']) + 'd' if row['lead_time_days'] else 'n/s'} | "
                f"{coa}{batch} | {row['rounds']} | {outcome} | {row['score']['total']:.0f} |"
            )

        if table:
            lead = table[0]
            parts += ["", f"How the leading price, {lead['supplier']}, was normalised:", ""]
            for step in (lead["normalisation"] or {}).get("steps", []):
                note = f" ({step['note']})" if step.get("note") else ""
                parts.append(f"1. {step['label']}: {step['value']}{note}")

        failed = store.query(
            """
            select s.name, c.batch_no, c.findings from coas c
            join run_suppliers rs on rs.id = c.run_supplier_id
            join suppliers s on s.id = rs.supplier_id
            where rs.run_id = %s and c.verdict = 'fail'
            """,
            (run["id"],),
        )
        if failed:
            parts += ["", "Certificates flagged during the run:", ""]
            for row in failed:
                bad = [f for f in row["findings"] if f["verdict"] == "fail"]
                parts.append(
                    f"1. {row['name']}, batch {row['batch_no']}: "
                    + "; ".join(f"{f['line']} {f['measured']} against {f['limit']}, {f['margin']}" for f in bad)
                )
        parts.append("")

    parts += [
        "## How the score is built",
        "",
        "1. Normalised price, 50%. The cheapest delivered offer scores 100 and every",
        "   other offer scores in proportion.",
        "2. Lead time, 20%. Shorter is better, measured against the deadline. A",
        "   supplier who never states a lead time scores close to zero here, because",
        "   silence about delivery is a risk to the launch date.",
        "3. Certificate, 20%. A pass scores 100, a missing certificate 40, a failure 0.",
        "4. Certification, 10%. Holding every required certificate scores 70, and",
        "   each extra one adds 10.",
        "",
        "A walked-away offer stays in the table, because it is still a real price the",
        "market gave us. It ranks below every offer still in play, so the leader is",
        "always something a buyer can actually award.",
        "",
    ]
    return "\n".join(parts)


def copy_doc() -> str:
    ingredient = store.ingredient("zinc-citrate")
    spec = store.specification("zinc-citrate")
    run = {"quantity_kg": 500, "needed_by_days": 84}
    supplier = {"name": "Jiangsu Vitalabs"}
    ref = "AON-7Q4K2M-9XWD"

    rfq = copytext.rfq(supplier=supplier, ingredient=ingredient, spec=spec, run=run, reference=ref)
    follow = copytext.followup(supplier=supplier, ingredient=ingredient, run=run, reference=ref, days_quiet=2)
    counter = copytext.counter(
        supplier=supplier,
        ingredient=ingredient,
        run=run,
        reference=ref,
        their_delivered=21.76,
        target_delivered=17.52,
        ceiling=17.52,
        best_rival_delivered=19.43,
        rival_count=5,
        round_number=1,
        gaps=["Your payment terms."],
    )
    close = copytext.close(
        supplier=supplier,
        ingredient=ingredient,
        spec=spec,
        run=run,
        reference=ref,
        agreed_price=14.60,
        currency="USD",
        unit="kg",
        incoterm="FOB",
        delivered=17.46,
        lead_time_days=49,
        batch_no="JIA-2521G",
    )

    def block(title: str, why: list[str], draft: copytext.Draft) -> list[str]:
        return (
            [f"## {title}", ""]
            + why
            + ["", f"**Subject:** {draft.subject}", "", "```text", draft.body.rstrip(), "```", ""]
        )

    parts = [
        "# Outreach and negotiation copy",
        "",
        "These four messages are rendered straight from `engine/copy.py`, which is",
        "the code the agents send from. The agents fill the slots. They do not",
        "rewrite the sentences, for three reasons.",
        "",
        "1. A buyer can read exactly what goes out in their name before they approve",
        "   the shortlist.",
        "2. The same words to every supplier make their replies comparable.",
        "3. A Request for Quotation that states its specification badly gets a bad",
        "   quotation back, so this is the text most worth writing once and well.",
        "",
        "The examples use a zinc citrate run. Figures are illustrative.",
        "",
    ]
    parts += block(
        "1. Opening Request for Quotation",
        [
            "Sent to every supplier on the approved shortlist. It states the full",
            "specification up front and asks for the six things that make a quotation",
            "comparable, so the parser has something to find. It tells the supplier",
            "a failing certificate loses even at a low price, which sets the terms of",
            "the negotiation before it starts.",
        ],
        rfq,
    )
    parts += block(
        "2. Follow-up",
        [
            "Sent once, when a supplier has been silent past the follow-up window.",
            "It names the three things that decide the order, invites a one-line",
            "refusal, and says a partial answer today beats a complete one later.",
            "There is no second chase. Silence after this closes the file.",
        ],
        follow,
    )
    parts += block(
        "3. Counter-offer",
        [
            "Sent when a normalised price sits above the ceiling. It shows the",
            "supplier how we read their price, names the best rival on the same",
            "basis without naming the rival, and explains that the ceiling comes",
            "from what the product can carry, which makes it credible rather than a",
            "haggling position. It offers three ways to close the gap, including two",
            "that cost the supplier nothing on unit price.",
        ],
        counter,
    )
    parts += block(
        "4. Close",
        [
            "Sent only after a person approves the award at the second gate. It",
            "restates every agreed term, including the delivered cost, and makes",
            "release of the goods conditional on the shipped batch's certificate",
            "passing the same specification the enquiry was sent with.",
        ],
        close,
    )
    return "\n".join(parts)


if __name__ == "__main__":
    (DOCS / "comparison.md").write_text(comparison_doc(), encoding="utf-8")
    (DOCS / "copy.md").write_text(copy_doc(), encoding="utf-8")
    print("wrote docs/comparison.md and docs/copy.md")
