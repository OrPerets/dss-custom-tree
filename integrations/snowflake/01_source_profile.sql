-- Run each SELECT separately in a Snowflake worksheet with read access to DWH.HR.
-- These queries do not create or update anything. Record CURRENT_DATE / time zone.
-- The attachment lists names and one sample row per table, not types or cardinality.

-- 1. Verify actual types and column comments before running the extraction.
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COMMENT
FROM DWH.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'HR'
  AND TABLE_NAME IN (
      'DIM_HR_EMP_JOB', 'DIM_HR_USER', 'DIM_HR_POSITION',
      'FACT_HR_EMPJOB', 'FACT_HR_HIRE_TO_RETIRE'
  )
ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- Date coverage: reconcile excluded/future records before accepting headcount.
SELECT CURRENT_DATE() AS extraction_date, COUNT(*) AS all_job_rows,
       COUNT_IF(START_DATE IS NULL) AS missing_start_date_rows,
       COUNT_IF(END_DATE IS NULL) AS open_end_date_rows,
       COUNT_IF(TO_DATE(START_DATE) > TO_DATE(END_DATE)) AS reversed_date_rows,
       COUNT_IF(TO_DATE(START_DATE) > CURRENT_DATE()) AS future_start_rows
FROM DWH.HR.DIM_HR_EMP_JOB;

-- 2. Profile current job statuses and deletion flags using the proposed version rule.
-- Null END_DATE is provisionally treated as open-ended; endpoints are inclusive.
WITH current_jobs AS (
    SELECT j.*
    FROM DWH.HR.DIM_HR_EMP_JOB j
    WHERE TO_DATE(j.START_DATE) <= CURRENT_DATE()
      AND (j.END_DATE IS NULL OR TO_DATE(j.END_DATE) >= CURRENT_DATE())
    QUALIFY DENSE_RANK() OVER (
        PARTITION BY NULLIF(TRIM(TO_VARCHAR(j.EMP_ID)), '')
        ORDER BY j.START_DATE DESC NULLS LAST, j.SEQ_NUMBER DESC NULLS LAST,
                 j.LAST_MODIFIED_DATE_TIME DESC NULLS LAST,
                 j.ETL_UPDATE_DATE DESC NULLS LAST
    ) = 1
)
SELECT EMP_STATUS, IS_DELETED, COUNT(*) AS row_count,
       COUNT(DISTINCT NULLIF(TRIM(TO_VARCHAR(EMP_ID)), '')) AS employee_count,
       COUNT_IF(END_DATE IS NULL) AS null_end_date_count,
       COUNT_IF(NULLIF(TRIM(TO_VARCHAR(MANAGER_ID)), '') IS NULL) AS blank_manager_count
FROM current_jobs
GROUP BY EMP_STATUS, IS_DELETED
ORDER BY row_count DESC;

-- 3. Dimension key uniqueness, including deleted rows. No implicit deduplication.
WITH keys AS (
    SELECT 'DIM_HR_USER.EMP_CODE' AS source,
           NULLIF(TRIM(TO_VARCHAR(EMP_CODE)), '') AS source_key
    FROM DWH.HR.DIM_HR_USER
    UNION ALL
    SELECT 'DIM_HR_USER.EMPLOYEE_NUMBER', NULLIF(TRIM(TO_VARCHAR(EMPLOYEE_NUMBER)), '')
    FROM DWH.HR.DIM_HR_USER
    UNION ALL
    SELECT 'DIM_HR_POSITION.POSITION_CODE', NULLIF(TRIM(TO_VARCHAR(POSITION_CODE)), '')
    FROM DWH.HR.DIM_HR_POSITION
), grouped AS (
    SELECT source, source_key, COUNT(*) AS key_rows FROM keys GROUP BY source, source_key
)
SELECT source, SUM(key_rows) AS total_rows,
       SUM(IFF(source_key IS NULL, key_rows, 0)) AS blank_key_rows,
       COUNT_IF(source_key IS NOT NULL AND key_rows > 1) AS duplicate_nonblank_keys
FROM grouped GROUP BY source;

-- 4. Confirm EMP_ID joins EMP_CODE, rather than assuming EMPLOYEE_NUMBER.
-- Distinct key sets avoid multiplying employee counts during this comparison.
WITH latest_jobs AS (
    SELECT j.* FROM DWH.HR.DIM_HR_EMP_JOB j
    WHERE TO_DATE(j.START_DATE) <= CURRENT_DATE()
      AND (j.END_DATE IS NULL OR TO_DATE(j.END_DATE) >= CURRENT_DATE())
    QUALIFY DENSE_RANK() OVER (
        PARTITION BY NULLIF(TRIM(TO_VARCHAR(j.EMP_ID)), '')
        ORDER BY j.START_DATE DESC NULLS LAST, j.SEQ_NUMBER DESC NULLS LAST,
                 j.LAST_MODIFIED_DATE_TIME DESC NULLS LAST,
                 j.ETL_UPDATE_DATE DESC NULLS LAST
    ) = 1
), active_jobs AS (
    SELECT DISTINCT NULLIF(TRIM(TO_VARCHAR(EMP_ID)), '') AS employee_key,
                    NULLIF(TRIM(TO_VARCHAR(POSITION_ID)), '') AS position_key
    FROM latest_jobs
    WHERE LOWER(TRIM(TO_VARCHAR(EMP_STATUS))) = 'active'
      AND LOWER(TRIM(TO_VARCHAR(IS_DELETED))) IN ('0', 'false')
), codes AS (
    SELECT DISTINCT NULLIF(TRIM(TO_VARCHAR(EMP_CODE)), '') AS employee_key
    FROM DWH.HR.DIM_HR_USER
), numbers AS (
    SELECT DISTINCT NULLIF(TRIM(TO_VARCHAR(EMPLOYEE_NUMBER)), '') AS employee_key
    FROM DWH.HR.DIM_HR_USER
), positions AS (
    SELECT DISTINCT NULLIF(TRIM(TO_VARCHAR(POSITION_CODE)), '') AS position_key
    FROM DWH.HR.DIM_HR_POSITION
)
SELECT COUNT(*) AS employee_position_pairs,
       COUNT_IF(c.employee_key IS NOT NULL) AS matched_user_emp_code,
       COUNT_IF(n.employee_key IS NOT NULL) AS matched_user_employee_number,
       COUNT_IF(p.position_key IS NOT NULL) AS matched_position_code
FROM active_jobs j
LEFT JOIN codes c ON c.employee_key = j.employee_key
LEFT JOIN numbers n ON n.employee_key = j.employee_key
LEFT JOIN positions p ON p.position_key = j.position_key;

-- 5. Check manager eligibility and seniority vocabulary. These are not span limits.
SELECT POSITION_STATUS, MANAGERIAL_ELIGIBILITY, SENIORITY_LEVEL, COUNT(*) AS row_count
FROM DWH.HR.DIM_HR_POSITION
GROUP BY POSITION_STATUS, MANAGERIAL_ELIGIBILITY, SENIORITY_LEVEL
ORDER BY row_count DESC;

-- 6. Compare manager and supervisor within FACT_HR_EMPJOB, retaining grain evidence.
-- The supplied schema has no effective dates for this fact; do not call it history.
WITH facts AS (
    SELECT NULLIF(TRIM(TO_VARCHAR(USERID)), '') AS employee_key,
           NULLIF(TRIM(TO_VARCHAR(MANAGER_ID)), '') AS manager_key,
           NULLIF(TRIM(TO_VARCHAR(SUPERVISER_ID)), '') AS supervisor_key
    FROM DWH.HR.FACT_HR_EMPJOB
), grouped AS (
    SELECT employee_key, COUNT(*) AS key_rows,
           COUNT_IF(manager_key IS DISTINCT FROM supervisor_key) AS differing_rows
    FROM facts GROUP BY employee_key
)
SELECT COUNT(*) AS employee_keys_including_blank,
       COUNT_IF(key_rows > 1) AS keys_with_multiple_rows,
       SUM(differing_rows) AS rows_where_manager_and_supervisor_differ
FROM grouped;

-- 7. Compare job MANAGER_ID to both fact fields only where each employee is unique.
WITH latest_jobs AS (
    SELECT j.* FROM DWH.HR.DIM_HR_EMP_JOB j
    WHERE TO_DATE(j.START_DATE) <= CURRENT_DATE()
      AND (j.END_DATE IS NULL OR TO_DATE(j.END_DATE) >= CURRENT_DATE())
    QUALIFY DENSE_RANK() OVER (
        PARTITION BY NULLIF(TRIM(TO_VARCHAR(j.EMP_ID)), '')
        ORDER BY j.START_DATE DESC NULLS LAST, j.SEQ_NUMBER DESC NULLS LAST,
                 j.LAST_MODIFIED_DATE_TIME DESC NULLS LAST,
                 j.ETL_UPDATE_DATE DESC NULLS LAST
    ) = 1
), jobs AS (
    SELECT NULLIF(TRIM(TO_VARCHAR(EMP_ID)), '') AS employee_key,
           NULLIF(TRIM(TO_VARCHAR(MANAGER_ID)), '') AS manager_key,
           EMP_STATUS, IS_DELETED
    FROM latest_jobs
    QUALIFY COUNT(*) OVER (PARTITION BY NULLIF(TRIM(TO_VARCHAR(EMP_ID)), '')) = 1
), facts AS (
    SELECT NULLIF(TRIM(TO_VARCHAR(USERID)), '') AS employee_key,
           NULLIF(TRIM(TO_VARCHAR(MANAGER_ID)), '') AS manager_key,
           NULLIF(TRIM(TO_VARCHAR(SUPERVISER_ID)), '') AS supervisor_key
    FROM DWH.HR.FACT_HR_EMPJOB
    QUALIFY COUNT(*) OVER (PARTITION BY NULLIF(TRIM(TO_VARCHAR(USERID)), '')) = 1
)
SELECT COUNT(*) AS unique_active_job_employees,
       COUNT_IF(f.employee_key IS NOT NULL) AS unique_fact_matches,
       COUNT_IF(f.employee_key IS NOT NULL AND j.manager_key IS DISTINCT FROM f.manager_key)
           AS differs_from_fact_manager,
       COUNT_IF(f.employee_key IS NOT NULL AND j.manager_key IS DISTINCT FROM f.supervisor_key)
           AS differs_from_fact_supervisor
FROM jobs j LEFT JOIN facts f ON f.employee_key = j.employee_key
WHERE LOWER(TRIM(TO_VARCHAR(j.EMP_STATUS))) = 'active'
  AND LOWER(TRIM(TO_VARCHAR(j.IS_DELETED))) IN ('0', 'false');

-- 8. Inspect the event fact's current/deleted population before using it as a substitute.
SELECT CURRENT_INDICATOR, LAST_EVENT_INDICATOR, IS_DELETED,
       COUNT(*) AS row_count, COUNT(DISTINCT EMP_CODE) AS employee_count
FROM DWH.HR.FACT_HR_HIRE_TO_RETIRE
GROUP BY CURRENT_INDICATOR, LAST_EVENT_INDICATOR, IS_DELETED
ORDER BY row_count DESC;
