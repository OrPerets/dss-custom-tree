from pathlib import Path

import pandas as pd
import pytest

from employee_tree import EmployeeTreeValidationError, simulate_org_tree_move


REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_DIR = REPO_ROOT / "demo"


def _load_rows(file_name):
    return pd.read_csv(str(DEMO_DIR / file_name)).to_dict("records")


def test_valid_move_updates_tree_and_change_log():
    payload = simulate_org_tree_move(
        _load_rows("employees-demo.csv"),
        _load_rows("manager-constraints-demo.csv"),
        employee_id="E009",
        new_manager_id="E005",
        change_log=[],
    )

    nodes_by_id = {node["employee_id"]: node for node in payload["nodes"]}

    assert nodes_by_id["E009"]["manager_id"] == "E005"
    assert nodes_by_id["E009"]["current_manager_name"] == "Daniel Katz"
    assert nodes_by_id["E005"]["children_ids"] == ["E007", "E009", "E008"]
    assert nodes_by_id["E006"]["children_ids"] == []
    assert len(payload["change_log"]) == 1
    assert payload["change_log"][0]["employee_id"] == "E009"
    assert payload["change_log"][0]["old_manager_id"] == "E006"
    assert payload["change_log"][0]["new_manager_id"] == "E005"


def test_move_rejects_scope_rule_violation():
    with pytest.raises(EmployeeTreeValidationError) as error:
        simulate_org_tree_move(
            _load_rows("employees-demo.csv"),
            _load_rows("manager-constraints-demo.csv"),
            employee_id="E014",
            new_manager_id="E010",
            change_log=[],
        )

    issue_codes = [issue["code"] for issue in error.value.issues]

    assert "department_not_allowed" in issue_codes


def test_move_rejects_cycle():
    with pytest.raises(EmployeeTreeValidationError) as error:
        simulate_org_tree_move(
            _load_rows("employees-demo.csv"),
            _load_rows("manager-constraints-demo.csv"),
            employee_id="E002",
            new_manager_id="E005",
            change_log=[],
        )

    assert error.value.issues[0]["code"] == "move_would_create_cycle"


def test_move_rejects_root_reassignment():
    with pytest.raises(EmployeeTreeValidationError) as error:
        simulate_org_tree_move(
            _load_rows("employees-demo.csv"),
            _load_rows("manager-constraints-demo.csv"),
            employee_id="E001",
            new_manager_id="E002",
            change_log=[],
        )

    assert error.value.issues[0]["code"] == "root_move_forbidden"


def test_move_rejects_capacity_violation():
    constraints_rows = _load_rows("manager-constraints-demo.csv")
    for row in constraints_rows:
        if row["manager_id"] == "E005":
            row["max_direct_reports"] = 2

    with pytest.raises(EmployeeTreeValidationError) as error:
        simulate_org_tree_move(
            _load_rows("employees-demo.csv"),
            constraints_rows,
            employee_id="E009",
            new_manager_id="E005",
            change_log=[],
        )

    assert error.value.issues[0]["code"] == "manager_capacity_exceeded"


def test_move_replays_existing_change_log_before_validating():
    payload = simulate_org_tree_move(
        _load_rows("employees-demo.csv"),
        _load_rows("manager-constraints-demo.csv"),
        employee_id="E012",
        new_manager_id="E003",
        change_log=[
            {
                "employee_id": "E009",
                "new_manager_id": "E005",
            }
        ],
    )

    nodes_by_id = {node["employee_id"]: node for node in payload["nodes"]}

    assert nodes_by_id["E009"]["manager_id"] == "E005"
    assert nodes_by_id["E012"]["manager_id"] == "E003"
    assert len(payload["change_log"]) == 2
