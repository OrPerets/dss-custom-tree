from pathlib import Path

import pandas as pd
import pytest

from employee_tree import build_org_tree_payload, EmployeeTreeValidationError


REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_DIR = REPO_ROOT / "demo"


def _load_rows(file_name):
    return pd.read_csv(str(DEMO_DIR / file_name)).to_dict("records")


def _expect_error(employee_rows, constraint_rows=None):
    with pytest.raises(EmployeeTreeValidationError) as error:
        build_org_tree_payload(employee_rows, constraint_rows or [])
    return error.value


def test_duplicate_employees_are_rejected():
    employee_rows = _load_rows("employees-demo.csv")
    duplicate_row = dict(employee_rows[0])
    duplicate_row["full_name"] = "Nora Levin Duplicate"
    employee_rows.append(duplicate_row)

    error = _expect_error(employee_rows, _load_rows("manager-constraints-demo.csv"))

    assert error.issues[0]["code"] == "duplicate_employee_id"
    assert "appears more than once" in error.issues[0]["message"]


def test_missing_manager_is_rejected():
    employee_rows = _load_rows("employees-demo.csv")
    employee_rows[1]["manager_id"] = "E999"

    error = _expect_error(employee_rows, _load_rows("manager-constraints-demo.csv"))

    assert error.issues[0]["code"] == "missing_manager"
    assert "references missing manager 'E999'" in error.issues[0]["message"]


def test_multiple_roots_are_rejected():
    employee_rows = _load_rows("employees-demo.csv")
    employee_rows[1]["manager_id"] = None

    error = _expect_error(employee_rows, _load_rows("manager-constraints-demo.csv"))

    assert error.issues[0]["code"] == "invalid_root_count"
    assert "Expected exactly one root employee" in error.issues[0]["message"]


def test_cycles_are_rejected():
    employee_rows = _load_rows("employees-demo.csv")
    employee_rows[1]["manager_id"] = "E005"

    error = _expect_error(employee_rows, _load_rows("manager-constraints-demo.csv"))

    assert error.issues[0]["code"] == "hierarchy_cycle"
    assert "Cycle detected" in error.issues[0]["message"]


def test_capacity_violations_are_rejected():
    employee_rows = _load_rows("employees-demo.csv")
    constraints_rows = _load_rows("manager-constraints-demo.csv")
    for row in constraints_rows:
        if row["manager_id"] == "E013":
            row["max_direct_reports"] = 1

    error = _expect_error(employee_rows, constraints_rows)

    assert error.issues[0]["code"] == "manager_capacity_exceeded"
    assert "capacity is 1" in error.issues[0]["message"]


def test_manager_scope_rules_are_rejected():
    employee_rows = _load_rows("employees-demo.csv")
    constraints_rows = _load_rows("manager-constraints-demo.csv")
    for row in employee_rows:
        if row["employee_id"] == "E014":
            row["manager_id"] = "E010"

    error = _expect_error(employee_rows, constraints_rows)

    issue_codes = [issue["code"] for issue in error.issues]

    assert "department_not_allowed" in issue_codes
    assert any("not allowed for manager 'E010'" in issue["message"] for issue in error.issues)
