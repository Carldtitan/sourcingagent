"""Run one ingredient end to end from the command line.

    python scripts/demo.py zinc-citrate 500 84

It opens a brief, qualifies the suppliers, approves the shortlist, sends real
Requests for Quotation, waits for the simulated suppliers to reply by real
email, parses every reply and certificate, negotiates, and stops at whatever
needs a human. Anything waiting on a person is printed rather than decided,
because deciding it here would defeat the point.

Pass --auto to answer the gates with the obvious choice so a full run
completes without you, which is what the demo recording uses.
"""

from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from engine import approvals, orchestrator, store


AUTO = {
    "gate_shortlist": "approve",
    "gate_award": "approve",
    "coa_failed": "retest",
    "price_ceiling": "hold",
    "rounds_exhausted": "walk",
    "supplier_question": "walk",
}


def show(run_id: str) -> None:
    run = store.run(run_id)
    ing = store.ingredient(run["ingredient_id"])
    print(f"\n  run {run_id}")
    print(f"  {float(run['quantity_kg']):,.0f} kg of {ing['name']}, status {run['status']}")
    print(f"  ceiling ${float(run['guardrails']['ceiling_usd_per_kg_active']):,.2f} per kg of active material\n")


def print_events(run_id: str, since: int) -> int:
    rows = store.query(
        "select * from events where run_id = %s and id > %s order by id", (run_id, since)
    )
    for r in rows:
        print(f"  [{r['actor']:<11}] {r['summary']}")
    return rows[-1]["id"] if rows else since


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    auto = "--auto" in sys.argv

    ingredient_id = args[0] if args else "zinc-citrate"
    quantity = float(args[1]) if len(args) > 1 else 500
    needed_by = int(args[2]) if len(args) > 2 else 84

    run_id = orchestrator.start_run(
        ingredient_id=ingredient_id, quantity_kg=quantity, needed_by_days=needed_by
    )
    show(run_id)
    cursor = print_events(run_id, 0)

    for step in range(80):
        for approval in store.open_approvals(run_id):
            choice = AUTO[approval["kind"]]
            if not auto:
                print(f"\n  WAITING ON A HUMAN: {approval['headline']}")
                for option in approval["options"]:
                    print(f"     {option['id']:<10} {option['label']}  ({option['consequence']})")
                print("\n  Re-run with --auto to let the script answer these.\n")
                return
            print(f"  [human      ] {choice} on: {approval['headline']}")
            approvals.resolve(approval_id=str(approval["id"]), decision=choice, decided_by="demo")

        orchestrator.tick(run_id)
        cursor = print_events(run_id, cursor)

        run = store.run(run_id)
        if run["status"] in ("closed", "cancelled"):
            break
        time.sleep(5)

    print()
    table = orchestrator.comparison(run_id)
    if not table:
        print("  no offers")
        return

    head = f"  {'#':<3}{'SUPPLIER':<28}{'COUNTRY':<15}{'QUOTED':<28}{'$/KG ACTIVE':>13}{'LEAD':>7}{'COA':>7}{'RDS':>5}{'SCORE':>7}"
    print(head)
    print("  " + "-" * (len(head) - 2))
    for n, row in enumerate(table, start=1):
        lead = f"{row['lead_time_days']}d" if row["lead_time_days"] else "n/s"
        print(
            f"  {n:<3}{row['supplier']:<28}{row['country']:<15}{row['quoted']:<28}"
            f"{row['delivered']:>13,.2f}{lead:>7}{row['coa_verdict']:>7}"
            f"{row['rounds']:>5}{row['score']['total']:>7.1f}"
        )
    print(f"\n  run id {run_id}\n")


if __name__ == "__main__":
    main()
