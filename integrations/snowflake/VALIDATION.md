# Local validation — 2026-09-08

The source is a schema/sample inventory, not a live warehouse export. No Snowflake or DSS connection was used and no HR data was written.

- All 11 SELECT statements parsed as Snowflake SQL with SQLGlot. Source-column references resolved against the table/column inventory supplied in `ipas.txt`; the metadata query was checked against the information-schema column names.
- The candidate SELECT exposes the exact 15 plugin workforce column names and two diagnostic columns.
- Thirteen synthetic checks passed using fictional records. SQLGlot translated the extraction to DuckDB for these local checks; this does not establish Snowflake runtime equivalence or live acceptance.
- The export helper compiled and ran with the existing plugin validation library.

Synthetic coverage:

1. Valid employee extraction and plugin acceptance.
2. Duplicate user keys are flagged without multiplying employee rows.
3. Duplicate position keys are flagged without multiplying employee rows.
4. Tied latest job records are retained and flagged.
5. Missing manager references are flagged.
6. Unknown manager eligibility is flagged.
7. Unknown job deletion flags are retained and flagged.
8. A latest deleted job does not revive an older active version in the effective candidate set.
9. A latest inactive job does not revive an older active version in the effective candidate set.
10. The plugin rejects an existing manager marked ineligible.
11. The plugin rejects a reporting cycle.
12. The plugin rejects multiple roots.
13. The CLI writes only a validated 15-column output, creates no output for source-quality failures, and refuses to overwrite an existing file.

Still requires warehouse verification: actual data types, read permissions, date semantics, effective/version grain, join coverage, reporting-line authority, population scope, seniority interpretation, accepted policy values and validation of the complete real extract.
