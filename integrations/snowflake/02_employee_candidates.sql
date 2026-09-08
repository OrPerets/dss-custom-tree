-- Read-only candidate extraction. Run 01_source_profile.sql and review README first.
-- Current snapshot only: DIM_HR_USER / DIM_HR_POSITION are not historic as-of joins.
-- Proposed reporting line: DIM_HR_EMP_JOB.MANAGER_ID. Proposed department: Org 3.
-- Keep diagnostic columns until validation; the plugin itself ignores these columns.
WITH effective_jobs AS (
    SELECT j.*,
        NULLIF(TRIM(TO_VARCHAR(j.EMP_ID)), '') AS employee_key,
        DENSE_RANK() OVER (
            PARTITION BY NULLIF(TRIM(TO_VARCHAR(j.EMP_ID)), '')
            ORDER BY j.START_DATE DESC NULLS LAST,
                     j.SEQ_NUMBER DESC NULLS LAST,
                     j.LAST_MODIFIED_DATE_TIME DESC NULLS LAST,
                     j.ETL_UPDATE_DATE DESC NULLS LAST
        ) AS version_rank
    FROM DWH.HR.DIM_HR_EMP_JOB j
    WHERE TO_DATE(j.START_DATE) <= CURRENT_DATE()
      AND (j.END_DATE IS NULL OR TO_DATE(j.END_DATE) >= CURRENT_DATE())
), latest_jobs AS (
    -- Retain tied latest versions and flag them; never choose an arbitrary row.
    SELECT j.*,
           COUNT(*) OVER (PARTITION BY j.employee_key) AS latest_job_matches
    FROM effective_jobs j
    WHERE j.version_rank = 1
), active_jobs AS (
    -- Filter status/deletion AFTER version selection to avoid reviving old rows.
    -- Null/unrecognized deletion flags remain visible and fail the quality gate.
    SELECT * FROM latest_jobs
    WHERE LOWER(TRIM(TO_VARCHAR(EMP_STATUS))) = 'active'
      AND COALESCE(LOWER(TRIM(TO_VARCHAR(IS_DELETED))), '')
          NOT IN ('1', 'true')
), users_counted AS (
    SELECT u.*,
        NULLIF(TRIM(TO_VARCHAR(u.EMP_CODE)), '') AS employee_key,
        COUNT(*) OVER (
            PARTITION BY NULLIF(TRIM(TO_VARCHAR(u.EMP_CODE)), '')
        ) AS key_matches
    FROM DWH.HR.DIM_HR_USER u
), user_keys AS (
    SELECT employee_key, MAX(key_matches) AS key_matches
    FROM users_counted GROUP BY employee_key
), positions_counted AS (
    -- Do not guess a history/version ordering for this dimension.
    SELECT p.*,
        NULLIF(TRIM(TO_VARCHAR(p.POSITION_CODE)), '') AS position_key,
        COUNT(*) OVER (
            PARTITION BY NULLIF(TRIM(TO_VARCHAR(p.POSITION_CODE)), '')
        ) AS key_matches
    FROM DWH.HR.DIM_HR_POSITION p
), position_keys AS (
    SELECT position_key, MAX(key_matches) AS key_matches
    FROM positions_counted GROUP BY position_key
), mapped AS (
    SELECT
        j.employee_key AS "employee_id",
        NULLIF(TRIM(TO_VARCHAR(j.MANAGER_ID)), '') AS "manager_id",
        NULLIF(TRIM(u.FULL_NAME), '') AS "full_name",
        NULLIF(TRIM(p.POSITION_TITLE), '') AS "job_title",
        NULLIF(TRIM(u.ORGANIZATIONAL_LEVEL_3), '') AS "department",
        NULLIF(TRIM(u.LOCATION), '') AS "location",
        NULLIF(TRIM(TO_VARCHAR(p.SENIORITY_LEVEL)), '') AS "level",
        LOWER(TRIM(TO_VARCHAR(j.EMP_STATUS))) AS "employment_status",
        NULLIF(TRIM(u.EMAIL), '') AS "email",
        NULLIF(TRIM(u.ORGANIZATIONAL_LEVEL_5), '') AS "team_name",
        NULL::VARCHAR AS "photo_url",
        TO_CHAR(TO_DATE(u.HIRE_DATE), 'YYYY-MM-DD') AS "start_date",
        NULL::INTEGER AS "max_direct_reports",
        CASE LOWER(TRIM(TO_VARCHAR(p.MANAGERIAL_ELIGIBILITY)))
            WHEN 'yes' THEN TRUE WHEN 'true' THEN TRUE WHEN '1' THEN TRUE
            WHEN 'no' THEN FALSE WHEN 'false' THEN FALSE WHEN '0' THEN FALSE
            ELSE NULL
        END AS "can_be_manager",
        NULL::INTEGER AS "sort_order",
        j.latest_job_matches,
        LOWER(TRIM(TO_VARCHAR(j.IS_DELETED))) AS job_deleted,
        COALESCE(uk.key_matches, 0) AS user_matches,
        LOWER(TRIM(TO_VARCHAR(u.IS_DELETED))) AS user_deleted,
        COALESCE(pk.key_matches, 0) AS position_matches,
        TO_DATE(p.END_DATE) AS position_end_date,
        LOWER(TRIM(TO_VARCHAR(p.POSITION_STATUS))) AS position_status
    FROM active_jobs j
    LEFT JOIN user_keys uk ON uk.employee_key = j.employee_key
    LEFT JOIN users_counted u
        ON u.employee_key = j.employee_key AND u.key_matches = 1
    LEFT JOIN position_keys pk
        ON pk.position_key = NULLIF(TRIM(TO_VARCHAR(j.POSITION_ID)), '')
    LEFT JOIN positions_counted p
        ON p.position_key = NULLIF(TRIM(TO_VARCHAR(j.POSITION_ID)), '')
       AND p.key_matches = 1
), assessed AS (
    SELECT m.*,
        ARRAY_CONSTRUCT_COMPACT(
            IFF(m.latest_job_matches <> 1, 'ambiguous_latest_job', NULL),
            IFF(COALESCE(m.job_deleted, '') NOT IN ('0', 'false'),
                'unknown_job_deletion_flag', NULL),
            IFF(m.user_matches = 0, 'missing_user_match', NULL),
            IFF(m.user_matches > 1, 'ambiguous_user_match', NULL),
            IFF(m.user_matches = 1 AND COALESCE(m.user_deleted, '') NOT IN ('0', 'false'),
                'deleted_or_unknown_user', NULL),
            IFF(m.position_matches = 0, 'missing_position_match', NULL),
            IFF(m.position_matches > 1, 'ambiguous_position_match', NULL),
            IFF(m.position_matches = 1 AND COALESCE(m.position_status, '') <> 'active',
                'position_status_requires_review', NULL),
            IFF(m.position_end_date < CURRENT_DATE(), 'expired_position', NULL),
            IFF(m."employee_id" IS NULL, 'missing_employee_id', NULL),
            IFF(m."full_name" IS NULL, 'missing_full_name', NULL),
            IFF(m."job_title" IS NULL, 'missing_job_title', NULL),
            IFF(m."department" IS NULL, 'missing_department', NULL),
            IFF(m."location" IS NULL, 'missing_location', NULL),
            IFF(m."level" IS NULL, 'missing_level', NULL),
            IFF(m."can_be_manager" IS NULL, 'unknown_manager_eligibility', NULL),
            IFF(m."manager_id" = m."employee_id", 'self_reporting', NULL),
            IFF(m."manager_id" IS NOT NULL AND parent.employee_key IS NULL,
                'manager_missing_from_active_population', NULL)
        ) AS source_issues
    FROM mapped m
    LEFT JOIN (SELECT DISTINCT employee_key FROM active_jobs) parent
        ON parent.employee_key = m."manager_id"
)
SELECT
    "employee_id", "manager_id", "full_name", "job_title", "department",
    "location", "level", "employment_status", "email", "team_name",
    "photo_url", "start_date", "max_direct_reports", "can_be_manager", "sort_order",
    ARRAY_SIZE(source_issues) AS "source_issue_count",
    ARRAY_TO_STRING(source_issues, '|') AS "source_issues"
FROM assessed;
