import pandas as pd

from employee_tree.exceptions import EmployeeTreeValidationError
from employee_tree.models import EmployeeRecord, ManagerConstraint


REQUIRED_EMPLOYEE_FIELDS = (
    "employee_id",
    "full_name",
    "job_title",
    "department",
    "location",
    "level",
    "employment_status",
)


def _is_blank(value):
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except TypeError:
        pass
    return isinstance(value, str) and value.strip() == ""


def _normalize_text(value):
    if _is_blank(value):
        return None
    return str(value).strip()


def _parse_bool(value, field_name, row_number, default=True):
    if _is_blank(value):
        return default
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in ("true", "1", "yes", "y"):
        return True
    if normalized in ("false", "0", "no", "n"):
        return False

    raise EmployeeTreeValidationError(
        [{
            "code": "invalid_boolean",
            "severity": "error",
            "field": field_name,
            "row_number": row_number,
            "message": "Row {0}: column '{1}' must be a boolean value.".format(row_number, field_name),
        }]
    )


def _parse_int(value, field_name, row_number):
    if _is_blank(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise EmployeeTreeValidationError(
            [{
                "code": "invalid_integer",
                "severity": "error",
                "field": field_name,
                "row_number": row_number,
                "message": "Row {0}: column '{1}' must be an integer.".format(row_number, field_name),
            }]
        )


def _parse_pipe_separated(value):
    normalized = _normalize_text(value)
    if normalized is None:
        return []
    return [item.strip() for item in normalized.split("|") if item.strip()]


def _parse_date_like(value):
    if _is_blank(value):
        return None
    if hasattr(value, "date"):
        try:
            return value.date().isoformat()
        except TypeError:
            pass
    return str(value).strip()


def parse_employee_rows(rows):
    issues = []
    employees = []

    for row_number, row in enumerate(rows, start=2):
        missing_fields = [
            field_name for field_name in REQUIRED_EMPLOYEE_FIELDS
            if _normalize_text(row.get(field_name)) is None
        ]
        if missing_fields:
            issues.append({
                "code": "missing_required_field",
                "severity": "error",
                "row_number": row_number,
                "fields": missing_fields,
                "message": "Row {0}: missing required employee field(s): {1}.".format(
                    row_number, ", ".join(missing_fields)
                ),
            })
            continue

        employees.append(EmployeeRecord(
            employee_id=_normalize_text(row.get("employee_id")),
            manager_id=_normalize_text(row.get("manager_id")),
            full_name=_normalize_text(row.get("full_name")),
            job_title=_normalize_text(row.get("job_title")),
            department=_normalize_text(row.get("department")),
            location=_normalize_text(row.get("location")),
            level=_normalize_text(row.get("level")),
            employment_status=_normalize_text(row.get("employment_status")),
            email=_normalize_text(row.get("email")),
            team_name=_normalize_text(row.get("team_name")),
            photo_url=_normalize_text(row.get("photo_url")),
            start_date=_parse_date_like(row.get("start_date")),
            max_direct_reports=_parse_int(row.get("max_direct_reports"), "max_direct_reports", row_number),
            can_be_manager=_parse_bool(row.get("can_be_manager"), "can_be_manager", row_number, default=True),
            sort_order=_parse_int(row.get("sort_order"), "sort_order", row_number),
            row_number=row_number,
        ))

    if issues:
        raise EmployeeTreeValidationError(issues)
    return employees


def parse_constraint_rows(rows):
    constraints = []
    issues = []

    for row_number, row in enumerate(rows, start=2):
        manager_id = _normalize_text(row.get("manager_id"))
        if manager_id is None:
            issues.append({
                "code": "missing_manager_id",
                "severity": "error",
                "field": "manager_id",
                "row_number": row_number,
                "message": "Row {0}: constraints dataset is missing 'manager_id'.".format(row_number),
            })
            continue

        constraints.append(ManagerConstraint(
            manager_id=manager_id,
            max_direct_reports=_parse_int(row.get("max_direct_reports"), "max_direct_reports", row_number),
            allowed_departments=_parse_pipe_separated(row.get("allowed_departments")),
            allowed_locations=_parse_pipe_separated(row.get("allowed_locations")),
            min_child_level=_normalize_text(row.get("min_child_level")),
            max_child_level=_normalize_text(row.get("max_child_level")),
            rule_note=_normalize_text(row.get("rule_note")),
            row_number=row_number,
        ))

    if issues:
        raise EmployeeTreeValidationError(issues)
    return constraints
