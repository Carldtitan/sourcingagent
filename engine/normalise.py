"""Turning quotations into one comparable number.

Suppliers quote in different currencies, in different units, under different
delivery terms, and they ship material of different purity. None of those
headline prices can be compared as they stand.

Normalising converts every quotation to United States dollars per kilogram
of active material, delivered to our door. Each step is recorded so the
interface can show a buyer exactly how a quoted price became a real one.
"""

from __future__ import annotations

from . import config


def normalise(
    *,
    price: float,
    currency: str,
    unit: str,
    incoterm: str,
    purity_pct: float | None,
    origin: str,
) -> dict:
    steps: list[dict] = []

    incoterm = (incoterm or "EXW").upper()
    currency = (currency or "USD").upper()
    unit = (unit or "kg").lower()

    steps.append(
        {
            "label": "As quoted",
            "value": f"{currency} {price:,.2f} per {unit}, {incoterm}",
        }
    )

    # 1. currency
    rate = config.FX_TO_USD.get(currency, 1.0)
    usd = price * rate
    if rate != 1.0:
        steps.append(
            {
                "label": "Converted to dollars",
                "value": f"USD {usd:,.2f} per {unit}",
                "note": f"1 {currency} = {rate:.2f} USD",
            }
        )

    # 2. unit
    if unit == "lb":
        usd = usd * config.LB_PER_KG
        steps.append(
            {
                "label": "Converted to kilograms",
                "value": f"USD {usd:,.2f} per kg",
                "note": f"1 kg = {config.LB_PER_KG:.3f} lb",
            }
        )

    gross_per_kg = usd

    # 3. freight and duty, by delivery term
    freight_rate, duty_rate = config.FREIGHT_USD_PER_KG.get(origin, (2.20, 0.06))
    freight_share, duty_share = config.INCOTERM_BUYER_SHARE.get(incoterm, (1.0, 1.0))

    freight = round(freight_rate * freight_share, 4)
    duty = round(gross_per_kg * duty_rate * duty_share, 4)

    if freight or duty:
        usd = usd + freight + duty
        parts = []
        if freight:
            parts.append(f"freight {freight:,.2f}")
        if duty:
            parts.append(f"duty {duty:,.2f}")
        steps.append(
            {
                "label": "Landed at our door",
                "value": f"USD {usd:,.2f} per kg",
                "note": f"{incoterm} leaves us {' and '.join(parts)} per kg, from {origin}",
            }
        )
    else:
        steps.append(
            {
                "label": "Landed at our door",
                "value": f"USD {usd:,.2f} per kg",
                "note": f"{incoterm} puts freight and duty on the supplier",
            }
        )

    # 4. purity
    purity = float(purity_pct) if purity_pct else 100.0
    active = usd / (purity / 100.0)
    steps.append(
        {
            "label": "Per kg of active material",
            "value": f"USD {active:,.2f} per kg",
            "note": f"assay {purity:.1f}%, so we pay for {purity:.1f} kg of active in every 100 kg",
        }
    )

    return {
        "usd_per_kg_active": round(active, 2),
        "usd_per_kg_landed": round(usd, 2),
        "usd_per_kg_gross": round(gross_per_kg, 2),
        "freight_usd_per_kg": freight,
        "duty_usd_per_kg": duty,
        "note": {"steps": steps},
    }


def ceiling_for(ingredient: dict, cost_model: dict) -> float:
    """The most we can pay per kg of active material.

    An ingredient's budget is its share of the ingredient cost one pouch of
    the finished product carries. Dividing that budget by the mass of the
    ingredient in a pouch gives the ceiling.
    """
    kg_per_pouch = (
        float(ingredient["dose_mg"]) * int(cost_model["servings_per_pouch"]) / 1_000_000.0
    )
    return round(float(ingredient["cost_budget_usd_per_pouch"]) / kg_per_pouch, 2)


def score(
    *,
    delivered: float,
    best_delivered: float,
    lead_time_days: int | None,
    max_lead_time_days: int,
    coa_verdict: str,
    certs: list[str],
    required_certs: list[str],
) -> dict:
    """Rank an offer on the four things that decide it.

    Price carries the most weight, and a failed certificate cannot be bought
    off with a low price.
    """
    price_score = max(0.0, min(1.0, best_delivered / delivered)) if delivered else 0.0

    if lead_time_days is None:
        lead_score = 0.5
    else:
        lead_score = max(0.0, min(1.0, 1 - (lead_time_days / max(max_lead_time_days, 1))))

    coa_score = {"pass": 1.0, "not_received": 0.4, "fail": 0.0}.get(coa_verdict, 0.4)

    held = set(certs)
    extra = held - set(required_certs)
    cert_score = min(1.0, 0.7 + 0.1 * len(extra)) if set(required_certs) <= held else 0.0

    total = (
        price_score * 0.50 + lead_score * 0.20 + coa_score * 0.20 + cert_score * 0.10
    )

    return {
        "total": round(total * 100, 1),
        "price": round(price_score * 100, 1),
        "lead_time": round(lead_score * 100, 1),
        "certificate": round(coa_score * 100, 1),
        "certification": round(cert_score * 100, 1),
    }
