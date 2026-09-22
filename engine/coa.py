"""Certificates of Analysis: producing them, reading them, judging them.

A Certificate of Analysis is the laboratory report a supplier sends with a
batch. It states what the material was tested for and what the tests found.
Checking one against the target specification is the step that decides
whether a batch may go into a product.

Three things happen here. Simulated suppliers produce a certificate as a
real PDF, with faults planted in a few of them. The reader pulls the
measured values back out of that PDF using a language model, which is the
same problem a real supplier's certificate poses. The judge then compares
every value against the specification with fixed arithmetic, because a
laboratory limit is not a matter of opinion.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import random
import re

from fpdf import FPDF
from pypdf import PdfReader

from . import config, jsonio


# ------------------------------------------------------------- production

LINES = [
    ("assay_pct", "Assay", "%", "HPLC"),
    ("lead_ppm", "Lead (Pb)", "ppm", "ICP-MS"),
    ("arsenic_ppm", "Arsenic (As)", "ppm", "ICP-MS"),
    ("cadmium_ppm", "Cadmium (Cd)", "ppm", "ICP-MS"),
    ("mercury_ppm", "Mercury (Hg)", "ppm", "ICP-MS"),
    ("tpc_cfu_g", "Total plate count", "cfu/g", "USP <2021>"),
    ("yeast_mould_cfu_g", "Yeast and mould", "cfu/g", "USP <2021>"),
]


def measured_values(*, spec: dict, purity_pct: float, fault: str | None, seed: str) -> dict:
    """Invent a plausible set of laboratory results for one batch."""
    rng = random.Random(seed)

    values = {
        "assay_pct": round(purity_pct + rng.uniform(-0.25, 0.25), 2),
        "lead_ppm": round(float(spec["lead_max_ppm"]) * rng.uniform(0.08, 0.55), 3),
        "arsenic_ppm": round(float(spec["arsenic_max_ppm"]) * rng.uniform(0.05, 0.40), 3),
        "cadmium_ppm": round(float(spec["cadmium_max_ppm"]) * rng.uniform(0.10, 0.60), 3),
        "mercury_ppm": round(float(spec["mercury_max_ppm"]) * rng.uniform(0.05, 0.45), 4),
        "tpc_cfu_g": int(float(spec["tpc_max_cfu_g"]) * rng.uniform(0.02, 0.35)),
        "yeast_mould_cfu_g": int(float(spec["yeast_mould_max_cfu_g"]) * rng.uniform(0.02, 0.40)),
    }

    if fault == "lead":
        values["lead_ppm"] = round(float(spec["lead_max_ppm"]) * rng.uniform(1.25, 1.85), 3)
    elif fault == "cadmium":
        values["cadmium_ppm"] = round(float(spec["cadmium_max_ppm"]) * rng.uniform(1.2, 1.7), 3)
    elif fault == "assay":
        values["assay_pct"] = round(float(spec["assay_min_pct"]) - rng.uniform(0.6, 2.4), 2)
    elif fault == "micro":
        values["tpc_cfu_g"] = int(float(spec["tpc_max_cfu_g"]) * rng.uniform(1.3, 2.6))

    return values


def batch_number(supplier_id: str, seed: str) -> str:
    rng = random.Random(seed)
    prefix = "".join(c for c in supplier_id.upper() if c.isalpha())[:3]
    return f"{prefix}-{rng.randint(2400, 2699)}{rng.choice('ABCDEFGH')}"


def build_pdf(
    *,
    supplier: dict,
    ingredient: dict,
    spec: dict,
    values: dict,
    batch_no: str,
    issued_on: dt.date,
) -> bytes:
    """Render a certificate that looks like the ones suppliers really send."""
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 8, supplier["name"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(
        0,
        4.5,
        f"Quality Control Laboratory  |  {supplier['country']}  |  "
        f"{', '.join(supplier['certs'])}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "CERTIFICATE OF ANALYSIS", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pdf.set_draw_color(30, 30, 30)
    pdf.set_line_width(0.5)
    y = pdf.get_y()
    pdf.line(10, y, 200, y)
    pdf.ln(3)

    meta = [
        ("Product", f"{ingredient['name']} ({ingredient['chemical_form']})"),
        ("CAS number", ingredient["cas_number"] or "not applicable"),
        ("Batch number", batch_no),
        ("Manufacture date", (issued_on - dt.timedelta(days=21)).isoformat()),
        ("Analysis date", issued_on.isoformat()),
        ("Retest date", (issued_on + dt.timedelta(days=730)).isoformat()),
        ("Country of manufacture", supplier["country"]),
        ("Appearance", "White to off-white crystalline powder"),
    ]
    pdf.set_font("Helvetica", "", 9)
    for key, value in meta:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(48, 5.4, key)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5.4, str(value), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(235, 235, 232)
    pdf.cell(64, 6.6, "  Test", border=0, fill=True)
    pdf.cell(44, 6.6, "Specification", border=0, fill=True)
    pdf.cell(34, 6.6, "Result", border=0, fill=True)
    pdf.cell(0, 6.6, "Method", border=0, fill=True, new_x="LMARGIN", new_y="NEXT")

    limits = {
        "assay_pct": f"{spec['assay_min_pct']}% min",
        "lead_ppm": f"NMT {spec['lead_max_ppm']} ppm",
        "arsenic_ppm": f"NMT {spec['arsenic_max_ppm']} ppm",
        "cadmium_ppm": f"NMT {spec['cadmium_max_ppm']} ppm",
        "mercury_ppm": f"NMT {spec['mercury_max_ppm']} ppm",
        "tpc_cfu_g": f"NMT {int(spec['tpc_max_cfu_g']):,} cfu/g",
        "yeast_mould_cfu_g": f"NMT {int(spec['yeast_mould_max_cfu_g']):,} cfu/g",
    }

    pdf.set_font("Helvetica", "", 9)
    for key, label, suffix, method in LINES:
        value = values[key]
        shown = f"{value:,}" if isinstance(value, int) else f"{value:g}"
        pdf.cell(64, 6, f"  {label}")
        pdf.cell(44, 6, limits[key])
        pdf.cell(34, 6, f"{shown} {suffix}")
        pdf.cell(0, 6, method, new_x="LMARGIN", new_y="NEXT")

    for label, limit, result, method in [
        ("  Escherichia coli", spec["ecoli_required"], "Absent", "USP <2022>"),
        ("  Salmonella", spec["salmonella_required"], "Absent", "USP <2022>"),
    ]:
        pdf.cell(64, 6, label)
        pdf.cell(44, 6, limit)
        pdf.cell(34, 6, result)
        pdf.cell(0, 6, method, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(
        0,
        4.2,
        "Released by the Quality Control department. Results apply to the batch "
        "identified above. Store in a cool dry place away from light.\n\n"
        "SIMULATED DOCUMENT. This certificate was generated for a prototype "
        "sourcing system. The company named above does not exist and these "
        "results describe no real material.",
    )

    return bytes(pdf.output())


# ---------------------------------------------------------------- reading

EXTRACTION_PROMPT = """You are reading a supplier's Certificate of Analysis for a
raw material going into a nutritional supplement.

Return a single JSON object and nothing else. Use these keys, all numbers, no
units, no thousands separators:

  batch_no            string, the batch or lot number
  issued_on           string, the analysis date as YYYY-MM-DD
  assay_pct           number
  lead_ppm            number
  arsenic_ppm         number
  cadmium_ppm         number
  mercury_ppm         number
  tpc_cfu_g           number
  yeast_mould_cfu_g   number
  ecoli               string, exactly what the certificate reports
  salmonella          string, exactly what the certificate reports

Rules. Read the result column, never the specification column. A result
written as "<0.05" is 0.05. A result written as "NMT 10" in the result column
means the test was not performed, so use null. If a value is genuinely absent
from the document, use null for that key. Never invent a number.

Certificate text follows.

---
{text}
---
"""


def pdf_to_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def read_certificate(data: bytes) -> dict:
    """Pull the measured values out of a certificate PDF.

    A language model does the reading, because a real certificate is laid out
    however the supplier's laboratory felt like laying it out. The numbers it
    returns are then judged by fixed arithmetic, never by the model.
    """
    text = pdf_to_text(data)
    return jsonio.ask(EXTRACTION_PROMPT.format(text=text[:12000]), max_tokens=900)


# ---------------------------------------------------------------- judging

JUDGED = [
    ("assay_pct", "Assay", "assay_min_pct", "min", "%"),
    ("lead_ppm", "Lead", "lead_max_ppm", "max", "ppm"),
    ("arsenic_ppm", "Arsenic", "arsenic_max_ppm", "max", "ppm"),
    ("cadmium_ppm", "Cadmium", "cadmium_max_ppm", "max", "ppm"),
    ("mercury_ppm", "Mercury", "mercury_max_ppm", "max", "ppm"),
    ("tpc_cfu_g", "Total plate count", "tpc_max_cfu_g", "max", "cfu/g"),
    ("yeast_mould_cfu_g", "Yeast and mould", "yeast_mould_max_cfu_g", "max", "cfu/g"),
]


def judge(measured: dict, spec: dict) -> tuple[str, list[dict]]:
    """Compare every line against the specification.

    Returns an overall verdict and one finding per line, each carrying how
    much of the limit the measured value uses. A value at 80% of its limit is
    passing and worth seeing, because it says the next batch might not.
    """
    findings: list[dict] = []
    failed = False

    for key, label, spec_key, direction, unit in JUDGED:
        limit = float(spec[spec_key])
        value = measured.get(key)

        if value is None:
            findings.append(
                {
                    "line": label,
                    "limit": f"{'at least' if direction == 'min' else 'at most'} {limit:g} {unit}",
                    "measured": "not reported",
                    "margin": "the certificate does not cover this test",
                    "load": 0.0,
                    "verdict": "fail",
                }
            )
            failed = True
            continue

        value = float(value)

        if direction == "max":
            load = value / limit if limit else 0.0
            ok = value <= limit
            if ok:
                margin = f"{(1 - load) * 100:.0f}% of the limit unused"
            else:
                margin = f"over by {(value - limit):g} {unit}"
            limit_text = f"at most {limit:g} {unit}"
        else:
            load = limit / value if value else 0.0
            ok = value >= limit
            if ok:
                margin = f"{(value - limit):.2f} {unit} above the minimum"
            else:
                margin = f"short by {(limit - value):.2f} {unit}"
            limit_text = f"at least {limit:g} {unit}"

        if not ok:
            failed = True

        findings.append(
            {
                "line": label,
                "limit": limit_text,
                "measured": f"{value:,g} {unit}",
                "margin": margin,
                "load": round(load, 3),
                "verdict": "pass" if ok else "fail",
            }
        )

    for key, label, required in [
        ("ecoli", "E. coli", spec["ecoli_required"]),
        ("salmonella", "Salmonella", spec["salmonella_required"]),
    ]:
        reported = (measured.get(key) or "").strip()
        ok = reported.lower().startswith("absent")
        failed = failed or not ok
        findings.append(
            {
                "line": label,
                "limit": required,
                "measured": reported or "not reported",
                "margin": "as required" if ok else "does not meet the requirement",
                "load": 0.0 if ok else 1.0,
                "verdict": "pass" if ok else "fail",
            }
        )

    return ("fail" if failed else "pass"), findings
