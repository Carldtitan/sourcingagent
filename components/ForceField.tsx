/**
 * The structure under load.
 *
 * Every offer is a strut. The vertical rule is the ceiling, which is the most
 * the finished product can carry for this ingredient. A strut sitting left of
 * the rule is inside the ceiling. A strut crossing it is over.
 *
 * The red cord running down the column is the tension the negotiation is
 * holding: it thickens where a supplier has been countered and gone slack
 * where one has stopped moving.
 */

type Offer = {
  id: string;
  supplier: string;
  country: string;
  delivered: number;
  rounds: number;
  stage: string;
  coa: "pass" | "fail" | "not_received";
};

const ROW = 46;
const PAD_TOP = 34;
const PAD_BOTTOM = 26;
const LEFT = 150;
const RIGHT = 150;

export function ForceField({
  offers,
  ceiling,
  width = 880,
}: {
  offers: Offer[];
  ceiling: number;
  width?: number;
}) {
  if (offers.length === 0) return null;

  const height = PAD_TOP + offers.length * ROW + PAD_BOTTOM;
  const plotWidth = width - LEFT - RIGHT;

  const prices = offers.map((o) => o.delivered);
  const low = Math.min(...prices, ceiling);
  const high = Math.max(...prices, ceiling);
  const span = Math.max(high - low, high * 0.08);
  const min = low - span * 0.18;
  const max = high + span * 0.18;

  const x = (value: number) =>
    LEFT + ((value - min) / (max - min)) * plotWidth;

  const ceilingX = x(ceiling);

  return (
    <figure
      style={{ margin: "0 0 4px", overflowX: "auto" }}
      aria-label="Offers drawn as struts against the price ceiling"
    >
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        style={{ minWidth: 640, display: "block" }}
        role="img"
      >
        <title>
          {offers.length} offers against a ceiling of ${ceiling.toFixed(2)} per
          kilogram of active material
        </title>

        {/* the ceiling: the one line nothing may cross */}
        <line
          x1={ceilingX}
          y1={14}
          x2={ceilingX}
          y2={height - 12}
          stroke="var(--ink)"
          strokeWidth={1.25}
        />
        <text
          x={ceilingX}
          y={10}
          textAnchor="middle"
          fontSize={9.5}
          letterSpacing="0.12em"
          fill="var(--ink)"
          fontFamily="var(--mono)"
        >
          CEILING ${ceiling.toFixed(2)}
        </text>

        {/* the cord: tension running down the column */}
        <polyline
          points={offers
            .map((o, i) => `${x(o.delivered)},${PAD_TOP + i * ROW + ROW / 2}`)
            .join(" ")}
          fill="none"
          stroke="var(--tension)"
          strokeWidth={1.2}
          strokeOpacity={0.55}
        />

        {offers.map((offer, i) => {
          const cy = PAD_TOP + i * ROW + ROW / 2;
          const px = x(offer.delivered);
          const over = offer.delivered > ceiling;
          const slack = offer.stage === "walked_away" || offer.coa === "fail";

          const strutColour = slack
            ? "var(--slack)"
            : offer.stage === "agreed"
              ? "var(--sand-deep)"
              : "var(--ink)";

          // a strut tilts with how far it sits from the ceiling
          const tilt = Math.max(-9, Math.min(9, ((offer.delivered - ceiling) / span) * 14));
          const half = 26;

          return (
            <g key={offer.id}>
              {/* leader line back to the name */}
              <line
                x1={LEFT - 12}
                y1={cy}
                x2={px - half - 4}
                y2={cy}
                stroke="var(--rule)"
                strokeWidth={1}
              />
              <text
                x={LEFT - 18}
                y={cy + 1}
                textAnchor="end"
                fontSize={11.5}
                fill="var(--ink)"
                fontFamily="var(--display)"
              >
                {offer.supplier}
              </text>
              <text
                x={LEFT - 18}
                y={cy + 13}
                textAnchor="end"
                fontSize={9}
                letterSpacing="0.1em"
                fill="var(--ink-3)"
                fontFamily="var(--mono)"
              >
                {offer.country.toUpperCase()}
              </text>

              {/* the strut */}
              <line
                x1={px - half}
                y1={cy + tilt}
                x2={px + half}
                y2={cy - tilt}
                stroke={strutColour}
                strokeWidth={6}
                strokeLinecap="round"
              />
              {/* the node */}
              <circle
                cx={px}
                cy={cy}
                r={3.4}
                fill={over ? "var(--breach)" : "var(--paper)"}
                stroke={over ? "var(--breach)" : "var(--ink)"}
                strokeWidth={1.4}
              />

              {/* the cord pulling it toward the ceiling */}
              {offer.rounds > 0 && (
                <line
                  x1={px}
                  y1={cy}
                  x2={ceilingX}
                  y2={cy}
                  stroke="var(--tension)"
                  strokeWidth={Math.min(3, 0.9 + offer.rounds * 0.7)}
                  strokeDasharray="3 3"
                />
              )}

              {/* the reading */}
              <line
                x1={px + half + 4}
                y1={cy}
                x2={width - RIGHT + 8}
                y2={cy}
                stroke="var(--rule)"
                strokeWidth={1}
              />
              <text
                x={width - RIGHT + 14}
                y={cy + 1}
                fontSize={12}
                fontFamily="var(--mono)"
                fill={over ? "var(--breach)" : "var(--ink)"}
              >
                ${offer.delivered.toFixed(2)}
              </text>
              <text
                x={width - RIGHT + 14}
                y={cy + 13}
                fontSize={9}
                letterSpacing="0.08em"
                fontFamily="var(--mono)"
                fill="var(--ink-3)"
              >
                {over
                  ? `+${(offer.delivered - ceiling).toFixed(2)} OVER`
                  : `${(ceiling - offer.delivered).toFixed(2)} UNDER`}
                {offer.rounds > 0 ? ` · ${offer.rounds} RD` : ""}
              </text>
            </g>
          );
        })}
      </svg>
      <figcaption
        className="label"
        style={{ paddingTop: 6, color: "var(--ink-3)" }}
      >
        Dollars per kilogram of active material, delivered. A dashed cord shows
        a supplier that has been countered.
      </figcaption>
    </figure>
  );
}
