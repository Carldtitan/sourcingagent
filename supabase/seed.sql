-- Aonic sourcing engine: seed data
--
-- Ingredients and doses are taken from the published Aonic Complete
-- Supplement Facts panel (HIS formulation) at aoniclife.com.
--
-- Everything else is simulated. The target specifications are our own
-- assumption written against standard industry limits, because Aonic's
-- internal specification sheet was not supplied. The twelve suppliers,
-- their prices, their certificates and their behaviour are invented for
-- this prototype. No real supplier is represented here.

truncate events, approvals, coas, quotes, messages, run_suppliers, runs,
         supplier_ingredients, suppliers, specifications, ingredients restart identity cascade;

-- ---------------------------------------------------------------- ingredients

insert into ingredients (id, name, chemical_form, cas_number, dose_mg, dose_note, sort_order) values
  ('vitamin-d3', 'Vitamin D3', 'Cholecalciferol, crystalline', '67-97-0', 0.05,
   '50 mcg per serving, 250% of the Daily Value', 1),
  ('zinc-citrate', 'Zinc', 'Zinc citrate trihydrate', '5990-32-9', 64.5,
   '20 mg of elemental zinc per serving, delivered as roughly 64.5 mg of the citrate salt', 2),
  ('coq10', 'Coenzyme Q10', 'Ubidecarenone, fermentation derived', '303-98-0', 80,
   '80 mg per serving, bioequivalent to 200 mg of conventional CoQ10', 3);

-- --------------------------------------------------------------- specifications

insert into specifications (
  ingredient_id, assay_min_pct, assay_basis,
  lead_max_ppm, arsenic_max_ppm, cadmium_max_ppm, mercury_max_ppm,
  tpc_max_cfu_g, yeast_mould_max_cfu_g,
  required_certs, max_moq_kg, max_lead_time_days, accepted_origins, source_note
) values
  ('vitamin-d3', 98.0, 'Cholecalciferol by HPLC, dried basis',
   0.5, 1.0, 0.5, 0.1, 1000, 100,
   '{GMP,ISO 22000,Non-GMO}', 250, 84,
   '{China,India,Germany,Switzerland,United States,Japan}',
   'Limits written by us against standard industry practice. Aonic''s internal specification sheet was not supplied.'),
  ('zinc-citrate', 98.0, 'Zinc citrate by titration, 30.0 to 32.0% elemental zinc',
   0.5, 1.0, 0.3, 0.1, 1000, 100,
   '{GMP,ISO 22000}', 1000, 84,
   '{China,India,Germany,Switzerland,United States,Japan}',
   'Cadmium held tighter than the general limit, because cadmium travels with zinc ores. Our assumption, not an Aonic document.'),
  ('coq10', 98.0, 'Ubidecarenone by HPLC, dried basis',
   0.5, 1.0, 0.5, 0.1, 1000, 100,
   '{GMP,ISO 22000,Non-GMO}', 100, 98,
   '{China,Germany,Switzerland,United States,Japan}',
   'Origin limited to countries with established fermentation capacity for this material. Our assumption, not an Aonic document.');

-- ------------------------------------------------------------------ suppliers

insert into suppliers (id, name, country, kind, email_local, certs, stubbornness, reply_delay_s, reply_style, omits_fields) values
  ('jiangsu-vitalabs',   'Jiangsu Vitalabs',            'China',         'manufacturer', 'jiangsu',   '{GMP,ISO 22000,Non-GMO,Kosher}',              0.35, 20, 'formal', '{}'),
  ('hebei-nutra',        'Hebei Nutra Chemical',        'China',         'manufacturer', 'hebei',     '{GMP,ISO 22000}',                             0.50, 35, 'terse',  '{payment_terms}'),
  ('shandong-kang',      'Shandong Kang Biotech',       'China',         'manufacturer', 'shandong',  '{GMP,ISO 22000,Halal}',                       0.90, 45, 'terse',  '{}'),
  ('zhejiang-rongtai',   'Zhejiang Rongtai Chemical',   'China',         'manufacturer', 'zhejiang',  '{ISO 22000}',                                 0.60, 30, 'terse',  '{}'),
  ('sri-venkat',         'Sri Venkat Nutrients',        'India',         'manufacturer', 'venkat',    '{GMP,ISO 22000,Kosher,Halal}',                0.40, 25, 'chatty', '{}'),
  ('mumbai-fine',        'Mumbai Fine Actives',         'India',         'manufacturer', 'mumbai',    '{GMP,FSSC 22000,ISO 22000,Non-GMO}',          0.45, 55, 'formal', '{lead_time}'),
  ('gujarat-bulk',       'Gujarat Bulk Ingredients',    'India',         'manufacturer', 'gujarat',   '{GMP,ISO 22000}',                             0.25, 40, 'terse',  '{}'),
  ('rheinland-vitamin',  'Rheinland Vitamin Werke',     'Germany',       'manufacturer', 'rheinland', '{GMP,ISO 22000,Non-GMO,Kosher,Halal}',        0.75, 60, 'formal', '{}'),
  ('helvetia-actives',   'Helvetia Actives AG',         'Switzerland',   'distributor',  'helvetia',  '{GMP,ISO 22000,Non-GMO}',                     0.80, 30, 'formal', '{}'),
  ('osaka-ferment',      'Osaka Ferment Kagaku',        'Japan',         'manufacturer', 'osaka',     '{GMP,ISO 22000,Non-GMO,Kosher}',              0.70, 90, 'formal', '{}'),
  ('midwest-botanical',  'Midwest Botanical Supply',    'United States', 'distributor',  'midwest',   '{GMP,Non-GMO,Kosher}',                        0.30, 15, 'chatty', '{incoterm}'),
  ('atlantic-partners',  'Atlantic Ingredient Partners','United States', 'distributor',  'atlantic',  '{GMP,ISO 22000}',                             0.55, 25, 'formal', '{}');

-- ------------------------------------------------------- supplier x ingredient

-- Vitamin D3, crystalline cholecalciferol
insert into supplier_ingredients (supplier_id, ingredient_id, list_price, price_floor, price_currency, price_unit, incoterm, purity_pct, moq_kg, lead_time_days, coa_fault) values
  ('jiangsu-vitalabs',  'vitamin-d3', 640, 505, 'USD', 'kg', 'FOB', 99.1,  25, 56, null),
  ('hebei-nutra',       'vitamin-d3', 590, 470, 'USD', 'kg', 'EXW', 98.4,  50, 63, null),
  ('shandong-kang',     'vitamin-d3', 705, 615, 'USD', 'kg', 'FOB', 99.3,  25, 70, null),
  ('zhejiang-rongtai',  'vitamin-d3', 540, 430, 'USD', 'kg', 'EXW', 98.0, 100, 63, null),
  ('sri-venkat',        'vitamin-d3', 615, 490, 'USD', 'kg', 'CIF', 98.8,  25, 70, null),
  ('mumbai-fine',       'vitamin-d3', 668, 540, 'USD', 'kg', 'FOB', 99.0,  50, 77, null),
  ('gujarat-bulk',      'vitamin-d3', 498, 415, 'USD', 'kg', 'EXW', 97.2, 500, 84, 'assay'),
  ('rheinland-vitamin', 'vitamin-d3', 742, 668, 'EUR', 'kg', 'DDP', 99.6,  10, 35, null),
  ('helvetia-actives',  'vitamin-d3', 795, 720, 'EUR', 'kg', 'DDP', 99.4,   5, 21, null),
  ('midwest-botanical', 'vitamin-d3', 355, 305, 'USD', 'lb', 'DDP', 99.0,  10, 14, null),
  ('atlantic-partners', 'vitamin-d3', 726, 620, 'USD', 'kg', 'DDP', 98.9,  20, 28, null);

-- Zinc citrate trihydrate
insert into supplier_ingredients (supplier_id, ingredient_id, list_price, price_floor, price_currency, price_unit, incoterm, purity_pct, moq_kg, lead_time_days, coa_fault) values
  ('jiangsu-vitalabs',  'zinc-citrate', 18.40, 14.20, 'USD', 'kg', 'FOB', 98.9,  500, 49, null),
  ('hebei-nutra',       'zinc-citrate', 15.80, 12.10, 'USD', 'kg', 'EXW', 98.5,  500, 56, 'lead'),
  ('shandong-kang',     'zinc-citrate', 21.30, 18.60, 'USD', 'kg', 'FOB', 99.1,  250, 56, null),
  ('zhejiang-rongtai',  'zinc-citrate', 14.90, 11.40, 'USD', 'kg', 'EXW', 98.2, 1000, 49, null),
  ('sri-venkat',        'zinc-citrate', 17.60, 13.40, 'USD', 'kg', 'CIF', 98.7,  500, 63, null),
  ('mumbai-fine',       'zinc-citrate', 19.20, 15.30, 'USD', 'kg', 'FOB', 99.0,  250, 70, null),
  ('gujarat-bulk',      'zinc-citrate', 13.70, 10.90, 'USD', 'kg', 'EXW', 98.4, 2000, 77, null),
  ('rheinland-vitamin', 'zinc-citrate', 26.40, 23.10, 'EUR', 'kg', 'DDP', 99.4,  200, 28, null),
  ('helvetia-actives',  'zinc-citrate', 29.80, 26.50, 'EUR', 'kg', 'DDP', 99.2,  100, 21, null),
  ('midwest-botanical', 'zinc-citrate', 13.10,  11.40,'USD', 'lb', 'DDP', 98.8,  100, 14, null),
  ('atlantic-partners', 'zinc-citrate', 24.60, 20.20, 'USD', 'kg', 'DDP', 98.9,  250, 28, 'micro');

-- Coenzyme Q10, fermentation derived
insert into supplier_ingredients (supplier_id, ingredient_id, list_price, price_floor, price_currency, price_unit, incoterm, purity_pct, moq_kg, lead_time_days, coa_fault) values
  ('jiangsu-vitalabs',  'coq10', 428, 352, 'USD', 'kg', 'FOB', 99.2,  25, 63, null),
  ('hebei-nutra',       'coq10', 396, 328, 'USD', 'kg', 'EXW', 98.3,  50, 70, null),
  ('shandong-kang',     'coq10', 474, 418, 'USD', 'kg', 'FOB', 99.0,  25, 70, null),
  ('zhejiang-rongtai',  'coq10', 362, 298, 'USD', 'kg', 'EXW', 98.1, 100, 63, null),
  ('rheinland-vitamin', 'coq10', 618, 556, 'EUR', 'kg', 'DDP', 99.5,  10, 42, null),
  ('helvetia-actives',  'coq10', 682, 614, 'EUR', 'kg', 'DDP', 99.3,   5, 28, null),
  ('osaka-ferment',     'coq10', 705, 640, 'USD', 'kg', 'CIF', 99.7,  25, 91, null),
  ('midwest-botanical', 'coq10', 248, 214, 'USD', 'lb', 'DDP', 99.0,  10, 21, null),
  ('atlantic-partners', 'coq10', 596, 510, 'USD', 'kg', 'DDP', 98.8,  20, 35, null);
