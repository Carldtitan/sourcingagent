-- Aonic sourcing engine: schema
-- Every supplier, quote and certificate in this database is simulated.
-- No real supplier is represented and no real price or test result is stored.

drop table if exists events cascade;
drop table if exists approvals cascade;
drop table if exists coas cascade;
drop table if exists quotes cascade;
drop table if exists messages cascade;
drop table if exists run_suppliers cascade;
drop table if exists runs cascade;
drop table if exists supplier_ingredients cascade;
drop table if exists suppliers cascade;
drop table if exists specifications cascade;
drop table if exists ingredients cascade;

-- ---------------------------------------------------------------- ingredients

create table ingredients (
  id            text primary key,
  name          text not null,
  chemical_form text not null,
  cas_number    text,
  dose_mg       numeric not null,
  dose_note     text,
  sort_order    int not null default 0
);

-- Target specification. Limits are our own assumption against standard
-- industry practice, because Aonic's internal specification sheet was
-- never supplied. Recorded in source_note and shown in the interface.
create table specifications (
  ingredient_id          text primary key references ingredients(id) on delete cascade,
  assay_min_pct          numeric not null,
  assay_basis            text not null,
  lead_max_ppm           numeric not null,
  arsenic_max_ppm        numeric not null,
  cadmium_max_ppm        numeric not null,
  mercury_max_ppm        numeric not null,
  tpc_max_cfu_g          numeric not null,
  yeast_mould_max_cfu_g  numeric not null,
  ecoli_required         text not null default 'Absent in 10 g',
  salmonella_required    text not null default 'Absent in 25 g',
  required_certs         text[] not null,
  max_moq_kg             numeric not null,
  max_lead_time_days     int not null,
  accepted_origins       text[] not null,
  source_note            text not null
);

-- ------------------------------------------------------------------ suppliers

create table suppliers (
  id              text primary key,
  name            text not null,
  country         text not null,
  kind            text not null check (kind in ('manufacturer', 'distributor')),
  email_local     text not null,          -- gmail plus-address tag
  certs           text[] not null,
  -- simulation personality, never shown as if it were real supplier data
  stubbornness    numeric not null,       -- 0 to 1, resistance to a counter
  reply_delay_s   int not null,
  reply_style     text not null,          -- terse | formal | chatty
  omits_fields    text[] not null default '{}',
  is_simulated    boolean not null default true
);

create table supplier_ingredients (
  supplier_id        text not null references suppliers(id) on delete cascade,
  ingredient_id      text not null references ingredients(id) on delete cascade,
  list_price         numeric not null,    -- price as the supplier first quotes it
  price_floor        numeric not null,    -- lowest they will ever go
  price_currency     text not null,
  price_unit         text not null,       -- kg | lb
  incoterm           text not null,       -- EXW | FOB | CIF | DDP
  purity_pct         numeric not null,    -- assay they actually ship
  moq_kg             numeric not null,
  lead_time_days     int not null,
  coa_fault          text,                -- null | lead | assay | micro | cadmium
  primary key (supplier_id, ingredient_id)
);

-- ----------------------------------------------------------------------- runs

create table runs (
  id              uuid primary key default gen_random_uuid(),
  ingredient_id   text not null references ingredients(id),
  quantity_kg     numeric not null,
  needed_by_days  int not null,
  status          text not null default 'qualifying',
  -- qualifying | awaiting_shortlist | outreach | negotiating | awaiting_award | closed | cancelled
  guardrails      jsonb not null,
  created_at      timestamptz not null default now(),
  closed_at       timestamptz
);

create table run_suppliers (
  id                 uuid primary key default gen_random_uuid(),
  run_id             uuid not null references runs(id) on delete cascade,
  supplier_id        text not null references suppliers(id),
  qualified          boolean,
  disqualify_reason  text,
  stage              text not null default 'pending',
  -- pending | shortlisted | rejected | rfq_sent | quoted | countered | agreed | walked_away | silent
  round              int not null default 0,
  last_contact_at    timestamptz,
  created_at         timestamptz not null default now(),
  unique (run_id, supplier_id)
);

-- ------------------------------------------------------------------- messages

create table messages (
  id              uuid primary key default gen_random_uuid(),
  run_id          uuid not null references runs(id) on delete cascade,
  run_supplier_id uuid references run_suppliers(id) on delete cascade,
  direction       text not null check (direction in ('outbound', 'inbound')),
  kind            text not null,  -- rfq | quote | followup | counter | revised | close | question | other
  from_addr       text not null,
  to_addr         text not null,
  subject         text not null,
  body            text not null,
  reference       text,           -- the code that matches a reply to its thread
  message_id      text,           -- real mail message id
  raw_headers     jsonb,
  parsed          jsonb,          -- what the parser pulled out of an inbound message
  agent_note      jsonb,          -- what the agent was holding when it wrote an outbound message
  attachment_path text,
  occurred_at     timestamptz not null default now()
);

create index on messages (run_id, occurred_at);

-- --------------------------------------------------------------------- quotes

create table quotes (
  id                  uuid primary key default gen_random_uuid(),
  run_supplier_id     uuid not null references run_suppliers(id) on delete cascade,
  message_id          uuid references messages(id) on delete set null,
  round               int not null,
  price               numeric not null,
  currency            text not null,
  unit                text not null,
  quantity_kg         numeric,
  incoterm            text not null,
  lead_time_days      int,
  payment_terms       text,
  purity_pct          numeric,
  valid_days          int,
  -- normalisation, all recomputed by the normaliser
  usd_per_kg_active   numeric,
  freight_usd_per_kg  numeric,
  duty_usd_per_kg     numeric,
  normalisation_note  jsonb,
  created_at          timestamptz not null default now()
);

-- ----------------------------------------------------- certificates of analysis

create table coas (
  id              uuid primary key default gen_random_uuid(),
  run_supplier_id uuid not null references run_suppliers(id) on delete cascade,
  message_id      uuid references messages(id) on delete set null,
  batch_no        text not null,
  issued_on       date,
  storage_path    text,
  measured        jsonb not null,   -- { assay_pct, lead_ppm, ... } as read from the PDF
  findings        jsonb not null,   -- per line: limit, measured, margin, verdict
  verdict         text not null,    -- pass | fail | not_received
  created_at      timestamptz not null default now()
);

-- ------------------------------------------------------------------ approvals

create table approvals (
  id            uuid primary key default gen_random_uuid(),
  run_id        uuid not null references runs(id) on delete cascade,
  kind          text not null,
  -- gate_shortlist | gate_award | coa_failed | price_ceiling | supplier_question | rounds_exhausted
  subject_id    uuid,             -- run_supplier_id where one applies
  headline      text not null,
  context       jsonb not null,
  options       jsonb not null,   -- the choices offered, in order
  status        text not null default 'open',  -- open | resolved | expired
  decision      text,
  note          text,
  opened_at     timestamptz not null default now(),
  decided_at    timestamptz
);

create index on approvals (run_id, status);

-- --------------------------------------------------------------------- events

create table events (
  id          bigserial primary key,
  run_id      uuid not null references runs(id) on delete cascade,
  actor       text not null,   -- qualifier | negotiator | coa_reader | chaser | normaliser | human | supplier
  summary     text not null,
  detail      jsonb,
  occurred_at timestamptz not null default now()
);

create index on events (run_id, occurred_at desc);
