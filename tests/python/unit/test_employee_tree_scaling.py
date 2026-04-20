import json
import time

from employee_tree import (
    build_org_snapshot_document,
    build_org_tree_payload,
    export_move_log_rows,
    export_org_hierarchy_rows,
    simulate_org_tree_move,
)


def _build_synthetic_rows(employee_count=2500, branching_factor=4):
    rows = []

    for index in range(1, employee_count + 1):
        manager_id = None if index == 1 else "E{0:05d}".format(((index - 2) // branching_factor) + 1)
        rows.append({
            "employee_id": "E{0:05d}".format(index),
            "manager_id": manager_id,
            "full_name": "Employee {0}".format(index),
            "job_title": "Software Engineer",
            "department": "Engineering",
            "location": "Tel Aviv",
            "level": "L3",
            "employment_status": "Active",
            "email": "employee{0}@example.com".format(index),
            "team_name": "Platform",
            "photo_url": "",
            "start_date": "2024-01-01",
            "max_direct_reports": 6,
            "can_be_manager": True,
        })

    return rows


def test_large_synthetic_org_build_move_and_export_are_fast_enough():
    employee_rows = _build_synthetic_rows()

    build_started = time.perf_counter()
    payload = build_org_tree_payload(employee_rows, [])
    build_elapsed = time.perf_counter() - build_started

    move_started = time.perf_counter()
    moved_payload = simulate_org_tree_move(
        employee_rows,
        [],
        employee_id="E02000",
        new_manager_id="E00050",
        change_log=[],
    )
    move_elapsed = time.perf_counter() - move_started

    snapshot_started = time.perf_counter()
    snapshot = build_org_snapshot_document(
        employee_rows,
        [],
        change_log=moved_payload["change_log"],
        source={"mode": "synthetic"},
        snapshot_name="synthetic-org.json",
        saved_at="2026-04-20T12:00:00Z",
    )
    hierarchy_rows = export_org_hierarchy_rows(employee_rows, moved_payload["change_log"])
    move_log_rows = export_move_log_rows(moved_payload["change_log"])
    snapshot_elapsed = time.perf_counter() - snapshot_started

    assert payload["meta"]["employee_count"] == 2500
    assert moved_payload["change_log"][0]["employee_id"] == "E02000"
    assert len(hierarchy_rows) == 2500
    assert move_log_rows[0]["new_manager_id"] == "E00050"
    assert snapshot["payload"]["meta"]["source"]["mode"] == "synthetic"

    assert build_elapsed < 1.5
    assert move_elapsed < 1.5
    assert snapshot_elapsed < 1.5


def test_snapshot_document_is_json_serializable():
    employee_rows = _build_synthetic_rows(employee_count=32, branching_factor=3)
    moved_payload = simulate_org_tree_move(
        employee_rows,
        [],
        employee_id="E00020",
        new_manager_id="E00005",
        change_log=[],
    )

    snapshot = build_org_snapshot_document(
        employee_rows,
        [],
        change_log=moved_payload["change_log"],
        source={"mode": "synthetic"},
        snapshot_name="roundtrip.json",
        saved_at="2026-04-20T12:15:00Z",
    )

    roundtrip = json.loads(json.dumps(snapshot))

    assert roundtrip["snapshot_name"] == "roundtrip.json"
    assert roundtrip["payload"]["change_log"][0]["employee_id"] == "E00020"
    assert roundtrip["payload"]["meta"]["employee_count"] == 32
