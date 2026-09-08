# Build organization-tree inputs from DWH.HR

Prepared from the supplied `ipas.txt` inventory (32 tables, column names and one sample row per table) and the current plugin input contract. This is a proposed current-snapshot mapping. The attachment does not establish joins, uniqueness, complete status vocabularies or policy definitions. The SQL has not been executed against your Snowflake account.

You need one workforce dataset and, optionally, one manager-rules dataset. Saved versions use a managed folder, not a third HR table. All SQL in this folder is read-only; it does not create tables or change `DWH.HR`.

## Proposed source mapping

Start with effective job assignments, then enrich them with user and position attributes. Starting from the user directory alone can include technical accounts: the supplied user sample is a guest account.

| Tree column | Proposed DWH.HR source | Interpretation / handling |
| --- | --- | --- |
| `employee_id` | `DIM_HR_EMP_JOB.EMP_ID` | Trimmed text; preserve IDs without numeric coercion. |
| `manager_id` | `DIM_HR_EMP_JOB.MANAGER_ID` | Direct reporting line, pending business confirmation. Only blank/null is treated as no manager. |
| `full_name` | `DIM_HR_USER.FULL_NAME` | Join `EMP_JOB.EMP_ID = USER.EMP_CODE`; profile this against `EMPLOYEE_NUMBER`. |
| `job_title` | `DIM_HR_POSITION.POSITION_TITLE` | Join `EMP_JOB.POSITION_ID = POSITION.POSITION_CODE`. |
| `department` | `DIM_HR_USER.ORGANIZATIONAL_LEVEL_3` | Proposed department definition: Org 3. Use one consistent business level. |
| `location` | `DIM_HR_USER.LOCATION` | Expected display label; profile its vocabulary. Position location is a code and is not a label fallback. |
| `level` | `DIM_HR_POSITION.SENIORITY_LEVEL` | Raw seniority code for display. Not an approved hierarchy/rule ordering. |
| `employment_status` | `DIM_HR_EMP_JOB.EMP_STATUS` | Initial candidate population: `Active`, normalized to `active`. |
| `can_be_manager` | `DIM_HR_POSITION.MANAGERIAL_ELIGIBILITY` | Recognized yes/no, true/false, 1/0 only. Unknown values must be resolved. |
| `email` | `DIM_HR_USER.EMAIL` | Optional. |
| `team_name` | `DIM_HR_USER.ORGANIZATIONAL_LEVEL_5` | Optional; proposed team definition: Org 5. |
| `start_date` | `DIM_HR_USER.HIRE_DATE` | Optional employee hire date; not job-assignment start date. |
| `max_direct_reports` | No established policy source in attachment | Leave null until an approved capacity policy exists. |
| `photo_url`, `sort_order` | Not needed initially | Leave null. |

The required nonblank attributes are employee ID, full name, job title, department, location, level and employment status. The extract also requires an explicit manager-eligibility value to prevent the parser's blank-to-true default from accepting missing policy data.

## How to build the datasets

1. Run the SELECTs in `01_source_profile.sql` individually in Snowflake. Review types/comments, deletion/status values, current-row selection, key uniqueness, join coverage and reporting-line comparisons.
2. Confirm the source choices below. Run `02_employee_candidates.sql` as a Snowflake SELECT or a Dataiku SQL-query input named `org_employee_candidates`. It returns the 15 workforce columns plus `source_issue_count` and `source_issues`.
3. Export the complete candidate result as UTF-8 CSV, preserving lowercase column names, text IDs and blank nulls. Run the included validator. It rejects source issues, then uses the same hierarchy and rule validation as the plugin. Only a passing run with `--output` creates `org_employees.csv`.
4. Upload that accepted CSV as the Dataiku dataset `org_employees`, or implement the same validation gate before publishing a recurring Dataiku output. Configure it as the webapp's **Input workforce dataset**. A direct SQL-query input also works after validation, but the plugin does not enforce the extra source diagnostic columns: a recurring refresh needs its own source-quality gate.
5. Initially leave **Default rules dataset** unselected. When rules are agreed, populate `manager_rules_template.csv` as `org_manager_rules`, validate it together with employees, and select it. `03_manager_rules_template.sql` provides the same empty typed schema if you prefer a SQL-backed dataset.
6. For **Save version**, create/select an empty managed folder such as `org_tree_versions` in **Baseline folder**.

Run from this folder (Python 3 with `pandas` installed):

```bash
python3 validate_extract.py /path/to/org_employee_candidates.csv \
  --output /path/to/org_employees.csv

# Once business rules exist, validate both inputs together:
python3 validate_extract.py /path/to/org_employee_candidates.csv \
  --rules /path/to/org_manager_rules.csv \
  --output /path/to/org_employees_with_rules.csv
```

The standalone ZIP contains the plugin's validation library under `python-lib/`; within the repository, the script uses the existing library. The script makes no database or DSS connections and will not overwrite an existing output file.

Do not remove failing employees with `WHERE source_issue_count = 0`: that can disconnect the hierarchy or hide whole teams. Resolve the causes and rebuild the full candidate set. A successful gate requires unique employee IDs, exactly one root, every other manager present, no reporting cycles, eligible active managers, and compatibility with all supplied rules.

## Decisions that must be settled with the source owner

**Reporting relationship.** The draft uses `DIM_HR_EMP_JOB.MANAGER_ID`. In the supplied samples, `FACT_HR_EMPJOB.MANAGER_ID` differs from `SUPERVISER_ID`; `FACT_HR_HIRE_TO_RETIRE.CURRENT_MANAGER_ID` also differs from its supervisor fields. These are alternative relationships, not interchangeable spellings. The profile compares the job source against both fact fields. Agreement rates help diagnose joins but do not decide which relationship the business needs. The relationships dimension's sample is an HR Partner relationship, so it is not a default line-manager source.

**Current population and row grain.** The proposal uses jobs effective today, with inclusive endpoints and null end dates treated as open-ended. It ranks by start date, sequence, source modification time, then ETL update time. Status and deletion filters apply after version selection. Exact latest ties are retained and flagged. Multiple concurrent assignments need an explicit primary-assignment rule because the plugin represents one node per employee. Active means the literal `Active` vocabulary, not employment type; contractors with active assignments are not separately excluded. Review leave, suspended and other statuses before adopting this population. Missing/invalid start dates and excluded statuses must be reconciled with expected headcount.

**Dimension grain.** The query requires one `DIM_HR_USER` row per `EMP_CODE` and one `DIM_HR_POSITION` row per `POSITION_CODE`, including historical/deleted rows in those uniqueness checks. Missing or multiple matches are flagged without multiplying employees or selecting an arbitrary dimension version. If these tables retain history, replace that strict assumption with their documented effective/version selection. `POSITION.CREATE_DATE` is not assumed to be an effective-start field; `RECORD_STATUS = 'N'` is not assumed to mean deleted. Expired positions and position statuses other than `Active` require review. User/position values represent the current dimension snapshot, so changing the date in the query alone does not create a valid historical tree.

**Tree scope and root.** The plugin accepts one connected tree. A whole-company extract may contain several organizations or references to inactive/out-of-scope managers. Do not turn all unmatched managers into roots. For one business unit, choose its actual head and retain that head plus all descendants; clear only that explicitly chosen head's external manager reference. Do not simply filter by department if reporting lines cross departments. Any source sentinel such as `0`, `-99` or a special text ID needs an explicit source-defined interpretation before becoming null. Source gaps need correction, not automatic reassignment to the CEO.

**Levels.** The attachment has several different concepts: position seniority (`S1`, etc.), job level letters, and opaque employee/position level codes. Keep them separate. The current plugin compares the first numeric part of a level when present, otherwise text; this is not a general HR grade hierarchy. Leave `min_child_level` and `max_child_level` empty until HR defines the relevant ordering. If ordinal enforcement is needed, add an explicit mapping to consistent `L1`, `L2`, etc. and apply it to both employees and rules.

## Optional policy dataset

| Column | How to supply it |
| --- | --- |
| `manager_id` | Existing employee ID; at most one rules row per manager. |
| `max_direct_reports` | Approved maximum number of direct reports, as an integer. Null means no rules-level override. |
| `allowed_departments` | Exact labels from employee `department`, separated by `|`. Blank means unrestricted. |
| `allowed_locations` | Exact labels from employee `location`, separated by `|`. Blank means unrestricted. |
| `min_child_level`, `max_child_level` | Leave blank until a consistent ordered level mapping is approved. |
| `rule_note` | Human explanation; does not execute logic. |

`TEAM_SIZE_DIRECT` and `TOTAL_DIRECT_REPORTS_PER_MANAGER` describe observed reporting counts. They are not capacity policies. The plugin computes current direct-report counts from the extracted edges. Existing relationships must satisfy the supplied rules before the tree can load; it does not enforce them only on future moves. A nonblank rules capacity overrides the employee-row capacity. Blank capacity in both places means unlimited.

For example, an approved rule allowing a particular manager up to 10 reports in Engineering or Data, located in Israel or India, would use `10`, `Engineering|Data` and `Israel|India`. Those are illustrative policy values, not facts inferred about Amdocs, and labels must match the real extract.

## Other tables

Use `DIM_HR_JOB_CODE` for a job-name fallback only after validating job-code/effective-date joins. `DIM_HR_DEPARTMENT` can resolve an organization code after confirming that its grain matches the chosen department level. `DIM_HR_SENIORITY` / `DIM_HR_GO_LEVEL` can add labels but do not by themselves establish rule ordering. `FACT_HR_HIRE_TO_RETIRE` may be the better canonical source if HR certifies its current flag, row grain and reporting semantics; it is deliberately not mixed into the first extract without that evidence. Recruitment, applicants, emergency contacts, compensation and talent-risk attributes are not needed for the current tree.

## SQL notes and validation scope

Quoted lowercase aliases preserve the plugin's exact column names in Snowflake: [identifier rules](https://docs.snowflake.com/en/sql-reference/identifiers-syntax). Current-row diagnostics use [QUALIFY](https://docs.snowflake.com/en/sql-reference/constructs/qualify); the extract builds diagnostic lists with [ARRAY_CONSTRUCT_COMPACT](https://docs.snowflake.com/en/sql-reference/functions/array_construct_compact).

Local static/fixture checks cannot establish live Snowflake types, permissions, join coverage, HR meanings or actual tree validity. Run the profile and candidate validation against the real full extract before using it in DSS.
