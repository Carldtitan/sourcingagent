import Link from "next/link";
import { notFound } from "next/navigation";
import { db } from "@/lib/db";
import { ForceField } from "@/components/ForceField";
import { ApprovalCard } from "@/components/ApprovalCard";
import { RunPulse } from "@/components/RunPulse";
import { rank } from "@/lib/rank";

export const dynamic = "force-dynamic";

const STATUS_WORD: Record<string, string> = {
  qualifying: "Qualifying",
  awaiting_shortlist: "Waiting on you",
  outreach: "Sending",
  negotiating: "Negotiating",
  awaiting_award: "Waiting on you",
  closed: "Closed",
  cancelled: "Cancelled",
};

const ACTOR_WORD: Record<string, string> = {
  qualifier: "Qualifier",
  negotiator: "Negotiator",
  coa_reader: "Certificate reader",
  chaser: "Chaser",
  normaliser: "Normaliser",
  human: "You",
  supplier: "Supplier",
};

export default async function RunPage({
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

  const [
    { data: runSuppliers },
    { data: approvals },
    { data: events },
    { data: spec },
  ] = await Promise.all([
    supabase
      .from("run_suppliers")
      .select("*, suppliers(*)")
      .eq("run_id", id),
    supabase
      .from("approvals")
      .select("*")
      .eq("run_id", id)
      .eq("status", "open")
      .order("opened_at"),
    supabase
      .from("events")
      .select("*")
      .eq("run_id", id)
      .order("occurred_at", { ascending: false })
      .limit(60),
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
  });

  const dropped = (runSuppliers ?? []).filter((r) => r.qualified === false);
  const live = !["closed", "cancelled"].includes(run.status);
  const ingredient = run.ingredients as {
    name: string;
    chemical_form: string;
    budget_note: string | null;
  };

  return (
    <>
      <div className="headblock">
        <div className="headblock-title">
          <h1>{ingredient.name}</h1>
          <p>
            {Number(run.quantity_kg).toLocaleString()} kg of{" "}
            {ingredient.chemical_form.toLowerCase()}, needed within{" "}
            {run.needed_by_days} days.
          </p>
        </div>
        <div className="readout">
          <div>
            <span className="label">Status</span>
            <span className={`v ${live ? "hot" : ""}`}>
              {STATUS_WORD[run.status] ?? run.status}
            </span>
          </div>
          <div>
            <span className="label">Ceiling, $/kg active</span>
            <span className="v">{ceiling.toFixed(2)}</span>
          </div>
          <div>
            <span className="label">Offers on the table</span>
            <span className="v">{offers.length}</span>
          </div>
          <div>
            <span className="label">Rounds allowed</span>
            <span className="v">{run.guardrails?.max_rounds ?? 3}</span>
          </div>
        </div>
      </div>

      {live && <RunPulse runId={id} />}

      {(approvals ?? []).length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2>Waiting on you</h2>
            <span className="rule-note">
              nothing moves on these until you decide
            </span>
          </div>
          <div className="stack" style={{ paddingTop: 18 }}>
            {(approvals ?? []).map((approval) => (
              <ApprovalCard key={approval.id} approval={approval} />
            ))}
          </div>
        </section>
      )}

      {offers.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2>The structure under load</h2>
            <span className="rule-note">
              ceiling set by ${Number(run.guardrails?.ceiling_usd_per_kg_active).toFixed(2)} of
              cost the pouch can carry
            </span>
          </div>
          <div style={{ paddingTop: 20 }}>
            <ForceField
              ceiling={ceiling}
              offers={offers.map((o) => ({
                id: o.runSupplierId,
                supplier: o.supplier,
                country: o.country,
                delivered: o.delivered,
                rounds: o.rounds,
                stage: o.stage,
                coa: o.coaVerdict,
              }))}
            />
          </div>
        </section>
      )}

      <section className="section">
        <div className="section-head">
          <h2>Offers</h2>
          <span className="rule-note">
            ranked on delivered cost, lead time, certificate and certification
          </span>
        </div>
        {offers.length === 0 ? (
          <p style={{ paddingTop: 20, color: "var(--ink-2)" }}>
            No quotations have come back yet. Requests go out once you approve
            the shortlist, and replies arrive by email a few seconds later.
          </p>
        ) : (
          <table className="ledger">
            <thead>
              <tr>
                <th>#</th>
                <th>Supplier</th>
                <th>As quoted</th>
                <th className="r">$/kg active</th>
                <th className="r">Against ceiling</th>
                <th className="r">Lead</th>
                <th>Certificate</th>
                <th className="r">Rds</th>
                <th className="r">Score</th>
              </tr>
            </thead>
            <tbody>
              {offers.map((offer, index) => (
                <tr
                  key={offer.runSupplierId}
                  className={index === 0 ? "is-lead" : undefined}
                >
                  <td className="num" style={{ color: "var(--ink-3)" }}>
                    {index + 1}
                  </td>
                  <td>
                    <Link href={`/runs/${id}/threads/${offer.runSupplierId}`}>
                      {offer.supplier}
                    </Link>
                    <span className="sub">
                      {offer.country} · {offer.kind}
                    </span>
                  </td>
                  <td className="num" style={{ fontSize: 12 }}>
                    {offer.quoted}
                  </td>
                  <td className="r num" style={{ fontWeight: 500 }}>
                    {offer.delivered.toFixed(2)}
                  </td>
                  <td className="r">
                    <div className="load">
                      <span
                        className="num"
                        style={{
                          fontSize: 11.5,
                          color:
                            offer.delivered > ceiling
                              ? "var(--breach)"
                              : "var(--ink-2)",
                        }}
                      >
                        {offer.delivered > ceiling ? "+" : "−"}
                        {Math.abs(offer.delivered - ceiling).toFixed(2)}
                      </span>
                      <span className="load-track">
                        <span
                          className={`load-fill ${
                            offer.delivered > ceiling
                              ? "over"
                              : offer.delivered > ceiling * 0.92
                                ? "near"
                                : ""
                          }`}
                          style={{
                            right: "auto",
                            width: `${Math.min(
                              100,
                              (offer.delivered / ceiling) * 100
                            )}%`,
                          }}
                        />
                      </span>
                    </div>
                  </td>
                  <td className="r num">
                    {offer.leadTimeDays ? `${offer.leadTimeDays}d` : "—"}
                  </td>
                  <td>
                    <Link
                      href={`/runs/${id}/certificates#${offer.runSupplierId}`}
                      style={{ textDecoration: "none" }}
                    >
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
                          ? "none yet"
                          : offer.coaVerdict}
                      </span>
                    </Link>
                  </td>
                  <td className="r num">{offer.rounds}</td>
                  <td className="r num" style={{ fontWeight: 500 }}>
                    {offer.score.total.toFixed(0)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {offers.length > 0 && (
          <div className="row" style={{ paddingTop: 20 }}>
            <Link className="btn" href={`/runs/${id}/compare`}>
              Full comparison
            </Link>
            <Link className="btn" href={`/runs/${id}/certificates`}>
              Certificates
            </Link>
          </div>
        )}
      </section>

      {dropped.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2>Not qualified</h2>
            <span className="rule-note">
              {dropped.length} dropped before anything was sent
            </span>
          </div>
          <table className="ledger">
            <tbody>
              {dropped.map((row) => (
                <tr key={row.id} className="is-void">
                  <td style={{ width: 240 }}>
                    {(row.suppliers as { name: string }).name}
                    <span className="sub">
                      {(row.suppliers as { country: string }).country}
                    </span>
                  </td>
                  <td>{row.disqualify_reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="section">
        <div className="section-head">
          <h2>What happened</h2>
          <span className="rule-note">newest first</span>
        </div>
        <table className="ledger">
          <tbody>
            {(events ?? []).map((event) => (
              <tr key={event.id}>
                <td className="num" style={{ width: 92, color: "var(--ink-3)" }}>
                  {new Date(event.occurred_at).toLocaleTimeString("en-GB", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </td>
                <td style={{ width: 150 }}>
                  <span className="label" style={{ color: "var(--ink-2)" }}>
                    {ACTOR_WORD[event.actor] ?? event.actor}
                  </span>
                </td>
                <td>{event.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
