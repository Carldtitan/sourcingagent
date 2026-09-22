"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Trace } from "./Trace";

type Choice = {
  id: string;
  name: string;
  chemical_form: string;
  dose_mg: number;
  budget_note: string | null;
  ceiling: number;
};

export function NewBrief({ ingredients }: { ingredients: Choice[] }) {
  const router = useRouter();
  const [ingredientId, setIngredientId] = useState(ingredients[0]?.id ?? "");
  const [quantity, setQuantity] = useState("500");
  const [neededBy, setNeededBy] = useState("84");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const chosen = ingredients.find((i) => i.id === ingredientId);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/engine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "start",
          ingredient_id: ingredientId,
          quantity_kg: Number(quantity),
          needed_by_days: Number(neededBy),
        }),
      });
      const body = await response.json();
      if (!response.ok || body.error) throw new Error(body.error ?? "failed");
      router.push(`/runs/${body.run_id}`);
    } catch (problem) {
      setError(
        problem instanceof Error
          ? problem.message
          : "The engine did not answer. Check that the Python functions are running."
      );
      setBusy(false);
    }
  }

  return (
    <div style={{ paddingTop: 20 }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(220px, 2fr) repeat(2, minmax(120px, 1fr)) auto",
          gap: 18,
          alignItems: "end",
        }}
      >
        <label className="field">
          <span className="label">Ingredient</span>
          <select
            value={ingredientId}
            onChange={(event) => setIngredientId(event.target.value)}
          >
            {ingredients.map((i) => (
              <option key={i.id} value={i.id}>
                {i.name} — {i.chemical_form}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="label">Quantity, kg</span>
          <input
            type="number"
            min={1}
            value={quantity}
            onChange={(event) => setQuantity(event.target.value)}
          />
        </label>

        <label className="field">
          <span className="label">Needed within, days</span>
          <input
            type="number"
            min={7}
            value={neededBy}
            onChange={(event) => setNeededBy(event.target.value)}
          />
        </label>

        <button
          className="btn btn-primary"
          onClick={start}
          disabled={busy || !ingredientId}
        >
          {busy ? "Qualifying" : "Start sourcing"}
          <Trace />
        </button>
      </div>

      {chosen && (
        <div className="notice assumption" style={{ marginTop: 20 }}>
          <strong>
            Ceiling ${chosen.ceiling.toFixed(2)} per kg of active material.
          </strong>{" "}
          {chosen.budget_note} The engine will not agree a price above this
          without a person raising it, because the pouch cannot carry the cost.
        </div>
      )}

      {error && (
        <div className="notice warn" style={{ marginTop: 16 }}>
          <strong>The brief did not start.</strong> {error}
        </div>
      )}
    </div>
  );
}
