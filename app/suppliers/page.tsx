import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

export default async function SuppliersPage() {
  const supabase = db();
  const [{ data: suppliers }, { data: prices }, { data: ingredients }] =
    await Promise.all([
      supabase.from("suppliers").select("*").order("name"),
      supabase.from("supplier_ingredients").select("*"),
      supabase.from("ingredients").select("*").order("sort_order"),
    ]);

  const byIngredient = new Map<string, string>(
    (ingredients ?? []).map((i) => [i.id, i.name])
  );

  return (
    <>
      <div className="headblock">
        <div className="headblock-title">
          <h1>Suppliers</h1>
          <p>
            Twelve companies that do not exist, each on its own email address.
            Each carries a secret price floor, a house style and a habit of
            leaving something out of a quotation, so the parser has to work on
            prose written by someone else.
          </p>
        </div>
        <div className="readout">
          <div>
            <span className="label">Companies</span>
            <span className="v">{suppliers?.length ?? 0}</span>
          </div>
          <div>
            <span className="label">Price rows</span>
            <span className="v">{prices?.length ?? 0}</span>
          </div>
        </div>
      </div>

      <div className="section">
        <div className="notice warn">
          <strong>Every supplier on this page is simulated.</strong> The names,
          prices, certificates and behaviour are invented for this prototype. No
          real supplier is represented and none is ever contacted.
        </div>
      </div>

      <section className="section">
        <div className="section-head">
          <h2>The twelve</h2>
          <span className="rule-note">
            what the qualifier sees before anything is sent
          </span>
        </div>
        <table className="ledger">
          <thead>
            <tr>
              <th>Supplier</th>
              <th>Origin</th>
              <th>Type</th>
              <th>Certification</th>
              <th>Email address</th>
              <th>Reply style</th>
              <th className="r">Holds out</th>
            </tr>
          </thead>
          <tbody>
            {(suppliers ?? []).map((supplier) => (
              <tr key={supplier.id}>
                <td>{supplier.name}</td>
                <td>{supplier.country}</td>
                <td style={{ color: "var(--ink-2)" }}>{supplier.kind}</td>
                <td style={{ fontSize: 12 }}>{supplier.certs.join(", ")}</td>
                <td className="num" style={{ fontSize: 11 }}>
                  +{supplier.email_local}
                </td>
                <td style={{ color: "var(--ink-2)" }}>
                  {supplier.reply_style}
                  {supplier.omits_fields?.length > 0 && (
                    <span className="sub">
                      omits {supplier.omits_fields.join(", ").replace(/_/g, " ")}
                    </span>
                  )}
                </td>
                <td className="r">
                  <span className="load">
                    <span className="load-track">
                      <span
                        className="load-fill"
                        style={{
                          width: `${Number(supplier.stubbornness) * 100}%`,
                        }}
                      />
                    </span>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {(ingredients ?? []).map((ingredient) => (
        <section className="section" key={ingredient.id}>
          <div className="section-head">
            <h2>{ingredient.name}</h2>
            <span className="rule-note">
              {
                (prices ?? []).filter((p) => p.ingredient_id === ingredient.id)
                  .length
              }{" "}
              suppliers carry it
            </span>
          </div>
          <table className="ledger">
            <thead>
              <tr>
                <th>Supplier</th>
                <th className="r">Opens at</th>
                <th className="r">Will not go below</th>
                <th className="r">Assay</th>
                <th className="r">MOQ</th>
                <th className="r">Lead</th>
                <th>Certificate fault planted</th>
              </tr>
            </thead>
            <tbody>
              {(prices ?? [])
                .filter((p) => p.ingredient_id === ingredient.id)
                .sort((a, b) => Number(a.price_floor) - Number(b.price_floor))
                .map((price) => (
                  <tr key={`${price.supplier_id}-${price.ingredient_id}`}>
                    <td>
                      {(suppliers ?? []).find((s) => s.id === price.supplier_id)
                        ?.name ?? price.supplier_id}
                    </td>
                    <td className="r num">
                      {price.price_currency} {Number(price.list_price).toFixed(2)}
                      /{price.price_unit} {price.incoterm}
                    </td>
                    <td className="r num" style={{ color: "var(--tension)" }}>
                      {price.price_currency}{" "}
                      {Number(price.price_floor).toFixed(2)}
                    </td>
                    <td className="r num">
                      {Number(price.purity_pct).toFixed(1)}%
                    </td>
                    <td className="r num">
                      {Number(price.moq_kg).toLocaleString()} kg
                    </td>
                    <td className="r num">{price.lead_time_days}d</td>
                    <td>
                      {price.coa_fault ? (
                        <span className="verdict fail">{price.coa_fault}</span>
                      ) : (
                        <span className="verdict pass">clean</span>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </section>
      ))}
    </>
  );
}
