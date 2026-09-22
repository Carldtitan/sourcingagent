"""Environment and constants for the sourcing engine."""

from __future__ import annotations

import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    """Read .env into os.environ without overwriting a real environment."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


def need(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is not set. See .env.example.")
    return value


GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))

DATABASE_URL = os.environ.get("DATABASE_URL", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

MODEL = os.environ.get("SOURCING_MODEL", "claude-sonnet-5")

# The buyer's own address. Gmail treats a plus tag as the same mailbox, so the
# buyer and all twelve simulated suppliers share one free account.
def buyer_address() -> str:
    local, domain = need("GMAIL_ADDRESS").split("@", 1)
    return f"{local}+sourcing@{domain}"


def supplier_address(tag: str) -> str:
    local, domain = need("GMAIL_ADDRESS").split("@", 1)
    return f"{local}+{tag}@{domain}"


def address_tag(addr: str) -> str | None:
    """Pull the plus tag out of an address, or None when there is none."""
    addr = addr.strip().lower()
    if "<" in addr and ">" in addr:
        addr = addr[addr.index("<") + 1 : addr.index(">")]
    if "+" not in addr or "@" not in addr:
        return None
    return addr.split("+", 1)[1].split("@", 1)[0]


# Freight and duty we add when a supplier does not deliver to the door.
# Rates are our own working assumption for this prototype, and the interface
# says so wherever a normalised price is shown.
FREIGHT_USD_PER_KG = {
    # origin -> (sea freight and inland to a US warehouse, import duty rate)
    "China": (2.40, 0.065),
    "India": (2.10, 0.060),
    "Japan": (2.30, 0.045),
    "Germany": (1.80, 0.045),
    "Switzerland": (1.90, 0.045),
    "United States": (0.35, 0.0),
}

# How much of the freight and duty each delivery term leaves with the buyer.
# EXW leaves everything, DDP leaves nothing.
INCOTERM_BUYER_SHARE = {
    "EXW": (1.00, 1.00),
    "FOB": (0.80, 1.00),
    "CIF": (0.25, 1.00),
    "DAP": (0.00, 1.00),
    "DDP": (0.00, 0.00),
}

FX_TO_USD = {"USD": 1.0, "EUR": 1.08, "CHF": 1.12, "GBP": 1.27}

LB_PER_KG = 2.20462
