"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

/**
 * Keeps a live run moving while someone is watching it.
 *
 * Vercel's free plan allows one scheduled job a day, which is no use to a
 * negotiation that moves in seconds. So the page itself asks the engine to
 * take a step every ten seconds, and a button forces one immediately. When
 * nobody is watching, nothing happens, which is the honest behaviour for a
 * prototype that costs nothing to host.
 */
export function RunPulse({ runId }: { runId: string }) {
  const router = useRouter();
  const [auto, setAuto] = useState(true);
  const [state, setState] = useState<"idle" | "working">("idle");
  const [last, setLast] = useState<string | null>(null);
  const running = useRef(false);

  async function step(manual = false) {
    if (running.current) return;
    running.current = true;
    setState("working");
    try {
      const response = await fetch("/api/engine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "tick", run_id: runId }),
      });
      const body = await response.json();
      const moved =
        (body.replies_triggered ?? 0) +
        (body.inbound_processed ?? 0) +
        (body.followups ?? 0) +
        (body.gates_opened ?? 0);
      setLast(
        moved > 0
          ? `${body.replies_triggered ?? 0} replies, ${body.inbound_processed ?? 0} read, ${body.followups ?? 0} chased`
          : "nothing to do"
      );
      if (moved > 0 || manual) router.refresh();
    } catch {
      setLast("the engine did not answer");
    } finally {
      running.current = false;
      setState("idle");
    }
  }

  useEffect(() => {
    if (!auto) return;
    const timer = setInterval(() => step(), 10_000);
    step();
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auto, runId]);

  return (
    <div
      className="section"
      style={{ paddingTop: 18, paddingBottom: 2 }}
      aria-live="polite"
    >
      <div
        className="row"
        style={{
          border: "1px solid var(--rule)",
          borderTop: "2px solid var(--tension)",
          padding: "12px 16px",
          gap: 18,
        }}
      >
        <span className={`verdict ${state === "working" ? "live" : "pending"}`}>
          {state === "working" ? "checking mail" : "watching"}
        </span>
        <span style={{ fontSize: 12.5, color: "var(--ink-2)" }}>
          This page asks the engine to take a step every ten seconds while it is
          open. Suppliers reply by real email, so give them a moment.
        </span>
        <span className="row" style={{ marginLeft: "auto", gap: 10 }}>
          {last && (
            <span
              className="num"
              style={{ fontSize: 11, color: "var(--ink-3)" }}
            >
              {last}
            </span>
          )}
          <button className="btn" onClick={() => step(true)}>
            Check mail now
          </button>
          <button className="btn" onClick={() => setAuto((value) => !value)}>
            {auto ? "Pause" : "Resume"}
          </button>
        </span>
      </div>
    </div>
  );
}
