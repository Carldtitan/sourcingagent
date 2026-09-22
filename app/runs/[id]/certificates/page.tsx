import Link from "next/link";
import { notFound } from "next/navigation";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

export default async function CertificatesPage({
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

  const [{ data: spec }, { data: runSuppliers }] = await Promise.all([
    supabase
      .from("specifications")
      .select("*")
      .eq("ingredient_id", run.ingredient_id)
      .single(),
    supabase.from("run_suppliers").select("id, suppliers(name, country)").eq("run_id", id),
  ]);

  const ids = (runSuppliers ?? []).map((r) => r.id);
  const { data: coas } = ids.length
    ? await supabase
        .from("coas")
        .select("*")
        .in("run_supplier_id", ids)
        .order("created_at")
    : { data: [] };

  const nameFor = new Map(
    (runSuppliers ?? []).map((r) => [
      r.id,
      r.suppliers as unknown as { name: string; country: string },
    ])
  );

  const ingredient = run.ingredients as Record<string, any>;
  const failing = (coas ?? []).filter((c) => c.verdict === "fail").length;

  return (
    <>
      <div className="headblock">
        <div className="headblock-title">
          <h1>Certificates of Analysis</h1>
          <p>
            Every measured value against its limit, with the margin left. A
            value using most of its limit is passing and still worth seeing,
            because it says the next batch might not.
          </p>
          <p style={{ marginTop: 6 }}>
            <Link href={`/runs/${id}`}>Back to the run</Link>
          </p>
        </div>
        <div className="readout">
          <div>
            <span className="label">Material</span>
            <span className="v">{ingredient.name}</span>
          </div>
          <div>
            <span className="label">Received</span>
            <span className="v">{coas?.length ?? 0}</span>
          </div>
          <div>
            <span className="label">Outside specification</span>
            <span className={`v ${failing ? "hot" : ""}`}>{failing}</span>
          </div>
        </div>
      </div>

      <section className="section">
        <div className="section-head">
          <h2>The target specification</h2>
          <span className="rule-note">what every batch is judged against</span>
        </div>
        <table className="ledger">
          <tbody>
            <tr>
              <td style={{ width: 230 }}>Assay</td>
              <td className="num">
                at least {spec?.assay_min_pct}% · {spec?.assay_basis}
              </td>
            </tr>
            <tr>
              <td>Heavy metals</td>
              <td className="num">
                lead {spec?.lead_max_ppm}, arsenic {spec?.arsenic_max_ppm},
                cadmium {spec?.cadmium_max_ppm}, mercury {spec?.mercury_max_ppm}{" "}
                ppm maximum
              </td>
            </tr>
            <tr>
              <td>Microbiology</td>
              <td className="num">
                total plate count {Number(spec?.tpc_max_cfu_g).toLocaleString()},
                yeast and mould{" "}
                {Number(spec?.yeast_mould_max_cfu_g).toLocaleString()} cfu/g
                maximum
              </td>
            </tr>
            <tr>
              <td>Pathogens</td>
              <td className="num">
                {spec?.ecoli_required}, {spec?.salmonella_required}
              </td>
            </tr>
            <tr>
              <td>Certification</td>
              <td className="num">{spec?.required_certs?.join(", ")}</td>
            </tr>
          </tbody>
        </table>
        <div className="notice assumption" style={{ marginTop: 18 }}>
          <strong>These limits are our assumption.</strong> {spec?.source_note}
        </div>
      </section>

      {(coas ?? []).map((coa) => {
        const supplier = nameFor.get(coa.run_supplier_id);
        const findings = (coa.findings ?? []) as any[];
        return (
          <section className="section" key={coa.id} id={coa.run_supplier_id}>
            <div className="section-head">
              <h2>{supplier?.name ?? "Supplier"}</h2>
              <span className="rule-note">
                batch {coa.batch_no}
                {coa.issued_on ? ` · analysed ${coa.issued_on}` : ""}
              </span>
            </div>

            <div className="row" style={{ padding: "16px 0 6px" }}>
              <span
                className={`verdict ${coa.verdict === "pass" ? "pass" : "fail"}`}
              >
                {coa.verdict === "pass"
                  ? "every line within specification"
                  : "outside specification"}
              </span>
              {coa.file_id && (
                <a className="btn" href={`/api/file/${coa.file_id}`}>
                  Open the PDF
                </a>
              )}
            </div>

            <table className="ledger">
              <thead>
                <tr>
                  <th>Test</th>
                  <th className="r">Measured</th>
                  <th>Limit</th>
                  <th style={{ width: 200 }}>Load against the limit</th>
                  <th>Margin</th>
                </tr>
              </thead>
              <tbody>
                {findings.map((finding) => {
                  const load = Number(finding.load ?? 0);
                  return (
                    <tr
                      key={finding.line}
                      className={finding.verdict === "fail" ? "" : undefined}
                    >
                      <td>{finding.line}</td>
                      <td
                        className="r num"
                        style={{
                          fontWeight: 500,
                          color:
                            finding.verdict === "fail"
                              ? "var(--breach)"
                              : undefined,
                        }}
                      >
                        {finding.measured}
                      </td>
                      <td className="num" style={{ color: "var(--ink-3)" }}>
                        {finding.limit}
                      </td>
                      <td>
                        <span className="load">
                          <span className="load-track">
                            <span
                              className={`load-fill ${
                                load > 1 ? "over" : load > 0.8 ? "near" : ""
                              }`}
                              style={{ width: `${Math.min(100, load * 100)}%` }}
                            />
                            <span
                              className="load-limit"
                              style={{ left: "100%" }}
                            />
                          </span>
                        </span>
                      </td>
                      <td style={{ fontSize: 12 }}>
                        <span
                          className={`verdict ${
                            finding.verdict === "fail" ? "fail" : "pass"
                          }`}
                        >
                          {finding.margin}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        );
      })}

      {(coas ?? []).length === 0 && (
        <div className="empty" style={{ marginTop: 28 }}>
          No certificates have arrived yet. Suppliers attach one to their first
          quotation.
        </div>
      )}
    </>
  );
}
