import Link from "next/link";

type Step = {
  name: string;
  does: string;
  how: string;
  human?: { gate: string; why: string };
  model?: boolean;
};

const STEPS: Step[] = [
  {
    name: "Brief and ceiling",
    does: "Ingredient, quantity and deadline in. A price ceiling out.",
    how: "The ceiling is the ingredient's share of the $12.60 of ingredient cost in a 30-serving pouch, divided by its mass in the pouch. The negotiator refuses a price because the pouch cannot carry it.",
  },
  {
    name: "Discovery",
    does: "Every supplier that carries the ingredient.",
    how: "Twelve simulated companies here. In production, supplier directories, trade databases and past purchase orders.",
  },
  {
    name: "Qualification",
    does: "Drops suppliers on certification, minimum order, lead time and origin.",
    how: "Fixed rules, not a model, because these are facts a buyer must be able to audit. Every cut carries its reason.",
  },
  {
    name: "Shortlist",
    does: "Waits for a person.",
    how: "Nothing is sent until the buyer approves who gets contacted.",
    human: {
      gate: "Gate 1",
      why: "Contacting a supplier cannot be undone, and a buyer knows things the system does not.",
    },
  },
  {
    name: "Outreach",
    does: "A real Request for Quotation to every shortlisted supplier.",
    how: "Sent over Gmail. A reference code in the subject routes every reply back to its negotiation.",
  },
  {
    name: "Reply parser",
    does: "Reads prose quotations.",
    how: "Pulls out price, currency, unit, delivery term, lead time, payment terms and assay, and lists what is missing.",
    model: true,
  },
  {
    name: "Certificate reader and judge",
    does: "Reads the attached PDF and judges every line.",
    how: "A model reads the values off the page. Fixed arithmetic judges them against the specification, because a laboratory limit is not a matter of opinion.",
    model: true,
    human: {
      gate: "Escalation",
      why: "A batch outside specification cannot go into a product on an agent's judgement.",
    },
  },
  {
    name: "Normaliser",
    does: "One comparable price.",
    how: "Dollars per kilogram of active material, delivered. Corrects for currency, pounds, freight and duty by Incoterm, and assay.",
  },
  {
    name: "Negotiator",
    does: "Accept, counter, walk or escalate.",
    how: "The model proposes a move and writes the reasoning. The guardrails overrule it: never above the ceiling, never a failed certificate, never past three rounds, never past the order value or the deadline.",
    model: true,
    human: {
      gate: "Escalation",
      why: "A price above the ceiling, a question the agent may not answer, or three rounds without agreement.",
    },
  },
  {
    name: "Chaser",
    does: "One follow-up to a silent supplier.",
    how: "Silence after that closes the file.",
  },
  {
    name: "Ranking",
    does: "Three to five offers, ranked.",
    how: "Normalised price 50%, lead time 20%, certificate 20%, certification 10%. Walked-away offers stay visible as real market prices.",
  },
  {
    name: "Award",
    does: "Waits for a person.",
    how: "The close email goes only after the buyer approves. Every other supplier is declined politely.",
    human: {
      gate: "Gate 2",
      why: "This is the commitment of company money.",
    },
  },
];

export default function HowPage() {
  return (
    <>
      <div className="headblock">
        <div className="headblock-title">
          <h1>How it works</h1>
          <p>
            One brief in, three to five validated and comparable offers out.
            Twelve steps, two gates where nothing moves without a person, and
            three places the engine stops itself and asks.
          </p>
        </div>
        <div className="readout">
          <div>
            <span className="label">Gates</span>
            <span className="v hot">2</span>
          </div>
          <div>
            <span className="label">Escalations</span>
            <span className="v hot">4</span>
          </div>
          <div>
            <span className="label">Model calls a reply</span>
            <span className="v">3</span>
          </div>
        </div>
      </div>

      <section className="section">
        <div className="section-head">
          <h2>The flow</h2>
          <span className="rule-note">red marks where a person decides</span>
        </div>

        <ol
          style={{
            listStyle: "none",
            margin: 0,
            padding: "22px 0 0",
            position: "relative",
          }}
        >
          <span
            aria-hidden="true"
            style={{
              position: "absolute",
              left: 15,
              top: 30,
              bottom: 30,
              width: 1,
              background: "var(--ink)",
            }}
          />
          {STEPS.map((step, index) => (
            <li
              key={step.name}
              style={{
                display: "grid",
                gridTemplateColumns: "32px minmax(0, 1fr) minmax(0, 1.1fr)",
                gap: "0 24px",
                padding: "0 0 22px",
                position: "relative",
              }}
            >
              <span
                aria-hidden="true"
                style={{
                  width: 11,
                  height: 11,
                  marginTop: 5,
                  marginLeft: 10,
                  borderRadius: step.human?.gate.startsWith("Gate") ? 0 : "50%",
                  transform: step.human?.gate.startsWith("Gate")
                    ? "rotate(45deg)"
                    : undefined,
                  background: step.human ? "var(--tension)" : "var(--paper)",
                  border: `1.5px solid ${step.human ? "var(--tension)" : "var(--ink)"}`,
                  position: "relative",
                  zIndex: 1,
                }}
              />
              <div>
                <span className="label" style={{ paddingBottom: 3 }}>
                  {String(index + 1).padStart(2, "0")}
                  {step.model ? " · reads with a model" : ""}
                </span>
                <h3 style={{ fontSize: 15 }}>{step.name}</h3>
                <p style={{ fontSize: 13, margin: "4px 0 0" }}>{step.does}</p>
              </div>
              <div>
                <p style={{ fontSize: 12.5, margin: 0 }}>{step.how}</p>
                {step.human && (
                  <p
                    style={{
                      fontSize: 12.5,
                      margin: "8px 0 0",
                      color: "var(--tension)",
                    }}
                  >
                    <strong
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 10.5,
                        letterSpacing: "0.1em",
                        textTransform: "uppercase",
                        marginRight: 8,
                      }}
                    >
                      {step.human.gate}
                    </strong>
                    {step.human.why}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Why the people sit where they sit</h2>
        </div>
        <div className="stack-tight" style={{ paddingTop: 16, maxWidth: 780 }}>
          <p>
            A person holds every decision that commits the company, and every
            decision where being wrong is expensive and hard to reverse. That
            gives two gates, at the start and the end, and four escalations in
            the middle.
          </p>
          <p>
            Everything else is work a person would do the same way, only slower:
            reading replies, converting prices, checking certificates against a
            written specification and countering inside a set ceiling. Keeping
            people out of those steps is what turns two to three days of
            sourcing into about thirty minutes.
          </p>
          <p>
            In production, each escalation would also reach the buyer on
            Telegram or Slack with the same choices. Here every gate lives in{" "}
            <Link href="/approvals">Approvals</Link>, so anyone reviewing this
            can act on all of them.
          </p>
        </div>
      </section>
    </>
  );
}
