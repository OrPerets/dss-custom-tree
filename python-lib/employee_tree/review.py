"""Explicit read-only visualization of an incomplete source hierarchy.

Display groups are never returned by source export, move or snapshot operations.
"""
from collections import defaultdict

from employee_tree.exceptions import EmployeeTreeValidationError
from employee_tree.parser import normalize_column_names, parse_constraint_rows, parse_employee_rows
from employee_tree.service import _collect_issues, build_org_tree_payload


REVIEWABLE_ISSUES = frozenset(("missing_manager", "invalid_root_count"))


def missing_manager_report(employee_rows):
    employees = parse_employee_rows(employee_rows)
    employee_ids = {employee.employee_id for employee in employees}
    missing = defaultdict(list)
    for employee in employees:
        if employee.manager_id is not None and employee.manager_id not in employee_ids:
            missing[employee.manager_id].append(employee.employee_id)
    return [{"missing_manager_id": manager_id,
             "direct_reports_in_dataset": len(reports),
             "employee_ids": "|".join(sorted(reports))}
            for manager_id, reports in sorted(missing.items())]


def build_org_tree_review_payload(employee_rows, constraint_rows=None):
    rows = [normalize_column_names(row) for row in employee_rows]
    employees = parse_employee_rows(rows)
    constraints = parse_constraint_rows(constraint_rows or [])
    issues, _, _, _, _ = _collect_issues(employees, constraints)
    blockers = [issue for issue in issues if issue["code"] not in REVIEWABLE_ISSUES]
    if blockers:
        raise EmployeeTreeValidationError(blockers)
    if not employees:
        raise EmployeeTreeValidationError([{
            "code": "empty_employee_dataset", "severity": "error",
            "message": "The selected employee dataset has no rows to review.",
        }])
    if not issues:
        return build_org_tree_payload(rows, constraint_rows)

    report = missing_manager_report(rows)
    missing_ids = {item["missing_manager_id"] for item in report}
    occupied_ids = {e.employee_id for e in employees} | missing_ids
    display_root = "__org_tree_review__"
    while display_root in occupied_ids:
        display_root += "_"
    original_parents = {e.employee_id: e.manager_id for e in employees}
    display_rows = [dict(row) for row in rows]
    for row, employee in zip(display_rows, employees):
        if employee.manager_id is None:
            row["manager_id"] = display_root
    for missing_id in sorted(missing_ids):
        display_rows.append({
            "employee_id": missing_id, "manager_id": display_root,
            "full_name": "Missing manager {0}".format(missing_id),
            "job_title": "No employee row in this dataset", "can_be_manager": None,
        })
    display_rows.append({
        "employee_id": display_root, "manager_id": None,
        "full_name": "Imported workforce", "job_title": "Review groups · not a reporting line",
        "can_be_manager": None,
    })
    payload = build_org_tree_payload(display_rows, constraint_rows)
    for node in payload["nodes"]:
        node_id = node["employee_id"]
        node["is_virtual_root"] = node_id == display_root
        node["is_missing_manager"] = node_id in missing_ids
        node["display_only"] = node["is_virtual_root"] or node["is_missing_manager"]
        if node["display_only"]:
            node["manager_id"] = None
            node["can_be_manager"] = False
            node["current_manager_name"] = None
            node["warnings"] = [] if node["is_virtual_root"] else [{
                "code": "missing_manager_record", "severity": "warning",
                "message": "This manager ID is referenced by employees but has no row in the source dataset. Name and reporting line are unknown.",
            }]
        else:
            # Preserve the real parent field; children_ids supply display grouping only.
            node["manager_id"] = original_parents[node_id]
            if node["manager_id"] is None:
                node["current_manager_name"] = None
            elif node["manager_id"] in missing_ids:
                node["warnings"].append({
                    "code": "missing_manager_record", "severity": "warning",
                    "message": "Manager '{0}' has no employee row in the source dataset. The original reporting ID is preserved.".format(node["manager_id"]),
                })
    payload["meta"].update({
        "review_only": True,
        "employee_count": len(employees),
        "missing_manager_count": len(report),
        "affected_employee_count": sum(item["direct_reports_in_dataset"] for item in report),
        "source_root_count": sum(e.manager_id is None for e in employees),
        "warning_count": sum(len(n["warnings"]) for n in payload["nodes"] if not n["display_only"]),
    })
    return payload
