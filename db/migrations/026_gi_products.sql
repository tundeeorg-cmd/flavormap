-- 026  gi_products — geographical-indication products (Task 4a).
--
-- A different relation from every other source in this project: GI data binds an
-- ingredient/product to a place *by law*, which makes it the only dataset here that
-- establishes provenance rather than usage. Not the recipes table, and not
-- local_dish_inventory: no dish, no ingredient list, no community survey — a legal
-- product designation with a province.
--
-- Rule 8, applied specifically per Task 4b: GI catalogue entries split into
-- product-level records (the designation itself, e.g. ข้าวหอมมะลิสุรินทร์) and
-- registrant-level records (ผู้ขอใช้ / ผู้ผลิตที่ใช้ — named individuals and
-- businesses with addresses). Only the product level is ever modelled here. There is
-- no column on this table for a registrant name, an applicant name, or an address,
-- and none should ever be added — that data does not belong in this project at all,
-- not even redacted, per Bible §4.

CREATE TABLE gi_products (
  gi_product_id        BIGSERIAL PRIMARY KEY,
  catalogue_id         BIGINT REFERENCES source_catalogue,  -- which catalogue entry this came from

  product_name_th      TEXT NOT NULL,
  province_code        TEXT REFERENCES provinces,  -- nullable by design, rule 2
  gi_registration_ref  TEXT,               -- the official GI registration number/reference
  product_category     TEXT,               -- e.g. ข้าว, ผลไม้ — source-stated, not a taxonomy

  -- Both exist in the source per the brief's own example (ข้าวหอมมะลิสุรินทร์:
  -- "both applicants and certified producers") — a product can appear at either
  -- stage, and the two are not the same claim about the product.
  registration_status  TEXT,               -- e.g. 'applicant' | 'certified', source-stated

  collected_at         DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE INDEX gi_products_province_idx ON gi_products (province_code);
