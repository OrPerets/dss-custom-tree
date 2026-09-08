-- Optional dataset: no rules are inferred from HR headcounts.
-- This read-only SELECT returns the correct columns and zero rows.
SELECT
    NULL::VARCHAR AS "manager_id",
    NULL::INTEGER AS "max_direct_reports",
    NULL::VARCHAR AS "allowed_departments",
    NULL::VARCHAR AS "allowed_locations",
    NULL::VARCHAR AS "min_child_level",
    NULL::VARCHAR AS "max_child_level",
    NULL::VARCHAR AS "rule_note"
WHERE FALSE;
