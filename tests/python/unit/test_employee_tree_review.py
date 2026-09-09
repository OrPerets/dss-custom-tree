from copy import deepcopy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from employee_tree import (EmployeeTreeValidationError, build_org_snapshot_document,
                           export_org_hierarchy_rows, simulate_org_tree_move, validate_org_tree_rows)
from employee_tree.review import build_org_tree_review_payload, missing_manager_report


def incomplete_rows():
    return [dict(employee_id=e, manager_id=m, full_name=e, employment_status="active")
            for e, m in [("001", None), ("002", "009"), ("003", "009"),
                         ("004", "002"), ("005", "008")]]


def test_review_preserves_people_and_original_parent_ids():
    rows = incomplete_rows()
    before = deepcopy(rows)
    payload = build_org_tree_review_payload(rows)
    nodes = {n["employee_id"]: n for n in payload["nodes"]}
    assert payload["meta"]["review_only"] is True
    assert payload["meta"]["employee_count"] == 5
    assert payload["meta"]["missing_manager_count"] == 2
    assert payload["meta"]["affected_employee_count"] == 3
    assert len(payload["nodes"]) == 8
    assert nodes["009"]["is_missing_manager"] and nodes["009"]["can_be_manager"] is False
    assert nodes["009"]["children_ids"] == ["002", "003"]
    assert nodes["002"]["manager_id"] == "009" and nodes["002"]["children_ids"] == ["004"]
    assert nodes["001"]["manager_id"] is None and nodes["001"]["current_manager_name"] is None
    assert rows == before
    assert export_org_hierarchy_rows(rows) == before
    assert payload["change_log"] == []


def test_report_groups_references_and_preserves_string_ids():
    assert missing_manager_report(incomplete_rows()) == [
        {"missing_manager_id": "008", "direct_reports_in_dataset": 1, "employee_ids": "005"},
        {"missing_manager_id": "009", "direct_reports_in_dataset": 2, "employee_ids": "002|003"},
    ]


@pytest.mark.parametrize("rows", [
    [{"employee_id": "1", "manager_id": "9"}],
    [{"employee_id": "1", "manager_id": None}, {"employee_id": "2", "manager_id": None}],
    [{"employee_id": "__org_tree_review__", "manager_id": "9"}],
])
def test_review_handles_no_source_root_multiple_roots_and_internal_id_collision(rows):
    payload = build_org_tree_review_payload(rows)
    source_ids = {row["employee_id"] for row in rows}
    assert payload["meta"]["root_employee_id"] not in source_ids
    assert sum(not n["display_only"] for n in payload["nodes"]) == len(rows)
    assert len({n["employee_id"] for n in payload["nodes"]}) == len(payload["nodes"])


@pytest.mark.parametrize("alter,expected", [
    (lambda r: r.append(dict(r[0])), "duplicate_employee_id"),
    (lambda r: r[1].update(manager_id="002"), "self_manager"),
    (lambda r: r[1].update(manager_id="004"), "hierarchy_cycle"),
])
def test_review_does_not_hide_structural_ambiguity(alter, expected):
    rows = incomplete_rows()
    alter(rows)
    with pytest.raises(EmployeeTreeValidationError) as error:
        build_org_tree_review_payload(rows)
    assert expected in {i["code"] for i in error.value.issues}


def test_strict_validation_moves_and_snapshots_still_reject_missing_managers():
    rows = incomplete_rows()
    for operation in [lambda: validate_org_tree_rows(rows),
                      lambda: simulate_org_tree_move(rows, employee_id="003", new_manager_id="001"),
                      lambda: build_org_snapshot_document(rows)]:
        with pytest.raises(EmployeeTreeValidationError) as error:
            operation()
        assert "missing_manager" in {i["code"] for i in error.value.issues}


def test_completing_source_restores_normal_editor_payload():
    rows = incomplete_rows()
    rows.extend([dict(employee_id=e, manager_id="001", full_name=e, employment_status="active")
                 for e in ("008", "009")])
    payload = build_org_tree_review_payload(rows)
    assert not payload["meta"].get("review_only")
    assert payload["meta"]["employee_count"] == 7
    assert simulate_org_tree_move(rows, employee_id="003", new_manager_id="001")["change_log"]


def test_review_endpoint_reads_project_dataset_and_export_excludes_display_rows():
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("review_backend", root / "webapps/employee-org-tree-editor/backend.py")
    backend = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)
    rows = incomplete_rows()
    backend.dataiku = SimpleNamespace(Dataset=lambda name: SimpleNamespace(iter_rows=lambda: iter(rows)))
    client = backend.app.test_client()
    source = {"employee_dataset": "prepared_workforce"}
    strict = client.post("/validate-input", json=source)
    assert strict.status_code == 400 and strict.get_json()["review_available"]
    assert "3 employees reference 2 managers" in strict.get_json()["message"]
    review = client.post("/review-org-tree", json=source)
    assert review.status_code == 200 and review.get_json()["meta"]["review_only"]
    report = client.post("/export-missing-managers", json=source).get_json()
    assert report["row_count"] == 2 and "002|003" in report["content"]
    export = client.post("/export-flat-table", json=source).get_json()
    assert export["row_count"] == 5 and "Imported workforce" not in export["content"]
    assert "Missing manager" not in export["content"]
    assert client.post("/save-snapshot", json=source).status_code == 400
    assert client.post("/move-employee", json=dict(source, employee_id="003", new_manager_id="001")).status_code == 400
    rows.clear()
    empty = client.post("/validate-input", json=source)
    assert empty.status_code == 400 and not empty.get_json()["review_available"]


def test_large_forest_review_keeps_all_source_rows():
    rows = [dict(employee_id=str(i), manager_id="M" + str(i % 200), employment_status="active")
            for i in range(24000)]
    payload = build_org_tree_review_payload(rows)
    assert payload["meta"]["employee_count"] == 24000
    assert payload["meta"]["missing_manager_count"] == 200
    assert payload["meta"]["affected_employee_count"] == 24000
    assert len(payload["nodes"]) == 24201
