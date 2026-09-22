import Link from "next/link";
import { notFound } from "next/navigation";
import { db } from "@/lib/db";
import { rank } from "@/lib/rank";

export const dynamic = "force-dynamic";

export default async function ComparePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = db();

  const { data: run } = await supabase
    .from("runs")
    .select("*, ingredients(*)")
    .eq("id", id)
    .single();
  if (!run) notFound();

  const [{ data: runSuppliers }, { data: spec }] = await Promise.all([
    supabase.from("run_suppliers").select("*, suppliers(*)").eq("run_id", id),
    supabase
      .from("specifications")
      .select("*")
      .eq("ingredient_id", run.ingredient_id)
      .single(),
  ]);

  const ids = (runSuppliers ?? []).map((r) => r.id);
  const [{ data: quotes }, { data: coas }] = ids.length
    ? await Promise.all([
        supabase.from("quotes").select("*").in("run_supplier_id", ids),
        supabase.from("coas").select("*").in("run_supplier_id", ids),
      ])
    : [{ data: [] }, { data: [] }];

  const ceiling = Number(run.guardrails?.ceiling_usd_per_kg_active ?? 0);
  const offers = rank({
    runSuppliers: runSuppliers ?? [],
    quotes: quotes ?? [],
    coas: coas ?? [],
    ceiling,
    maxLeadTime: Number(run.guardrails?.max_lead_time_days ?? 84),
    requiredCerts: spec?.required_certs ?? [],
  }).slice(0, 5);

  const ingredient = run.ingredients as Record<string, any>;

  return (
    <>
      <div className="headblock">
        <div className="headblock-title">
          <h1>{ingredient.name}: the offers side by side</h1>
          <p>
            Every quotation converted to one number, dollars per kilogram of
            active material delivered to our door. That is the only way a price
            quoted ex works in euros per kilogram and a price quoted delivered
            in dollars per pound can be compared.
          </p>
          <p style={{ marginTop: 6 }}>
            <Link href={`/runs/${id}`}>Back to the run</Link>
          </p>
        </div>
        <div className="readout">
          <div>
            <span className="label">Order</span>
            <span className="v">
              {Number(run.quantity_kg).toLocaleString()} kg
            </span>
          </div>
          <div>
            <span className="label">Ceiling</span>
            <span className="v">${ceiling.toFixed(2)}</span>
          </div>
          <div>
            <span className="label">Offers</span>
            <span className="v">{offers.length}</span>
          </div>
        </div>
      </div>

      <section className="section">
        <div className="section-head">
          <h2>Comparison</h2>
          <span className="rule-note">ranked</span>
        </div>

        <div style={{ overflowX: "auto", paddingTop: 10 }}>
          <table className="ledger" style={{ minWidth: 980 }}>
            <thead>
              <tr>
                <th>#</th>
                <th>Supplier</th>
                <th>Origin</th>
                <th>As quoted</th>
                <th className="r">Freight</th>
                <th className="r">Duty</th>
                <th className="r">Assay</th>
                <th className="r">$/kg active</th>
                <th className="r">Order value</th>
                <th className="r">Lead</th>
                <th>Payment</th>
                <th>Certificate</th>
                <th className="r">Rds</th>
                <th className="r">Score</th>
              </tr>
            </thead>
            <tbody>
              {offers.map((offer, index) => {
                const quote = (quotes ?? []).find(
                  (q) =>
                    q.run_supplier_id === offer.runSupplierId &&
                    Number(q.usd_per_kg_active) === offer.delivered
                );
                return (
                  <tr
                    key={offer.runSupplierId}
                    className={
                      offer.stage === "walked_away"
                        ? "is-void"
                        : index === 0
                          ? "is-lead"
                          : undefined
                    }
                  >
                    <td className="num" style={{ color: "var(--ink-3)" }}>
                      {index + 1}
                    </td>
                    <td>
                      <Link href={`/runs/${id}/threads/${offer.runSupplierId}`}>
                        {offer.supplier}
                      </Link>
                      <span className="sub">
                        {offer.kind}
                        {offer.stage === "walked_away" ? " · we walked away" : ""}
                        {offer.stage === "agreed" ? " · agreed" : ""}
                      </span>
                    </td>
                    <td>{offer.country}</td>
                    <td className="num" style={{ fontSize: 12 }}>
                      {offer.quoted}
                    </td>
                    <td className="r num" style={{ fontSize: 12 }}>
                      {quote?.freight_usd_per_kg
                        ? `+${Number(quote.freight_usd_per_kg).toFixed(2)}`
                        : "—"}
                    </td>
                    <td className="r num" style={{ fontSize: 12 }}>
                      {quote?.duty_usd_per_kg
                        ? `+${Number(quote.duty_usd_per_kg).toFixed(2)}`
                        : "—"}
                    </td>
                    <td className="r num" style={{ fontSize: 12 }}>
                      {offer.purityPct ? `${offer.purityPct.toFixed(1)}%` : "—"}
                    </td>
                    <td className="r num" style={{ fontWeight: 600 }}>
                      ${offer.delivered.toFixed(2)}
                    </td>
                    <td className="r num">
                      $
                      {(offer.delivered * Number(run.quantity_kg)).toLocaleString(
                        "en-US",
                        { maximumFractionDigits: 0 }
                      )}
                    </td>
                    <td className="r num">
                      {offer.leadTimeDays ? `${offer.leadTimeDays}d` : "—"}
                    </td>
                    <td style={{ fontSize: 11.5, color: "var(--ink-2)" }}>
                      {offer.paymentTerms ?? "not stated"}
                    </td>
                    <td>
                      <span
                        className={`verdict ${
                          offer.coaVerdict === "pass"
                            ? "pass"
                            : offer.coaVerdict === "fail"
                              ? "fail"
                              : "pending"
                        }`}
                      >
                        {offer.coaVerdict === "not_received"
                          ? "none"
                          : offer.coaVerdict}
                      </span>
                      {offer.batchNo && (
                        <span className="sub num">{offer.batchNo}</span>
                      )}
                    </td>
                    <td className="r num">{offer.rounds}</td>
                    <td className="r num" style={{ fontWeight: 500 }}>
                      {offer.score.total.toFixed(0)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {offers.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2>How the leading price was worked out</h2>
            <span className="rule-note">{offers[0].supplier}</span>
          </div>
          <table className="ledger">
            <tbody>
              {(offers[0].normalisation?.steps ?? []).map((step, index) => (
                <tr key={index}>
                  <td style={{ width: 230 }}>{step.label}</td>
                  <td className="num" style={{ width: 210, fontWeight: 500 }}>
                    {step.value}
                  </td>
                  <td style={{ fontSize: 12, color: "var(--ink-3)" }}>
                    {step.note ?? ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="notice assumption" style={{ marginTop: 20 }}>
            <strong>Freight and duty are our working rates.</strong> Sea freight
            and inland delivery are estimated per origin, and duty is applied on
            the goods value at the rate for that origin. A real run would use
            the freight quotation and the tariff code for the material.
          </div>
        </section>
      )}
    </>
  );
}
