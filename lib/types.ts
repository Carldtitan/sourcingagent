export type Ingredient = {
  id: string;
  name: string;
  chemical_form: string;
  cas_number: string | null;
  dose_mg: number;
  dose_note: string | null;
  sort_order: number;
};

export type Specification = {
  ingredient_id: string;
  assay_min_pct: number;
  assay_basis: string;
  lead_max_ppm: number;
  arsenic_max_ppm: number;
  cadmium_max_ppm: number;
  mercury_max_ppm: number;
  tpc_max_cfu_g: number;
  yeast_mould_max_cfu_g: number;
  ecoli_required: string;
  salmonella_required: string;
  required_certs: string[];
  max_moq_kg: number;
  max_lead_time_days: number;
  accepted_origins: string[];
  source_note: string;
};

export type Supplier = {
  id: string;
  name: string;
  country: string;
  kind: "manufacturer" | "distributor";
  email_local: string;
  certs: string[];
  stubbornness: number;
  reply_delay_s: number;
  reply_style: string;
  omits_fields: string[];
  is_simulated: boolean;
};

export type RunStatus =
  | "qualifying"
  | "awaiting_shortlist"
  | "outreach"
  | "negotiating"
  | "awaiting_award"
  | "closed"
  | "cancelled";

export type Guardrails = {
  ceiling_usd_per_kg_active: number;
  max_rounds: number;
  max_order_value_usd: number;
  max_lead_time_days: number;
  followup_after_seconds: number;
};

export type Run = {
  id: string;
  ingredient_id: string;
  quantity_kg: number;
  needed_by_days: number;
  status: RunStatus;
  guardrails: Guardrails;
  created_at: string;
  closed_at: string | null;
};

export type RunSupplierStage =
  | "pending"
  | "shortlisted"
  | "rejected"
  | "rfq_sent"
  | "quoted"
  | "countered"
  | "agreed"
  | "walked_away"
  | "silent";

export type RunSupplier = {
  id: string;
  run_id: string;
  supplier_id: string;
  qualified: boolean | null;
  disqualify_reason: string | null;
  stage: RunSupplierStage;
  round: number;
  last_contact_at: string | null;
  created_at: string;
};

export type Message = {
  id: string;
  run_id: string;
  run_supplier_id: string | null;
  direction: "outbound" | "inbound";
  kind: string;
  from_addr: string;
  to_addr: string;
  subject: string;
  body: string;
  reference: string | null;
  message_id: string | null;
  raw_headers: Record<string, unknown> | null;
  parsed: Record<string, unknown> | null;
  agent_note: Record<string, unknown> | null;
  attachment_path: string | null;
  occurred_at: string;
};

export type Quote = {
  id: string;
  run_supplier_id: string;
  message_id: string | null;
  round: number;
  price: number;
  currency: string;
  unit: string;
  quantity_kg: number | null;
  incoterm: string;
  lead_time_days: number | null;
  payment_terms: string | null;
  purity_pct: number | null;
  valid_days: number | null;
  usd_per_kg_active: number | null;
  freight_usd_per_kg: number | null;
  duty_usd_per_kg: number | null;
  normalisation_note: NormalisationNote | null;
  created_at: string;
};

export type NormalisationNote = {
  steps: { label: string; value: string; note?: string }[];
};

export type CoaFinding = {
  line: string;
  limit: string;
  measured: string;
  margin: string;
  /** 0 to 1 and beyond, where 1 sits exactly on the limit */
  load: number;
  verdict: "pass" | "fail";
};

export type Coa = {
  id: string;
  run_supplier_id: string;
  message_id: string | null;
  batch_no: string;
  issued_on: string | null;
  storage_path: string | null;
  measured: Record<string, number>;
  findings: CoaFinding[];
  verdict: "pass" | "fail" | "not_received";
  created_at: string;
};

export type ApprovalKind =
  | "gate_shortlist"
  | "gate_award"
  | "coa_failed"
  | "price_ceiling"
  | "supplier_question"
  | "rounds_exhausted";

export type ApprovalOption = {
  id: string;
  label: string;
  consequence: string;
  tone?: "primary" | "danger" | "plain";
};

export type Approval = {
  id: string;
  run_id: string;
  kind: ApprovalKind;
  subject_id: string | null;
  headline: string;
  context: Record<string, unknown>;
  options: ApprovalOption[];
  status: "open" | "resolved" | "expired";
  decision: string | null;
  note: string | null;
  opened_at: string;
  decided_at: string | null;
};

export type RunEvent = {
  id: number;
  run_id: string;
  actor: string;
  summary: string;
  detail: Record<string, unknown> | null;
  occurred_at: string;
};
