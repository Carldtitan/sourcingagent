"""Reset the database and run all three ingredients end to end, one after another.

    python scripts/run_all.py

Produces the comparison tables in docs/comparison.md. Runs sequentially
because all three share one mailbox.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import mail, store  # noqa: E402

BRIEFS = [
    ("vitamin-d3", 50, 84),
    ("zinc-citrate", 500, 84),
    ("coq10", 100, 98),
]

if __name__ == "__main__":
    store.execute("delete from runs")
    store.execute("delete from files")
    # clear anything already sitting in the mailbox
    mail.fetch_unread(limit=500)
    print("reset")

    for ingredient_id, quantity, needed_by in BRIEFS:
        print(f"\n===== {ingredient_id} =====", flush=True)
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "demo.py"), ingredient_id,
             str(quantity), str(needed_by), "--auto"],
            check=False,
        )
