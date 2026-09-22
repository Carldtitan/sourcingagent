import Link from "next/link";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

export default async function MailPage() {
  const supabase = db();
  const { data: messages } = await supabase
    .from("messages")
    .select("*, run_suppliers(id, run_id, suppliers(name))")
    .order("occurred_at", { ascending: false })
    .limit(120);

  const inbound = (messages ?? []).filter((m) => m.direction === "inbound");

  return (
    <>
      <div className="headblock">
        <div className="headblock-title">
          <h1>Mail log</h1>
          <p>
            Every message this system has sent or received, newest first. These
            are real emails with real headers and real message identifiers. The
            addresses are plus tags on one Gmail account, so both sides of every
            conversation land in a mailbox we own and nothing reaches a company
            outside it.
          </p>
        </div>
        <div className="readout">
          <div>
            <span className="label">Messages</span>
            <span className="v">{messages?.length ?? 0}</span>
          </div>
          <div>
            <span className="label">Received</span>
            <span className="v">{inbound.length}</span>
          </div>
          <div>
            <span className="label">With a certificate</span>
            <span className="v">
              {inbound.filter((m) => m.attachment_file_id).length}
            </span>
          </div>
        </div>
      </div>

      <section className="section">
        <div className="section-head">
          <h2>The wire</h2>
          <span className="rule-note">
            proof that the mail moved, not a simulation of it
          </span>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="ledger" style={{ minWidth: 940 }}>
            <thead>
              <tr>
                <th>Time</th>
                <th>Direction</th>
                <th>Kind</th>
                <th>From</th>
                <th>To</th>
                <th>Subject</th>
                <th>Reference</th>
                <th>Attachment</th>
              </tr>
            </thead>
            <tbody>
              {(messages ?? []).map((message) => {
                const rs = message.run_suppliers as any;
                return (
                  <tr key={message.id}>
                    <td className="num" style={{ color: "var(--ink-3)", width: 92 }}>
                      {new Date(message.occurred_at).toLocaleTimeString("en-GB")}
                    </td>
                    <td>
                      <span
                        className={`verdict ${
                          message.direction === "inbound" ? "live" : "pass"
                        }`}
                      >
                        {message.direction === "inbound" ? "in" : "out"}
                      </span>
                    </td>
                    <td style={{ color: "var(--ink-2)" }}>{message.kind}</td>
                    <td className="num" style={{ fontSize: 11 }}>
                      {message.from_addr}
                    </td>
                    <td className="num" style={{ fontSize: 11 }}>
                      {message.to_addr}
                    </td>
                    <td style={{ fontSize: 12.5, maxWidth: 320 }}>
                      {rs?.run_id ? (
                        <Link href={`/runs/${rs.run_id}/threads/${rs.id}`}>
                          {message.subject}
                        </Link>
                      ) : (
                        message.subject
                      )}
                      {message.message_id && (
                        <span className="sub num" style={{ fontSize: 10 }}>
                          {message.message_id}
                        </span>
                      )}
                    </td>
                    <td className="num" style={{ fontSize: 11 }}>
                      {message.reference}
                    </td>
                    <td>
                      {message.attachment_file_id ? (
                        <a href={`/api/file/${message.attachment_file_id}`}>
                          {message.attachment_path}
                        </a>
                      ) : (
                        <span style={{ color: "var(--ink-3)" }}>—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {(messages ?? []).length === 0 && (
          <p style={{ paddingTop: 20, color: "var(--ink-2)" }}>
            No mail yet. Start a brief and approve the shortlist.
          </p>
        )}
      </section>
    </>
  );
}
