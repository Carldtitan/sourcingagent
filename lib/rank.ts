/**
 * Ranking offers for display.
 *
 * The arithmetic mirrors engine/normalise.py so the interface and the agents
 * never disagree about which offer leads. Prices themselves are normalised in
 * Python when a quotation arrives and stored on the quote, so nothing is
 * recalculated here.
 */

export type RankedOffer = {
  runSupplierId: string;
  supplier: string;
  country: string;
  kind: string;
  certs: string[];
  quoted: string;
  delivered: number;
  leadTimeDays: number | null;
  purityPct: number | null;
  paymentTerms: string | null;
  incoterm: string;
  coaVerdict: "pass" | "fail" | "not_received";
  batchNo: string | null;
  rounds: number;
  stage: string;
  normalisation: { steps: { label: string; value: string; note?: string }[] } | null;
  score: {
    total: number;
    price: number;
    leadTime: number;
    certificate: number;
    certification: number;
  };
};

type Row = Record<string, any>;

export function rank({
  runSuppliers,
  quotes,
  coas,
  ceiling,
  maxLeadTime,
  requiredCerts,
}: {
  runSuppliers: Row[];
  quotes: Row[];
  coas: Row[];
  ceiling: number;
  maxLeadTime: number;
  requiredCerts: string[];
}): RankedOffer[] {
  const latestQuote = new Map<string, Row>();
  for (const quote of quotes) {
    const held = latestQuote.get(quote.run_supplier_id);
    if (!held || quote.round >= held.round) latestQuote.set(quote.run_supplier_id, quote);
  }

  const latestCoa = new Map<string, Row>();
  for (const coa of coas) {
    const held = latestCoa.get(coa.run_supplier_id);
    if (!held || coa.created_at >= held.created_at)
      latestCoa.set(coa.run_supplier_id, coa);
  }

  const candidates = runSuppliers.filter(
    (row) => row.qualified && latestQuote.has(row.id)
  );
  if (candidates.length === 0) return [];

  const best = Math.min(
    ...candidates.map((row) => Number(latestQuote.get(row.id)!.usd_per_kg_active))
  );

  const offers = candidates.map((row) => {
    const quote = latestQuote.get(row.id)!;
    const coa = latestCoa.get(row.id);
    const supplier = row.suppliers as Row;
    const delivered = Number(quote.usd_per_kg_active);
    const coaVerdict = (coa?.verdict ?? "not_received") as RankedOffer["coaVerdict"];
    const certs: string[] = supplier.certs ?? [];

    const priceScore = delivered ? Math.max(0, Math.min(1, best / delivered)) : 0;
    const leadScore =
      quote.lead_time_days == null
        ? 0.5
        : Math.max(0, Math.min(1, 1 - Number(quote.lead_time_days) / Math.max(maxLeadTime, 1)));
    const coaScore = { pass: 1, not_received: 0.4, fail: 0 }[coaVerdict] ?? 0.4;
    const holdsAll = requiredCerts.every((c) => certs.includes(c));
    const extra = certs.filter((c) => !requiredCerts.includes(c)).length;
    const certScore = holdsAll ? Math.min(1, 0.7 + 0.1 * extra) : 0;

    const total =
      priceScore * 0.5 + leadScore * 0.2 + coaScore * 0.2 + certScore * 0.1;

    return {
      runSupplierId: row.id,
      supplier: supplier.name,
      country: supplier.country,
      kind: supplier.kind,
      certs,
      quoted: `${quote.currency} ${Number(quote.price).toFixed(2)}/${quote.unit} ${quote.incoterm}`,
      delivered,
      leadTimeDays: quote.lead_time_days ?? null,
      purityPct: quote.purity_pct ? Number(quote.purity_pct) : null,
      paymentTerms: quote.payment_terms ?? null,
      incoterm: quote.incoterm,
      coaVerdict,
      batchNo: coa?.batch_no ?? null,
      rounds: Number(row.round ?? 0),
      stage: row.stage,
      normalisation: quote.normalisation_note ?? null,
      score: {
        total: Number((total * 100).toFixed(1)),
        price: Number((priceScore * 100).toFixed(1)),
        leadTime: Number((leadScore * 100).toFixed(1)),
        certificate: Number((coaScore * 100).toFixed(1)),
        certification: Number((certScore * 100).toFixed(1)),
      },
    } satisfies RankedOffer;
  });

  // Offers still in play rank above ones we walked away from, so the leader
  // is always something the buyer can actually award.
  const settled = (stage: string) => (stage === "walked_away" ? 1 : 0);
  offers.sort(
    (a, b) =>
      settled(a.stage) - settled(b.stage) ||
      b.score.total - a.score.total ||
      a.delivered - b.delivered
  );
  return offers;
}
