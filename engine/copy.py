"""The outreach and negotiation copy.

Four moments: the opening Request for Quotation, the follow-up when a
supplier goes quiet, the counter-offer when a price comes back above what
the product can carry, and the close when terms are agreed.

The copy is written here rather than generated, for three reasons. A buyer
has to be able to read exactly what goes out in their name before they
approve it. The same words every time make a supplier's reply comparable
across twelve of them. And a quotation that states its specification badly
gets a bad quotation back, so this text is the part of the system that most
rewards being written once and written well.

The agents fill the slots. They do not rewrite the sentences.
"""

from __future__ import annotations

from dataclasses import dataclass


SIGNATURE = """
Carla Mensah
Sourcing, Aonic Inc.
2261 Market Street #5416, San Francisco, CA 94114
""".strip()

DISCLOSURE = (
    "This message was sent by an automated sourcing agent working for Aonic. "
    "A buyer approves every shortlist before outreach begins and every award "
    "before an order is placed."
)


@dataclass
class Draft:
    subject: str
    body: str


def _spec_block(spec: dict) -> str:
    certs = ", ".join(spec["required_certs"])
    return "\n".join(
        [
            f"  Assay              {spec['assay_min_pct']}% minimum. {spec['assay_basis']}.",
            f"  Lead               {spec['lead_max_ppm']} ppm maximum",
            f"  Arsenic            {spec['arsenic_max_ppm']} ppm maximum",
            f"  Cadmium            {spec['cadmium_max_ppm']} ppm maximum",
            f"  Mercury            {spec['mercury_max_ppm']} ppm maximum",
            f"  Total plate count  {int(spec['tpc_max_cfu_g']):,} cfu/g maximum",
            f"  Yeast and mould    {int(spec['yeast_mould_max_cfu_g']):,} cfu/g maximum",
            f"  E. coli            {spec['ecoli_required']}",
            f"  Salmonella         {spec['salmonella_required']}",
            f"  Certification      {certs}",
        ]
    )


# --------------------------------------------------------------------- RFQ

def rfq(*, supplier: dict, ingredient: dict, spec: dict, run: dict, reference: str) -> Draft:
    subject = (
        f"Request for Quotation: {ingredient['name']} "
        f"({ingredient['chemical_form']}), {run['quantity_kg']:,.0f} kg [{reference}]"
    )

    body = f"""Dear {supplier['name']} sales team,

Aonic is a functional nutrition company in San Francisco. We are sourcing
{ingredient['name']} for a daily multinutrient and would like a quotation
from you.

WHAT WE NEED

  Material           {ingredient['name']}, {ingredient['chemical_form']}
  CAS number         {ingredient['cas_number'] or 'not specified'}
  Quantity           {run['quantity_kg']:,.0f} kg for a first order
  Required on site   within {run['needed_by_days']} days of order
  Delivered to       Aonic contract manufacturer, Illinois, United States

TARGET SPECIFICATION

{_spec_block(spec)}

PLEASE QUOTE

  1. Your price, stating the currency, the unit and the delivery term.
  2. The quantity that price holds for, and your minimum order quantity.
  3. Lead time in days from purchase order to shipment.
  4. Payment terms.
  5. Country of manufacture.
  6. How long the price stays valid.

PLEASE ATTACH

  A recent Certificate of Analysis for this material, as a PDF. We compare
  every line of it against the specification above before we shortlist a
  supplier, so a certificate that omits heavy metals or microbiology will
  send us back to you for a second one.

We are running this enquiry with several qualified suppliers and will
decide on delivered cost per kilogram of active material, lead time and
certificate quality together. A low price with a failing certificate does
not win.

Please keep {reference} in the subject line so your reply reaches the right
file.

{SIGNATURE}

--
{DISCLOSURE}
"""
    return Draft(subject, body)


# ---------------------------------------------------------------- follow-up

def followup(
    *, supplier: dict, ingredient: dict, run: dict, reference: str, days_quiet: int
) -> Draft:
    subject = (
        f"Following up: {ingredient['name']}, {run['quantity_kg']:,.0f} kg [{reference}]"
    )

    body = f"""Dear {supplier['name']} sales team,

I wrote to you {days_quiet} days ago about {run['quantity_kg']:,.0f} kg of
{ingredient['name']} and have not heard back. I am following up once before
we close the enquiry.

If you can supply this material, the three things that decide it for us are
your price with its delivery term, your lead time in days, and a Certificate
of Analysis covering assay, heavy metals and microbiology.

If this material is outside what you carry, or the quantity is too small to
be worth your time, please say so in one line and I will take you off this
enquiry.

Our decision closes shortly, so a partial answer today is worth more than a
complete one next week.

Reference {reference}.

{SIGNATURE}

--
{DISCLOSURE}
"""
    return Draft(subject, body)


# ------------------------------------------------------------- counter-offer

def counter(
    *,
    supplier: dict,
    ingredient: dict,
    run: dict,
    reference: str,
    their_delivered: float,
    target_delivered: float,
    ceiling: float,
    best_rival_delivered: float | None,
    rival_count: int,
    round_number: int,
    gaps: list[str],
) -> Draft:
    subject = (
        f"Counter-offer: {ingredient['name']}, {run['quantity_kg']:,.0f} kg "
        f"[{reference}]"
    )

    lines = [
        f"Dear {supplier['name']} sales team,",
        "",
        "Thank you for the quotation. Here is where it lands against the other",
        "offers on this enquiry, and what we can do.",
        "",
        "HOW WE READ YOUR PRICE",
        "",
        "  We compare every quotation on one number: United States dollars per",
        "  kilogram of active material, delivered to our door, with freight,",
        "  duty and assay all taken into account. That way a price quoted ex",
        "  works and a price quoted delivered can sit side by side.",
        "",
        f"  Your quotation normalises to ${their_delivered:,.2f} per kg delivered.",
    ]

    if best_rival_delivered is not None:
        lines.append(
            f"  The best of the other {rival_count} offers is "
            f"${best_rival_delivered:,.2f} per kg on the same basis."
        )

    lines += [
        "",
        "WHAT WE CAN PAY",
        "",
        f"  ${ceiling:,.2f} per kg delivered is our ceiling on this material. It is",
        "  set by what the finished product can carry, not by haggling, so we",
        "  cannot move above it whoever supplies us.",
        "",
        f"  We would place the order at ${target_delivered:,.2f} per kg delivered.",
    ]

    if gaps:
        lines += ["", "ALSO MISSING FROM YOUR QUOTATION", ""]
        lines += [f"  {n}. {g}" for n, g in enumerate(gaps, start=1)]

    lines += [
        "",
        "THREE WAYS TO CLOSE THE GAP",
        "",
        "  1. Move your unit price.",
        "  2. Quote delivered duty paid instead of ex works, and carry the",
        "     freight and duty yourself if you can buy it cheaper than we can.",
        "  3. Improve the assay, since we pay for active material rather than",
        "     for gross weight, and a higher assay lowers the delivered cost",
        "     without changing your unit price.",
        "",
        f"This is round {round_number} of three. If we cannot reach agreement by",
        "the third round I will close the file and come back to you on the next",
        "enquiry.",
        "",
        f"Reference {reference}.",
        "",
        SIGNATURE,
        "",
        "--",
        DISCLOSURE,
    ]

    return Draft(subject, "\n".join(lines) + "\n")


# ------------------------------------------------------------------- close

def close(
    *,
    supplier: dict,
    ingredient: dict,
    spec: dict,
    run: dict,
    reference: str,
    agreed_price: float,
    currency: str,
    unit: str,
    incoterm: str,
    delivered: float,
    lead_time_days: int,
    batch_no: str | None,
) -> Draft:
    subject = (
        f"Agreed: {ingredient['name']}, {run['quantity_kg']:,.0f} kg at "
        f"{currency} {agreed_price:,.2f} per {unit} {incoterm} [{reference}]"
    )

    coa_line = (
        f"  Certificate        batch {batch_no}, checked against our specification\n"
        if batch_no
        else "  Certificate        to be supplied with the shipment\n"
    )

    body = f"""Dear {supplier['name']} sales team,

We have a deal. Thank you for working through the rounds with us.

WHAT WE AGREED

  Material           {ingredient['name']}, {ingredient['chemical_form']}
  Quantity           {run['quantity_kg']:,.0f} kg
  Price              {currency} {agreed_price:,.2f} per {unit}, {incoterm}
  Delivered cost     ${delivered:,.2f} per kg of active material
  Lead time          {lead_time_days} days from purchase order
{coa_line}
WHAT HAPPENS NEXT

  1. Our buyer countersigns this agreement, which has already been approved
     on our side.
  2. We raise a purchase order against it within two working days.
  3. You confirm the order and send the production batch number.
  4. You send the Certificate of Analysis for the shipped batch before the
     material leaves your site. We check it against the same specification
     we sent with the enquiry, and a batch outside any limit is held at our
     warehouse rather than released into production.

Please reply confirming these terms and the batch you will ship against.

Reference {reference}.

{SIGNATURE}

--
{DISCLOSURE}
"""
    return Draft(subject, body)


# ------------------------------------------------ closing a supplier we drop

def decline(*, supplier: dict, ingredient: dict, reference: str, reason: str) -> Draft:
    subject = f"Closing our enquiry: {ingredient['name']} [{reference}]"
    body = f"""Dear {supplier['name']} sales team,

Thank you for your time on this enquiry. We have placed the order elsewhere.

{reason}

We buy this material regularly and will come back to you on the next
enquiry, so please keep our details on file.

Reference {reference}.

{SIGNATURE}

--
{DISCLOSURE}
"""
    return Draft(subject, body)
