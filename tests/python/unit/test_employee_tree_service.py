from pathlib import Path

import pandas as pd

from employee_tree import build_org_tree_payload, validate_org_tree_rows


REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_DIR = REPO_ROOT / "demo"


def _load_rows(file_name):
    return pd.read_csv(str(DEMO_DIR / file_name)).to_dict("records")


def test_demo_inputs_validate():
    summary = validate_org_tree_rows(
        _load_rows("employees-demo.csv"),
        _load_rows("manager-constraints-demo.csv"),
    )

    assert summary == {
        "valid": True,
        "employee_count": 15,
        "constraint_count": 8,
        "root_employee_id": "E001",
    }


def test_demo_payload_is_normalized_and_stable():
    payload = build_org_tree_payload(
        _load_rows("employees-demo.csv"),
        _load_rows("manager-constraints-demo.csv"),
    )

    assert payload["meta"]["root_employee_id"] == "E001"
    assert payload["meta"]["employee_count"] == 15
    assert payload["meta"]["warning_count"] == 1
    assert payload["change_log"] == []

    nodes_by_id = {node["employee_id"]: node for node in payload["nodes"]}

    assert payload["nodes"][0]["employee_id"] == "E001"
    assert nodes_by_id["E001"]["children_ids"] == ["E002", "E003", "E004"]
    assert nodes_by_id["E001"]["direct_reports_count"] == 3
    assert nodes_by_id["E001"]["max_direct_reports"] == 4
    assert nodes_by_id["E013"]["children_ids"] == ["E014", "E015"]
    assert nodes_by_id["E013"]["direct_reports_count"] == 2
    assert nodes_by_id["E013"]["capacity_remaining"] == 0
    assert nodes_by_id["E013"]["warnings"][0]["code"] == "at_capacity"
    assert nodes_by_id["E013"]["manager_rule"]["rule_note"] == "People Ops manager is already at capacity"
    assert nodes_by_id["E009"]["current_manager_name"] == "Lior Shani"
    assert nodes_by_id["E007"]["can_be_manager"] is False
