"""Serve the engine locally on port 8787.

On Vercel, api/engine.py runs as a Python function. Locally, Next.js cannot
run Python, so this serves the very same handler and next.config.mjs points
/api/engine at it during development.

    python scripts/engine_server.py
"""

from __future__ import annotations

import pathlib
import sys
from http.server import ThreadingHTTPServer

import importlib.util

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# api/engine.py shares its name with the engine package, so load it by path
# under a name of its own.
_spec = importlib.util.spec_from_file_location("api_engine", ROOT / "api" / "engine.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
handler = _module.handler

PORT = 8787

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    print(f"engine listening on http://127.0.0.1:{PORT}")
    server.serve_forever()
