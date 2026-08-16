-- 013  HD-1 (decided 2026-08-16, option B): five-way dialect split PLUS an explicit
--      `Transitional` value for provinces that genuinely straddle a boundary.
--
-- Why the sixth value exists: forcing a boundary province into its majority group
-- misdescribes exactly the provinces RQ1 looks at when hunting for a change point.
-- `Transitional` lets those provinces be reported separately, or dropped in a
-- sensitivity run, without pretending the ambiguity is not there.
--
-- Bible §14 (L12) commits to publishing the resulting matrix, judgment calls included.

ALTER TABLE provinces
  ADD CONSTRAINT provinces_dialect_group_check
  CHECK (dialect_group IN (
    'Central',       -- ภาษากลาง
    'Kam_Mueang',    -- คำเมือง / Lanna, upper North
    'Isaan_Lao',     -- ลาวอีสาน
    'Dambro',        -- ปักษ์ใต้ / Southern Thai
    'Malay',         -- Pattani Malay
    'Transitional'   -- straddles a boundary; see decision_note in docs/decisions.md
  ));

COMMENT ON COLUMN provinces.dialect_group IS
  'HD-1, option B. Five linguistic groups plus Transitional. NULL is still permitted: '
  'an unassigned province is honest, a wrongly-assigned one is not.';
