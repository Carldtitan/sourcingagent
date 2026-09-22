import Link from "next/link";
import { db } from "@/lib/db";
import { NewBrief } from "@/components/NewBrief";

export const dynamic = "force-dynamic";

const STATUS_WORD: Record<string, string> = {
  qualifying: "Qualifying suppliers",
  awaiting_shortlist: "Waiting for you to approve the shortlist",
  outreach: "Sending requests",
  negotiating: "Negotiating",
  awaiting_award: "Waiting for you to approve the award",
  closed: "Closed",
  cancelled: "Cancelled",
};

const STATUS_MARK: Record<string, string> = {
  qualifying: "live",
  awaiting_shortlist: "pending",
  outreach: "live",
  negotiating: "live",
  awaiting_award: "pending",
  closed: "agreed",
  cancelled: "void",
};

export default async function Home() {
  const supabase = db();

  const [{ data: ingredients }, { data: runs }, { data: costModel }] =
    await Promise.all([
      supabase.from("ingredients").select("*").order("sort_order"),
      supabase
        .from("runs")
        .select("*, ingredients(name, chemical_form)")
        .order("created_at", { ascending: false })
        .limit(25),
      supabase.from("cost_model").select("*").eq("id", "aonic-complete").single(),
    ]);

  const runIds = (runs ?? []).map((r) => r.id);
  const { data: offerCounts } = runIds.length
    ? await supabase
        .from("run_suppliers")
        .select("run_id, stage")
        .in("run_id", runIds)
    : { data: [] as { run_id: string; stage: string }[] };

  const shortlisted = new Map<string, number>();
  for (const row of offerCounts ?? []) {
    if (row.stage === "rejected") continue;
    shortlisted.set(row.run_id, (shortlisted.get(row.run_id) ?? 0) + 1);
  }

  return (
    <>
      <div className="headblock">
        <div className="headblock-title">
          <h1>Ingredient briefs</h1>
          <p>
            One brief becomes three to five validated, comparable supplier
            offers. The engine qualifies suppliers, emails them, reads their
            replies and certificates, negotiates inside a ceiling set by the
            product&rsquo;s own cost, and stops at every point where a person
            should decide.
          </p>
        </div>
        <div className="readout">
          <div>
            <span className="label">Product</span>
            <span className="v">Aonic Complete</span>
          </div>
          <div>
            <span className="label">Ingredient cost per pouch</span>
            <span className="v">
              ${Number(costModel?.ingredients_usd ?? 0).toFixed(2)}
            </span>
          </div>
          <div>
            <span className="label">Servings</span>
            <span className="v">{costModel?.servings_per_pouch ?? 30}</span>
          </div>
        </div>
      </div>

      <section className="section">
        <div className="section-head">
          <h2>Open a brief</h2>
          <span className="rule-note">
            The ceiling is calculated, not typed
          </span>
        </div>
        <NewBrief
          ingredients={(ingredients ?? []).map((i) => ({
            id: i.id,
            name: i.name,
            chemical_form: i.chemical_form,
            dose_mg: Number(i.dose_mg),
            budget_note: i.budget_note,
            ceiling:
              Number(i.cost_budget_usd_per_pouch) /
              ((Number(i.dose_mg) * Number(costModel?.servings_per_pouch ?? 30)) /
                1_000_000),
          }))}
        />
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Runs</h2>
          <span className="rule-note">{runs?.length ?? 0} total</span>
        </div>

        {(runs ?? []).length === 0 ? (
          <p style={{ paddingTop: 20, color: "var(--ink-2)" }}>
            Nothing has been sourced yet. Open a brief above and the first
            Request for Quotation goes out as soon as you approve the
            shortlist.
          </p>
        ) : (
          <table className="ledger">
            <thead>
              <tr>
                <th>Ingredient</th>
                <th className="r">Quantity</th>
                <th className="r">Ceiling</th>
                <th className="r">In play</th>
                <th>Status</th>
                <th>Opened</th>
              </tr>
            </thead>
            <tbody>
              {(runs ?? []).map((run) => (
                <tr key={run.id}>
                  <td>
                    <Link href={`/runs/${run.id}`}>
                      {(run.ingredients as { name: string } | null)?.name ??
                        run.ingredient_id}
                    </Link>
                    <span className="sub">
                      {(run.ingredients as { chemical_form: string } | null)
                        ?.chemical_form ?? ""}
                    </span>
                  </td>
                  <td className="r num">
                    {Number(run.quantity_kg).toLocaleString()} kg
                  </td>
                  <td className="r num">
                    $
                    {Number(
                      run.guardrails?.ceiling_usd_per_kg_active ?? 0
                    ).toFixed(2)}
                  </td>
                  <td className="r num">{shortlisted.get(run.id) ?? 0}</td>
                  <td>
                    <span className={`verdict ${STATUS_MARK[run.status]}`}>
                      {STATUS_WORD[run.status] ?? run.status}
                    </span>
                  </td>
                  <td className="num" style={{ color: "var(--ink-3)" }}>
                    {new Date(run.created_at).toLocaleString("en-GB", {
                      day: "2-digit",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}
