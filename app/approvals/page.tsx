import Link from "next/link";
import { db } from "@/lib/db";
import { ApprovalCard } from "@/components/ApprovalCard";

export const dynamic = "force-dynamic";

export default async function ApprovalsPage() {
  const supabase = db();

  const [{ data: open }, { data: resolved }] = await Promise.all([
    supabase
      .from("approvals")
      .select("*, runs(ingredient_id, ingredients(name))")
      .eq("status", "open")
      .order("opened_at"),
    supabase
      .from("approvals")
      .select("*, runs(ingredient_id, ingredients(name))")
      .eq("status", "resolved")
      .order("decided_at", { ascending: false })
      .limit(30),
  ]);

  return (
    <>
      <div className="headblock">
        <div className="headblock-title">
          <h1>Approvals</h1>
          <p>
            Two gates stop the engine on its own: nothing is sent until the
            shortlist is approved, and nothing is agreed until the award is
            approved. Four escalations interrupt it: a failed certificate, a
            price above what the product can carry, a question the agent cannot
            answer, and a negotiation that has used its rounds.
          </p>
        </div>
        <div className="readout">
          <div>
            <span className="label">Waiting</span>
            <span className={`v ${open?.length ? "hot" : ""}`}>
              {open?.length ?? 0}
            </span>
          </div>
          <div>
            <span className="label">Decided</span>
            <span className="v">{resolved?.length ?? 0}</span>
          </div>
        </div>
      </div>

      <section className="section">
        <div className="section-head">
          <h2>Waiting on you</h2>
          <span className="rule-note">nothing moves until you decide</span>
        </div>
        {(open ?? []).length === 0 ? (
          <p style={{ paddingTop: 20, color: "var(--ink-2)" }}>
            Nothing is waiting. The engine is either working or finished.
          </p>
        ) : (
          <div className="stack" style={{ paddingTop: 18 }}>
            {(open ?? []).map((approval) => (
              <div key={approval.id}>
                <ApprovalCard approval={approval as any} />
                <p style={{ fontSize: 12.5, margin: "8px 0 0" }}>
                  Part of the{" "}
                  <Link href={`/runs/${approval.run_id}`}>
                    {(approval.runs as any)?.ingredients?.name ?? "sourcing"} run
                  </Link>
                  .
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Already decided</h2>
          <span className="rule-note">the record of who chose what</span>
        </div>
        <table className="ledger">
          <tbody>
            {(resolved ?? []).map((approval) => (
              <tr key={approval.id}>
                <td className="num" style={{ width: 110, color: "var(--ink-3)" }}>
                  {approval.decided_at
                    ? new Date(approval.decided_at).toLocaleString("en-GB", {
                        day: "2-digit",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : ""}
                </td>
                <td style={{ width: 130 }}>
                  <span className="label" style={{ color: "var(--ink-2)" }}>
                    {approval.kind.replace(/_/g, " ")}
                  </span>
                </td>
                <td>
                  <Link href={`/runs/${approval.run_id}`}>
                    {approval.headline}
                  </Link>
                </td>
                <td style={{ width: 110 }}>
                  <span className="verdict agreed">{approval.decision}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(resolved ?? []).length === 0 && (
          <p style={{ paddingTop: 20, color: "var(--ink-2)" }}>
            No decisions yet.
          </p>
        )}
      </section>
    </>
  );
}
