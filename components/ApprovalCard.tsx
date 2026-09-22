"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { engine } from "@/lib/engine";
import { Trace } from "./Trace";

type Option = {
  id: string;
  label: string;
  consequence: string;
  tone?: "primary" | "danger" | "plain";
};

type Approval = {
  id: string;
  kind: string;
  headline: string;
  context: Record<string, any>;
  options: Option[];
  opened_at: string;
};

const WHY: Record<string, string> = {
  gate_shortlist:
    "Nothing leaves the building until a person approves who gets contacted.",
  gate_award:
    "Nothing is agreed until a person approves what the company commits to.",
  coa_failed:
    "A batch outside specification cannot go into a product on an agent's say-so.",
  price_ceiling:
    "The price is above what the finished product can carry, so only a person can raise it.",
  rounds_exhausted:
    "Three rounds ended without agreement. The agent stops rather than keep pushing.",
  supplier_question:
    "The supplier asked something the agent is not allowed to answer.",
};

export function ApprovalCard({ approval }: { approval: Approval }) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(decision: string) {
    setBusy(decision);
    setError(null);
    try {
      await engine({
        action: "decide",
        approval_id: approval.id,
        decision,
      });
      router.refresh();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Something failed.");
      setBusy(null);
    }
  }

  const context = approval.context ?? {};

  return (
    <article className="node is-live">
      <div className="node-head">
        <h3>{approval.headline}</h3>
        <span className="verdict live">waiting</span>
      </div>

      <p style={{ margin: "0 0 14px", fontSize: 13 }}>
        {WHY[approval.kind] ?? "A person has to decide this one."}
      </p>

      {approval.kind === "gate_shortlist" && (
        <ShortlistDetail context={context} />
      )}
      {approval.kind === "coa_failed" && <CertificateDetail context={context} />}
      {(approval.kind === "price_ceiling" ||
        approval.kind === "rounds_exhausted") && (
        <CeilingDetail context={context} />
      )}
      {approval.kind === "gate_award" && <AwardDetail context={context} />}
      {approval.kind === "supplier_question" && (
        <div className="notice" style={{ marginBottom: 16 }}>
          <strong>They wrote:</strong>{" "}
          {String(context.body ?? "").slice(0, 400)}
        </div>
      )}

      <div className="row" style={{ marginTop: 4 }}>
        {approval.options.map((option) => (
          <button
            key={option.id}
            className={`btn ${
              option.tone === "primary"
                ? "btn-primary"
                : option.tone === "danger"
                  ? "btn-danger"
                  : ""
            }`}
            onClick={() => decide(option.id)}
            disabled={busy !== null}
            title={option.consequence}
          >
            {busy === option.id ? "Working" : option.label}
            {option.tone === "primary" && <Trace />}
          </button>
        ))}
      </div>

      <ul
        style={{
          listStyle: "none",
          padding: 0,
          margin: "12px 0 0",
          fontSize: 12,
          color: "var(--ink-3)",
        }}
      >
        {approval.options.map((option) => (
          <li key={option.id}>
            <span className="num" style={{ color: "var(--ink-2)" }}>
              {option.label}
            </span>{" "}
            — {option.consequence}
          </li>
        ))}
      </ul>

      {error && (
        <div className="notice warn" style={{ marginTop: 14 }}>
          <strong>That did not go through.</strong> {error}
        </div>
      )}
    </article>
  );
}

function ShortlistDetail({ context }: { context: Record<string, any> }) {
  const kept: any[] = context.kept ?? [];
  const dropped: any[] = context.dropped ?? [];
  return (
    <div style={{ marginBottom: 16 }}>
      <table className="ledger">
        <tbody>
          {kept.map((row) => (
            <tr key={row.name}>
              <td style={{ width: 28 }}>
                <span className="verdict pass" aria-label="qualified" />
              </td>
              <td style={{ width: 220 }}>
                {row.name}
                <span className="sub">{row.country}</span>
              </td>
              <td style={{ fontSize: 12, color: "var(--ink-2)" }}>
                {row.reason}
              </td>
            </tr>
          ))}
          {dropped.map((row) => (
            <tr key={row.name} className="is-void">
              <td>
                <span className="verdict fail" aria-label="dropped" />
              </td>
              <td>
                {row.name}
                <span className="sub">{row.country}</span>
              </td>
              <td style={{ fontSize: 12 }}>{row.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CertificateDetail({ context }: { context: Record<string, any> }) {
  const findings: any[] = context.findings ?? [];
  return (
    <div style={{ marginBottom: 16 }}>
      <span className="label" style={{ paddingBottom: 8 }}>
        Batch {context.batch_no}
      </span>
      <table className="ledger">
        <tbody>
          {findings
            .filter((f) => f.verdict === "fail")
            .concat(findings.filter((f) => f.verdict !== "fail"))
            .map((finding) => (
              <tr key={finding.line}>
                <td style={{ width: 170 }}>{finding.line}</td>
                <td className="num" style={{ width: 130 }}>
                  {finding.measured}
                </td>
                <td
                  className="num"
                  style={{ width: 150, color: "var(--ink-3)" }}
                >
                  {finding.limit}
                </td>
                <td>
                  <span
                    className={`verdict ${
                      finding.verdict === "fail" ? "fail" : "pass"
                    }`}
                  >
                    {finding.margin}
                  </span>
                </td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}

function CeilingDetail({ context }: { context: Record<string, any> }) {
  const delivered = Number(context.delivered ?? 0);
  const ceiling = Number(context.ceiling ?? 0);
  const over = delivered - ceiling;
  return (
    <div style={{ marginBottom: 16 }}>
      <div className="row" style={{ gap: 34, marginBottom: 12 }}>
        <div>
          <span className="label">Their best</span>
          <span className="num" style={{ fontSize: 17 }}>
            ${delivered.toFixed(2)}
          </span>
        </div>
        <div>
          <span className="label">Ceiling</span>
          <span className="num" style={{ fontSize: 17 }}>
            ${ceiling.toFixed(2)}
          </span>
        </div>
        <div>
          <span className="label">Gap</span>
          <span
            className="num"
            style={{ fontSize: 17, color: "var(--breach)" }}
          >
            +${over.toFixed(2)}
          </span>
        </div>
        <div>
          <span className="label">Rounds used</span>
          <span className="num" style={{ fontSize: 17 }}>
            {context.round ?? 0}
          </span>
        </div>
      </div>
      {context.reasoning && (
        <p style={{ fontSize: 13, margin: 0 }}>{context.reasoning}</p>
      )}
      {Array.isArray(context.guardrails_applied) &&
        context.guardrails_applied.length > 0 && (
          <div className="notice" style={{ marginTop: 12 }}>
            <strong>The guardrails stopped the agent here:</strong>{" "}
            {context.guardrails_applied.join("; ")}.
          </div>
        )}
    </div>
  );
}

function AwardDetail({ context }: { context: Record<string, any> }) {
  const table: any[] = context.table ?? [];
  return (
    <div style={{ marginBottom: 16 }}>
      <table className="ledger">
        <thead>
          <tr>
            <th>Supplier</th>
            <th className="r">$/kg active</th>
            <th className="r">Lead</th>
            <th>Certificate</th>
            <th className="r">Score</th>
          </tr>
        </thead>
        <tbody>
          {table.slice(0, 5).map((row, index) => (
            <tr key={row.run_supplier_id} className={index === 0 ? "is-lead" : ""}>
              <td>
                {row.supplier}
                <span className="sub">{row.country}</span>
              </td>
              <td className="r num">{Number(row.delivered).toFixed(2)}</td>
              <td className="r num">
                {row.lead_time_days ? `${row.lead_time_days}d` : "—"}
              </td>
              <td>
                <span
                  className={`verdict ${
                    row.coa_verdict === "pass"
                      ? "pass"
                      : row.coa_verdict === "fail"
                        ? "fail"
                        : "pending"
                  }`}
                >
                  {row.coa_verdict === "not_received" ? "none" : row.coa_verdict}
                </span>
              </td>
              <td className="r num">{Number(row.score?.total ?? 0).toFixed(0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
