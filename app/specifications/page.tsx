import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

const WHY: Record<string, string> = {
  assay:
    "We pay for active material, so assay changes the real price of a kilogram.",
  lead: "Accumulates in the body and is regulated in finished supplements.",
  arsenic: "Travels with mineral and botanical raw materials.",
  cadmium: "Found alongside zinc in ore, so it matters most on zinc salts.",
  mercury: "Standard heavy metal panel for a supplement ingredient.",
  tpc: "A high count points at hygiene in the plant.",
  mould: "Points at storage and moisture control.",
  pathogens: "A single positive result rejects the batch outright.",
  certs:
    "Aonic is responsible for what it sells, even when someone else made the material.",
  commercial:
    "A low price is useless when the smallest order is years of demand.",
};

export default async function SpecificationsPage() {
  const supabase = db();
  const [{ data: ingredients }, { data: specs }, { data: costModel }] =
    await Promise.all([
      supabase.from("ingredients").select("*").order("sort_order"),
      supabase.from("specifications").select("*"),
      supabase.from("cost_model").select("*").eq("id", "aonic-complete").single(),
    ]);

  const specFor = new Map((specs ?? []).map((s) => [s.ingredient_id, s]));
  const servings = Number(costModel?.servings_per_pouch ?? 30);
  const ingredientCost = Number(costModel?.ingredients_usd ?? 12.6);

  return (
    <>
      <div className="headblock">
        <div className="headblock-title">
          <h1>Specifications and ceilings</h1>
          <p>
            The specification decides whether a batch may be used. The ceiling
            decides what may be paid for it. Both are set out here, so a buyer
            can see exactly what the agents hold the line on.
          </p>
        </div>
        <div className="readout">
          <div>
            <span className="label">Ingredient cost a pouch carries</span>
            <span className="v">${ingredientCost.toFixed(2)}</span>
          </div>
          <div>
            <span className="label">Servings a pouch</span>
            <span className="v">{servings}</span>
          </div>
          <div>
            <span className="label">Member price</span>
            <span className="v">
              ${Number(costModel?.member_price_usd ?? 0).toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      <div className="section">
        <div className="notice assumption">
          <strong>Where these numbers come from.</strong> The ingredients and
          doses are read off the published Aonic Complete Supplement Facts
          panel. The cost of a pouch comes from {costModel?.source_note} The
          purity limits, contaminant ceilings and certification requirements are
          written by us against standard industry practice, because
          Aonic&rsquo;s internal specification sheet was not supplied.
        </div>
      </div>

      {(ingredients ?? []).map((ingredient) => {
        const spec = specFor.get(ingredient.id);
        const gramsPerPouch = (Number(ingredient.dose_mg) * servings) / 1000;
        const ceiling =
          Number(ingredient.cost_budget_usd_per_pouch) / (gramsPerPouch / 1000);

        const rows = spec
          ? [
              ["Assay", `at least ${spec.assay_min_pct}%`, WHY.assay],
              ["Lead", `at most ${spec.lead_max_ppm} ppm`, WHY.lead],
              ["Arsenic", `at most ${spec.arsenic_max_ppm} ppm`, WHY.arsenic],
              ["Cadmium", `at most ${spec.cadmium_max_ppm} ppm`, WHY.cadmium],
              ["Mercury", `at most ${spec.mercury_max_ppm} ppm`, WHY.mercury],
              [
                "Total plate count",
                `at most ${Number(spec.tpc_max_cfu_g).toLocaleString()} cfu/g`,
                WHY.tpc,
              ],
              [
                "Yeast and mould",
                `at most ${Number(spec.yeast_mould_max_cfu_g).toLocaleString()} cfu/g`,
                WHY.mould,
              ],
              [
                "Pathogens",
                `${spec.ecoli_required}, ${spec.salmonella_required}`,
                WHY.pathogens,
              ],
              ["Certification", spec.required_certs.join(", "), WHY.certs],
              [
                "Commercial limits",
                `minimum order at most ${Number(spec.max_moq_kg).toLocaleString()} kg, lead time at most ${spec.max_lead_time_days} days`,
                WHY.commercial,
              ],
              [
                "Accepted origins",
                spec.accepted_origins.join(", "),
                spec.source_note,
              ],
            ]
          : [];

        return (
          <section className="section" key={ingredient.id}>
            <div className="section-head">
              <h2>{ingredient.name}</h2>
              <span className="rule-note">
                {ingredient.chemical_form}
                {ingredient.cas_number ? ` · CAS ${ingredient.cas_number}` : ""}
              </span>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: 18,
                padding: "20px 0 4px",
              }}
            >
              <div className="node">
                <span className="label">Per serving</span>
                <span className="num" style={{ fontSize: 19 }}>
                  {Number(ingredient.dose_mg) < 1
                    ? `${(Number(ingredient.dose_mg) * 1000).toFixed(0)} mcg`
                    : `${Number(ingredient.dose_mg)} mg`}
                </span>
              </div>
              <div className="node">
                <span className="label">In one pouch</span>
                <span className="num" style={{ fontSize: 19 }}>
                  {gramsPerPouch < 1
                    ? `${(gramsPerPouch * 1000).toFixed(1)} mg`
                    : `${gramsPerPouch.toFixed(2)} g`}
                </span>
              </div>
              <div className="node">
                <span className="label">Budget per pouch</span>
                <span className="num" style={{ fontSize: 19 }}>
                  ${Number(ingredient.cost_budget_usd_per_pouch).toFixed(5)}
                </span>
                <p style={{ fontSize: 12, margin: "6px 0 0" }}>
                  {(
                    (Number(ingredient.cost_budget_usd_per_pouch) /
                      ingredientCost) *
                    100
                  ).toFixed(2)}
                  % of the ingredient cost
                </p>
              </div>
              <div className="node is-live">
                <span className="label">Ceiling, $/kg active</span>
                <span
                  className="num"
                  style={{ fontSize: 19, color: "var(--tension)" }}
                >
                  ${ceiling.toFixed(2)}
                </span>
                <p style={{ fontSize: 12, margin: "6px 0 0" }}>
                  budget divided by the mass in a pouch
                </p>
              </div>
            </div>

            {ingredient.budget_note && (
              <p style={{ fontSize: 13 }}>{ingredient.budget_note}</p>
            )}

            <table className="ledger">
              <thead>
                <tr>
                  <th>Test</th>
                  <th>Limit</th>
                  <th>Why it is there</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(([test, limit, why]) => (
                  <tr key={String(test)}>
                    <td style={{ width: 180 }}>{test}</td>
                    <td className="num" style={{ width: 300, fontSize: 12.5 }}>
                      {limit}
                    </td>
                    <td style={{ fontSize: 12, color: "var(--ink-2)" }}>
                      {why}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        );
      })}
    </>
  );
}
