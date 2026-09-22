# Outreach and negotiation copy

These four messages are rendered straight from `engine/copy.py`, which is
the code the agents send from. The agents fill the slots. They do not
rewrite the sentences, for three reasons.

1. A buyer can read exactly what goes out in their name before they approve
   the shortlist.
2. The same words to every supplier make their replies comparable.
3. A Request for Quotation that states its specification badly gets a bad
   quotation back, so this is the text most worth writing once and well.

The examples use a zinc citrate run. Figures are illustrative.

## 1. Opening Request for Quotation

Sent to every supplier on the approved shortlist. It states the full
specification up front and asks for the six things that make a quotation
comparable, so the parser has something to find. It tells the supplier
a failing certificate loses even at a low price, which sets the terms of
the negotiation before it starts.

**Subject:** Request for Quotation: Zinc (Zinc citrate trihydrate), 500 kg [AON-7Q4K2M-9XWD]

```text
Dear Jiangsu Vitalabs sales team,

Aonic is a functional nutrition company in San Francisco. We are sourcing
Zinc for a daily multinutrient and would like a quotation
from you.

WHAT WE NEED

  Material           Zinc, Zinc citrate trihydrate
  CAS number         5990-32-9
  Quantity           500 kg for a first order
  Required on site   within 84 days of order
  Delivered to       Aonic contract manufacturer, Illinois, United States

TARGET SPECIFICATION

  Assay              98.0% minimum. Zinc citrate by titration, 30.0 to 32.0% elemental zinc.
  Lead               0.5 ppm maximum
  Arsenic            1.0 ppm maximum
  Cadmium            0.3 ppm maximum
  Mercury            0.1 ppm maximum
  Total plate count  1,000 cfu/g maximum
  Yeast and mould    100 cfu/g maximum
  E. coli            Absent in 10 g
  Salmonella         Absent in 25 g
  Certification      GMP, ISO 22000

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

Please keep AON-7Q4K2M-9XWD in the subject line so your reply reaches the right
file.

Carla Mensah
Sourcing, Aonic Inc.
2261 Market Street #5416, San Francisco, CA 94114

--
This message was sent by an automated sourcing agent working for Aonic. A buyer approves every shortlist before outreach begins and every award before an order is placed.
```

## 2. Follow-up

Sent once, when a supplier has been silent past the follow-up window.
It names the three things that decide the order, invites a one-line
refusal, and says a partial answer today beats a complete one later.
There is no second chase. Silence after this closes the file.

**Subject:** Following up: Zinc, 500 kg [AON-7Q4K2M-9XWD]

```text
Dear Jiangsu Vitalabs sales team,

I wrote to you 2 days ago about 500 kg of
Zinc and have not heard back. I am following up once before
we close the enquiry.

If you can supply this material, the three things that decide it for us are
your price with its delivery term, your lead time in days, and a Certificate
of Analysis covering assay, heavy metals and microbiology.

If this material is outside what you carry, or the quantity is too small to
be worth your time, please say so in one line and I will take you off this
enquiry.

Our decision closes shortly, so a partial answer today is worth more than a
complete one next week.

Reference AON-7Q4K2M-9XWD.

Carla Mensah
Sourcing, Aonic Inc.
2261 Market Street #5416, San Francisco, CA 94114

--
This message was sent by an automated sourcing agent working for Aonic. A buyer approves every shortlist before outreach begins and every award before an order is placed.
```

## 3. Counter-offer

Sent when a normalised price sits above the ceiling. It shows the
supplier how we read their price, names the best rival on the same
basis without naming the rival, and explains that the ceiling comes
from what the product can carry, which makes it credible rather than a
haggling position. It offers three ways to close the gap, including two
that cost the supplier nothing on unit price.

**Subject:** Counter-offer: Zinc, 500 kg [AON-7Q4K2M-9XWD]

```text
Dear Jiangsu Vitalabs sales team,

Thank you for the quotation. Here is where it lands against the other
offers on this enquiry, and what we can do.

HOW WE READ YOUR PRICE

  We compare every quotation on one number: United States dollars per
  kilogram of active material, delivered to our door, with freight,
  duty and assay all taken into account. That way a price quoted ex
  works and a price quoted delivered can sit side by side.

  Your quotation normalises to $21.76 per kg delivered.
  The best of the other 5 offers is $19.43 per kg on the same basis.

WHAT WE CAN PAY

  $17.52 per kg delivered is our ceiling on this material. It is
  set by what the finished product can carry, not by haggling, so we
  cannot move above it whoever supplies us.

  We would place the order at $17.52 per kg delivered.

ALSO MISSING FROM YOUR QUOTATION

  1. Your payment terms.

THREE WAYS TO CLOSE THE GAP

  1. Move your unit price.
  2. Quote delivered duty paid instead of ex works, and carry the
     freight and duty yourself if you can buy it cheaper than we can.
  3. Improve the assay, since we pay for active material rather than
     for gross weight, and a higher assay lowers the delivered cost
     without changing your unit price.

This is round 1 of three. If we cannot reach agreement by
the third round I will close the file and come back to you on the next
enquiry.

Reference AON-7Q4K2M-9XWD.

Carla Mensah
Sourcing, Aonic Inc.
2261 Market Street #5416, San Francisco, CA 94114

--
This message was sent by an automated sourcing agent working for Aonic. A buyer approves every shortlist before outreach begins and every award before an order is placed.
```

## 4. Close

Sent only after a person approves the award at the second gate. It
restates every agreed term, including the delivered cost, and makes
release of the goods conditional on the shipped batch's certificate
passing the same specification the enquiry was sent with.

**Subject:** Agreed: Zinc, 500 kg at USD 14.60 per kg FOB [AON-7Q4K2M-9XWD]

```text
Dear Jiangsu Vitalabs sales team,

We have a deal. Thank you for working through the rounds with us.

WHAT WE AGREED

  Material           Zinc, Zinc citrate trihydrate
  Quantity           500 kg
  Price              USD 14.60 per kg, FOB
  Delivered cost     $17.46 per kg of active material
  Lead time          49 days from purchase order
  Certificate        batch JIA-2521G, checked against our specification

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

Reference AON-7Q4K2M-9XWD.

Carla Mensah
Sourcing, Aonic Inc.
2261 Market Street #5416, San Francisco, CA 94114

--
This message was sent by an automated sourcing agent working for Aonic. A buyer approves every shortlist before outreach begins and every award before an order is placed.
```
