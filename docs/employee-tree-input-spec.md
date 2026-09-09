# Employee Tree Input Specification

## Overview

The plugin should accept a flat employee table and build a hierarchy from it. Each row represents one employee. The hierarchy is formed by joining `manager_id` to another row's `employee_id`.

Use:

- One required employee dataset
- One optional manager-constraints dataset

## Employee Columns

Select the prepared dataset in your Dataiku project. The plugin reads it through the DSS dataset API; no warehouse connection, SQL configuration or warehouse table names are needed. Column names are matched without case sensitivity and with surrounding whitespace removed. Ambiguous duplicates such as both `employee_id` and `EMPLOYEE_ID` are rejected.

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| `employee_id` | string | yes | Unique stable identifier for the employee |
| `manager_id` | string | column required | Empty or null value only for the root; other values reference employee IDs |
| `full_name` | string | no | Missing name displays as `Employee <employee_id>` with a review notice |
| `job_title` | string | no | Missing title displays as `Role not provided` |
| `department` | string | no | Needed when an applicable department rule must be checked |
| `location` | string | no | Needed when an applicable location rule must be checked |
| `level` | string | no | Needed when an applicable level-range rule must be checked |
| `employment_status` | string | no for viewing | Must explicitly be `active` to receive new direct reports |

Missing details remain null in the underlying data and generate a concise review notice for the employee. The source dataset and its blank values are preserved in hierarchy exports; display placeholders are not written back. Only the employee-ID value and the two hierarchy columns are mandatory for viewing a structurally valid tree. Keep both ID columns as strings in the Dataiku dataset schema to preserve leading zeros.

## Recommended Optional Employee Columns

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| `email` | string | no | Useful for details panel |
| `team_name` | string | no | Useful for grouping and filtering |
| `photo_url` | string | no | For avatar rendering |
| `start_date` | date | no | For tenure display |
| `max_direct_reports` | integer | no | Per-manager override |
| `can_be_manager` | boolean | no | Omitted column defaults to true for compatibility. An explicit blank is unknown and blocks new reports; false blocks management |
| `sort_order` | integer | no | Stable sibling ordering |

## Required Data Rules

- `employee_id` must be unique.
- `manager_id` must either be empty/null or reference an existing `employee_id`.
- Exactly one employee should have an empty/null `manager_id` in v1.
- No employee may manage themselves.
- The hierarchy must be acyclic.
- Missing status/explicitly blank eligibility allows viewing existing relationships with review notices but blocks assigning new reports to that person. A known inactive or ineligible manager with existing reports remains a validation error.
- Missing department/location/level required by an existing rule produces a review notice; a proposed move requiring that missing value is blocked. Known rule and capacity violations remain errors.

## Optional Manager Constraints Dataset

Use this second dataset when business rules vary by manager. One row represents rules for one manager.

### Suggested Columns

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| `manager_id` | string | yes | Must match an employee `employee_id` |
| `max_direct_reports` | integer | no | Overrides employee-level default |
| `allowed_departments` | string | no | Pipe-separated list such as `Engineering|Data` |
| `allowed_locations` | string | no | Pipe-separated list such as `Tel Aviv|Remote` |
| `min_child_level` | string | no | Lowest allowed child level |
| `max_child_level` | string | no | Highest allowed child level |
| `rule_note` | string | no | Human-readable explanation for UI feedback |

## Move Validation Rules

When a user drags employee `A` under manager `B`, validate in this order:

1. `B` exists.
2. `A` is not the root if root moves are forbidden.
3. `B` is not `A`.
4. `B` is not inside `A`'s subtree.
5. `B` can accept direct reports.
6. `B` will not exceed `max_direct_reports`.
7. Department and location rules pass if configured.
8. Level-range rules pass if configured.

## Normalized Frontend Payload

The backend should return a normalized document similar to:

```json
{
  "meta": {
    "root_employee_id": "E001",
    "employee_count": 15,
    "warning_count": 0
  },
  "nodes": [
    {
      "employee_id": "E001",
      "manager_id": null,
      "full_name": "Nora Levin",
      "job_title": "CEO",
      "department": "Executive",
      "location": "Tel Aviv",
      "level": "L1",
      "employment_status": "active",
      "direct_reports_count": 3,
      "max_direct_reports": 4,
      "children_ids": ["E002", "E003", "E004"],
      "warnings": []
    }
  ],
  "change_log": []
}
```

## Demo Files In This Repo

- `demo/employees-demo.csv`
- `demo/manager-constraints-demo.csv`
