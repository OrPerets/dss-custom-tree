"""Prepared DSS datasets may have incomplete attributes but must retain valid edges."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from employee_tree import (
    EmployeeTreeValidationError, build_org_snapshot_document, build_org_tree_payload,
    export_org_hierarchy_rows, materialize_org_tree_payload, simulate_org_tree_move,
)


def workforce():
    return [dict(employee_id=employee_id, manager_id=manager_id, full_name=name,
                 job_title="Engineer", department="Engineering", location="Israel",
                 level="L2", employment_status="active", can_be_manager=True)
            for employee_id, manager_id, name in
            [("001", None, "Root"), ("002", "001", "Alex"), ("003", "001", "Sam")]]


@pytest.mark.parametrize("blank", [None, "  ", float("nan"), pd.NA])
def test_missing_details_load_with_one_review_notice_and_no_source_mutation(blank):
    rows = workforce()
    for field in ("full_name", "job_title", "department", "location", "level"):
        rows[1][field] = blank
    payload = build_org_tree_payload(rows)
    node = next(n for n in payload["nodes"] if n["employee_id"] == "002")
    assert node["full_name"] == "Employee 002"
    assert node["job_title"] is None and node["department"] is None and node["level"] is None
    assert len(node["warnings"]) == 1
    assert node["warnings"][0]["fields"] == ["full_name", "job_title", "department", "location", "level"]
    assert rows[1]["full_name"] is blank


def test_two_hierarchy_columns_suffice_for_viewing():
    rows = [{"employee_id": "001", "manager_id": None},
            {"employee_id": "002", "manager_id": "001"}]
    payload = build_org_tree_payload(rows)
    assert len(payload["nodes"]) == 2
    assert payload["nodes"][0]["children_ids"] == ["002"]
    assert all(n["employment_status"] is None for n in payload["nodes"])


@pytest.mark.parametrize("field,code", [("employment_status", "unknown_manager_status"),
                                        ("can_be_manager", "unknown_manager_eligibility")])
def test_unknown_manager_policy_allows_viewing_but_blocks_new_reports(field, code):
    rows = workforce()
    rows[0][field] = None  # Existing parent can still be viewed.
    rows[2][field] = None
    assert len(build_org_tree_payload(rows)["nodes"]) == 3
    with pytest.raises(EmployeeTreeValidationError) as error:
        simulate_org_tree_move(rows, employee_id="002", new_manager_id="003")
    assert error.value.issues[0]["code"] == code


@pytest.mark.parametrize("field,rule", [
    ("department", {"allowed_departments": "Engineering"}),
    ("location", {"allowed_locations": "Israel"}),
    ("level", {"min_child_level": "L1"}),
    ("level", {"max_child_level": "L9"}),
])
def test_missing_rule_inputs_warn_on_existing_edges_and_block_proposed_edges(field, rule):
    rows = workforce()
    rows[1][field] = None
    rules = [dict(rule, manager_id="001"), dict(rule, manager_id="003")]
    payload = build_org_tree_payload(rows, rules)
    child = next(n for n in payload["nodes"] if n["employee_id"] == "002")
    assert any(w["code"] == "missing_rule_field" for w in child["warnings"])
    with pytest.raises(EmployeeTreeValidationError) as error:
        simulate_org_tree_move(rows, rules, employee_id="002", new_manager_id="003")
    assert error.value.issues[0]["code"] == "missing_rule_field"
    assert error.value.issues[0]["field"] == field


def test_case_normalization_survives_move_replay_snapshot_and_export():
    source = workforce()
    source[1]["full_name"] = None
    rows = [{" " + key.upper() + " ": value for key, value in row.items()} for row in source]
    original = deepcopy(rows)
    moved = simulate_org_tree_move(rows, employee_id="002", new_manager_id="003")
    replayed = materialize_org_tree_payload(rows, change_log=moved["change_log"])
    snapshot = build_org_snapshot_document(rows, change_log=moved["change_log"])
    assert replayed["nodes"] == snapshot["payload"]["nodes"]
    child = next(n for n in replayed["nodes"] if n["employee_id"] == "002")
    assert child["manager_id"] == "003" and child["full_name"] == "Employee 002"
    exported = export_org_hierarchy_rows(rows, moved["change_log"])
    assert exported[1]["full_name"] is None and exported[1]["manager_id"] == "003"
    assert rows == original


@pytest.mark.parametrize("alter,code", [
    (lambda r: r[0].update(EMPLOYEE_ID="different"), "ambiguous_column_name"),
    (lambda r: r[1].pop("manager_id"), "missing_manager_column"),
    (lambda r: r[1].update(employee_id=None), "missing_required_field"),
    (lambda r: r[1].update(employee_id="001"), "duplicate_employee_id"),
    (lambda r: r[1].update(manager_id="missing"), "missing_manager"),
    (lambda r: r[1].update(manager_id=None), "invalid_root_count"),
    (lambda r: (r[1].update(manager_id="003"), r[2].update(manager_id="002")), "hierarchy_cycle"),
    (lambda r: r[0].update(can_be_manager=False), "manager_not_allowed"),
    (lambda r: r[0].update(employment_status="inactive"), "inactive_manager"),
])
def test_structural_and_known_policy_errors_still_block(alter, code):
    rows = workforce()
    rows[1]["full_name"] = None
    alter(rows)
    with pytest.raises(EmployeeTreeValidationError) as error:
        build_org_tree_payload(rows)
    assert code in {issue["code"] for issue in error.value.issues}


def test_dss_project_dataset_route_load_move_export_and_snapshot(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("partial_input_backend", root / "webapps/employee-org-tree-editor/backend.py")
    backend = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)
    rows = workforce()
    rows[1]["full_name"] = rows[1]["department"] = None
    rows = [{key.upper(): value for key, value in row.items()} for row in rows]
    reads = []

    class Dataset:
        def __init__(self, name):
            assert name == "prepared_workforce"
            reads.append(name)

        def iter_rows(self):
            return iter(deepcopy(rows))

    backend.dataiku = SimpleNamespace(Dataset=Dataset)
    client = backend.app.test_client()
    source = {"employee_dataset": "prepared_workforce"}
    response = client.post("/load-org-tree", json=source)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["meta"]["source"]["mode"] == "dataiku"
    assert payload["nodes"][0]["employee_id"] == "001"
    assert client.post("/validate-input", json=source).status_code == 200
    moved = client.post("/move-employee", json=dict(source, employee_id="002", new_manager_id="003"))
    assert moved.status_code == 200
    draft = dict(source, change_log=moved.get_json()["change_log"])
    exported = client.post("/export-flat-table", json=draft)
    assert exported.status_code == 200
    assert "Employee 002" not in exported.get_json()["content"]
    saved = []
    monkeypatch.setattr(backend, "_write_snapshot_document", lambda folder, name, document:
                        (saved.append(document) or {"path": name, "storage_label": "test"}))
    assert client.post("/save-snapshot", json=draft).status_code == 200
    assert saved[0]["payload"]["nodes"] == moved.get_json()["nodes"]
    assert len(reads) == 5
