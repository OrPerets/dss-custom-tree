from pathlib import Path

import pandas as pd

from employee_tree import (
    build_org_snapshot_document,
    export_move_log_rows,
    export_org_hierarchy_rows,
    materialize_org_tree_payload,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_DIR = REPO_ROOT / "demo"


def _load_rows(file_name):
    return pd.read_csv(str(DEMO_DIR / file_name)).to_dict("records")


def _sample_change_log():
    return [
        {
            "employee_id": "E009",
            "employee_name": "Tomer Niv",
            "old_manager_id": "E006",
            "old_manager_name": "Lior Shani",
            "new_manager_id": "E005",
            "new_manager_name": "Daniel Katz",
            "timestamp": "2026-04-20T10:30:00Z",
            "status": "pending_save",
            "validation_note": "Move validated against hierarchy, capacity, and manager-rule constraints.",
        }
    ]


def test_materialized_payload_applies_change_log():
    payload = materialize_org_tree_payload(
        _load_rows("employees-demo.csv"),
        _load_rows("manager-constraints-demo.csv"),
        change_log=_sample_change_log(),
    )

    nodes_by_id = {node["employee_id"]: node for node in payload["nodes"]}

    assert nodes_by_id["E009"]["manager_id"] == "E005"
    assert nodes_by_id["E005"]["children_ids"] == ["E007", "E009", "E008"]
    assert payload["change_log"][0]["employee_id"] == "E009"


def test_snapshot_document_contains_materialized_payload_and_metadata():
    snapshot = build_org_snapshot_document(
        _load_rows("employees-demo.csv"),
        _load_rows("manager-constraints-demo.csv"),
        change_log=_sample_change_log(),
        source={"mode": "demo", "employee_dataset": "demo/employees-demo.csv"},
        snapshot_name="org-tree-snapshot-demo.json",
        saved_at="2026-04-20T11:00:00Z",
    )

    assert snapshot["snapshot_version"] == 1
    assert snapshot["snapshot_name"] == "org-tree-snapshot-demo.json"
    assert snapshot["saved_at"] == "2026-04-20T11:00:00Z"
    assert snapshot["payload"]["meta"]["source"]["mode"] == "demo"
    assert snapshot["payload"]["nodes"][0]["employee_id"] == "E001"
    assert snapshot["payload"]["change_log"][0]["new_manager_id"] == "E005"


def test_export_org_hierarchy_rows_updates_manager_id():
    rows = export_org_hierarchy_rows(
        _load_rows("employees-demo.csv"),
        change_log=_sample_change_log(),
    )

    rows_by_id = {row["employee_id"]: row for row in rows}

    assert rows_by_id["E009"]["manager_id"] == "E005"
    assert rows_by_id["E008"]["manager_id"] == "E005"


def test_export_move_log_rows_is_tabular():
    rows = export_move_log_rows(_sample_change_log())

    assert rows == [
        {
            "sequence": 1,
            "employee_id": "E009",
            "employee_name": "Tomer Niv",
            "old_manager_id": "E006",
            "old_manager_name": "Lior Shani",
            "new_manager_id": "E005",
            "new_manager_name": "Daniel Katz",
            "timestamp": "2026-04-20T10:30:00Z",
            "status": "pending_save",
            "validation_note": "Move validated against hierarchy, capacity, and manager-rule constraints.",
        }
    ]
