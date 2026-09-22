-- The cost model behind every price ceiling.
--
-- A sourcing engine that negotiates against an invented ceiling is guessing.
-- This table holds the cost of one pouch of Aonic Complete, so each
-- ingredient's ceiling is a share of the ingredient cost the product can
-- actually carry. When the negotiator refuses a price, it refuses because
-- the pouch cannot absorb it.
--
-- Figures come from Carl Okpala's Aonic Complete cost analysis, September
-- 2026. They are a working model, not an Aonic finance document, and the
-- interface says so wherever a ceiling is shown.

create table if not exists cost_model (
  id                  text primary key,
  product             text not null,
  servings_per_pouch  int not null,
  ingredients_usd     numeric not null,
  tolling_usd         numeric not null,
  packaging_usd       numeric not null,
  freight_usd         numeric not null,
  pick_pack_usd       numeric not null,
  handling_pct        numeric not null,
  member_price_usd    numeric not null,
  source_note         text not null
);

insert into cost_model (id, product, servings_per_pouch, ingredients_usd,
  tolling_usd, packaging_usd, freight_usd, pick_pack_usd, handling_pct,
  member_price_usd, source_note)
values (
  'aonic-complete', 'Aonic Complete', 30, 12.60,
  2.00, 0.80, 0.20, 2.50, 0.10,
  19.91,
  'Carl Okpala''s Aonic Complete cost analysis, September 2026. A working model, not an Aonic finance document.'
)
on conflict (id) do update set
  ingredients_usd = excluded.ingredients_usd,
  member_price_usd = excluded.member_price_usd,
  source_note = excluded.source_note;

-- Each ingredient's share of the $12.60 of ingredient cost a pouch carries.
alter table ingredients add column if not exists cost_budget_usd_per_pouch numeric;
alter table ingredients add column if not exists budget_note text;

update ingredients set
  cost_budget_usd_per_pouch = 0.00084,
  budget_note = '1.5 mg of cholecalciferol per pouch. Under a tenth of a cent, so the ceiling is generous and lead time decides this one.'
where id = 'vitamin-d3';

update ingredients set
  cost_budget_usd_per_pouch = 0.0339,
  budget_note = '1.94 g of zinc citrate per pouch. A quarter of a percent of ingredient cost, and cadmium risk matters more than price.'
where id = 'zinc-citrate';

update ingredients set
  cost_budget_usd_per_pouch = 0.96,
  budget_note = '2.4 g of CoQ10 per pouch. Roughly 7.6% of the $12.60 of ingredient cost, so this is where a dollar per kilogram is worth chasing.'
where id = 'coq10';
