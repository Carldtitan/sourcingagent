import Link from "next/link";
import { notFound } from "next/navigation";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

const KIND_WORD: Record<string, string> = {
  rfq: "Request for Quotation",
  quote: "Quotation",
  followup: "Follow-up",
  counter: "Counter-offer",
  revised: "Revised quotation",
  close: "Closing email",
  decline: "Decline note",
  retest: "Retest request",
  question: "Question",
};

export default async function ThreadPage({
  params,
}: {
  params: Promise<{ id: string; rsId: string }>;
}) {
  const { id, rsId } = await params;
  const supabase = db();

  const { data: runSupplier } = await supabase
    .from("run_suppliers")
    .select("*, suppliers(*), runs(*, ingredients(*))")
    .eq("id", rsId)
    .single();

  if (!runSupplier) notFound();

  const [{ data: messages }, { data: quotes }] = await Promise.all([
    supabase
      .from("messages")
      .select("*")
      .eq("run_supplier_id", rsId)
      .order("occurred_at"),
    supabase.from("quotes").select("*").eq("run_supplier_id", rsId).order("round"),
  ]);

  const supplier = runSupplier.suppliers as Record<string, any>;
  const run = runSupplier.runs as Record<string, any>;
  const ingredient = run.ingredients as Record<string, any>;
  const quoteByMessage = new Map(
    (quotes ?? []).map((q) => [q.message_id, q])
  );

  return (
    <>
      <div className="headblock">
        <div className="headblock-title">
          <h1>{supplier.name}</h1>
          <p>
            {ingredient.name} · {supplier.country} · {supplier.kind} ·{" "}
            {supplier.certs.join(", ")}
          </p>
          <p style={{ marginTop: 6 }}>
            <Link href={`/runs/${id}`}>Back to the run</Link>
          </p>
        </div>
        <div className="readout">
          <div>
            <span className="label">Stage</span>
            <span className="v">{runSupplier.stage.replace(/_/g, " ")}</span>
          </div>
          <div>
            <span className="label">Rounds</span>
            <span className="v">{runSupplier.round}</span>
          </div>
          <div>
            <span className="label">Messages</span>
            <span className="v">{messages?.length ?? 0}</span>
          </div>
        </div>
      </div>

      <section className="section">
        <div className="section-head">
          <h2>The conversation</h2>
          <span className="rule-note">
            every message as it was actually sent and received
          </span>
        </div>

        <div className="stack" style={{ paddingTop: 22 }}>
          {(messages ?? []).map((message) => {
            const outbound = message.direction === "outbound";
            const quote = quoteByMessage.get(message.id);
            return (
              <article
                key={message.id}
                className={`node ${outbound ? "" : "is-live"}`}
                style={{
                  marginLeft: outbound ? 0 : 56,
                  marginRight: outbound ? 56 : 0,
                }}
              >
                <div className="node-head">
                  <h3 style={{ fontSize: 14 }}>{message.subject}</h3>
                  <span
                    className="num"
                    style={{
                      marginLeft: "auto",
                      fontSize: 10.5,
                      color: "var(--ink-3)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {new Date(message.occurred_at).toLocaleString("en-GB")}
                  </span>
                </div>

                <div
                  style={{
                    fontSize: 11.5,
                    color: "var(--ink-3)",
                    fontFamily: "var(--mono)",
                    marginBottom: 12,
                    wordBreak: "break-all",
                  }}
                >
                  <span
                    style={{
                      color: outbound ? "var(--ink)" : "var(--tension)",
                      fontWeight: 500,
                    }}
                  >
                    {outbound ? "We sent" : "They sent"} a{" "}
                    {(KIND_WORD[message.kind] ?? message.kind).toLowerCase()}
                  </span>{" "}
                  · from {message.from_addr} · to {message.to_addr}
                  {message.message_id ? ` · ${message.message_id}` : ""}
                </div>

                {message.agent_note?.reasoning && (
                  <div className="notice" style={{ marginBottom: 12 }}>
                    <strong>Why the agent sent this.</strong>{" "}
                    {message.agent_note.reasoning}
                    {Array.isArray(message.agent_note.guardrails_applied) &&
                      message.agent_note.guardrails_applied.length > 0 && (
                        <>
                          {" "}
                          <em>
                            Guardrails applied:{" "}
                            {message.agent_note.guardrails_applied.join("; ")}.
                          </em>
                        </>
                      )}
                  </div>
                )}
                {message.agent_note?.why && !message.agent_note?.reasoning && (
                  <div className="notice" style={{ marginBottom: 12 }}>
                    <strong>Why the agent sent this.</strong>{" "}
                    {message.agent_note.why}
                  </div>
                )}

                <pre
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 11.5,
                    lineHeight: 1.6,
                    whiteSpace: "pre-wrap",
                    margin: 0,
                    color: "var(--ink-2)",
                    maxHeight: 420,
                    overflowY: "auto",
                  }}
                >
                  {message.body}
                </pre>

                {message.attachment_file_id && (
                  <p style={{ marginTop: 12, marginBottom: 0, fontSize: 13 }}>
                    <a href={`/api/file/${message.attachment_file_id}`}>
                      {message.attachment_path}
                    </a>{" "}
                    <span style={{ color: "var(--ink-3)" }}>
                      — the certificate that came with this message
                    </span>
                  </p>
                )}

                {message.parsed && (
                  <div style={{ marginTop: 14 }}>
                    <span className="label" style={{ paddingBottom: 6 }}>
                      What the parser pulled out of it
                    </span>
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(auto-fill, minmax(170px, 1fr))",
                        gap: "2px 20px",
                      }}
                    >
                      {Object.entries(message.parsed)
                        .filter(
                          ([, value]) =>
                            value !== null &&
                            value !== undefined &&
                            !(Array.isArray(value) && value.length === 0) &&
                            value !== false
                        )
                        .map(([key, value]) => (
                          <div className="spread" key={key}>
                            <span className="k">{key.replace(/_/g, " ")}</span>
                            <span className="v">
                              {Array.isArray(value)
                                ? value.join(", ")
                                : String(value)}
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {quote?.normalisation_note?.steps && (
                  <div style={{ marginTop: 14 }}>
                    <span className="label" style={{ paddingBottom: 6 }}>
                      How that price became comparable
                    </span>
                    <table className="ledger">
                      <tbody>
                        {quote.normalisation_note.steps.map(
                          (step: any, index: number) => (
                            <tr key={index}>
                              <td style={{ width: 200 }}>{step.label}</td>
                              <td className="num" style={{ width: 200 }}>
                                {step.value}
                              </td>
                              <td
                                style={{ fontSize: 12, color: "var(--ink-3)" }}
                              >
                                {step.note ?? ""}
                              </td>
                            </tr>
                          )
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      </section>
    </>
  );
}
