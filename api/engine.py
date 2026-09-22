"""The engine's HTTP surface.

One endpoint, four actions. The interface reads from the database directly
and writes only through here, so every change to a run passes through the
same code the command line uses.

    POST /api/engine  {"action": "start",  "ingredient_id": ..., "quantity_kg": ..., "needed_by_days": ...}
    POST /api/engine  {"action": "tick",   "run_id": ...}
    POST /api/engine  {"action": "decide", "approval_id": ..., "decision": ..., "note": ...}
    POST /api/engine  {"action": "reset"}
"""

from __future__ import annotations

import json
import pathlib
import sys
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from engine import approvals, orchestrator, store  # noqa: E402


def act(payload: dict) -> dict:
    action = payload.get("action")

    if action == "start":
        run_id = orchestrator.start_run(
            ingredient_id=payload["ingredient_id"],
            quantity_kg=float(payload["quantity_kg"]),
            needed_by_days=int(payload["needed_by_days"]),
        )
        return {"run_id": run_id}

    if action == "tick":
        return orchestrator.tick(payload.get("run_id"))

    if action == "decide":
        return approvals.resolve(
            approval_id=payload["approval_id"],
            decision=payload["decision"],
            note=payload.get("note"),
            decided_by=payload.get("decided_by", "buyer"),
        )

    if action == "reset":
        store.execute("delete from runs")
        return {"reset": True}

    raise ValueError(f"unknown action: {action!r}")


class handler(BaseHTTPRequestHandler):
    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _send(self, status: int, body: dict) -> None:
        raw = json.dumps(body, default=str).encode()
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
            self._send(200, act(payload))
        except Exception as error:
            self._send(
                500,
                {
                    "error": str(error),
                    "type": type(error).__name__,
                    "trace": traceback.format_exc()[-1200:],
                },
            )

    def do_GET(self) -> None:  # noqa: N802
        self._send(200, {"ok": True, "actions": ["start", "tick", "decide", "reset"]})
