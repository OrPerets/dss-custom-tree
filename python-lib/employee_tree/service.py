import re
from collections import defaultdict
from datetime import datetime, timezone

from employee_tree.exceptions import EmployeeTreeValidationError
from employee_tree.parser import parse_constraint_rows, parse_employee_rows


def validate_org_tree_rows(employee_rows, constraint_rows=None):
    employees = parse_employee_rows(employee_rows)
    constraints = parse_constraint_rows(constraint_rows or [])

    issues, employee_by_id, children_by_manager, constraint_by_manager, root_id = _collect_issues(
        employees, constraints
    )
    if issues:
        raise EmployeeTreeValidationError(issues)

    return {
        "valid": True,
        "employee_count": len(employee_by_id),
        "constraint_count": len(constraint_by_manager),
        "root_employee_id": root_id,
    }


def build_org_tree_payload(employee_rows, constraint_rows=None, change_log=None):
    employees = parse_employee_rows(employee_rows)
    constraints = parse_constraint_rows(constraint_rows or [])

    issues, employee_by_id, children_by_manager, constraint_by_manager, root_id = _collect_issues(
        employees, constraints
    )
    if issues:
        raise EmployeeTreeValidationError(issues)

    ordered_employee_ids = _traverse_tree(root_id, children_by_manager, employee_by_id)
    nodes = []

    for employee_id in ordered_employee_ids:
        employee = employee_by_id[employee_id]
        child_ids = [child.employee_id for child in children_by_manager.get(employee_id, [])]
        manager = employee_by_id.get(employee.manager_id)
        manager_constraint = constraint_by_manager.get(employee.employee_id)
        max_direct_reports = _resolve_max_direct_reports(employee, constraint_by_manager)
        warnings = _build_node_warnings(employee, len(child_ids), max_direct_reports)

        nodes.append({
            "employee_id": employee.employee_id,
            "manager_id": employee.manager_id,
            "full_name": employee.full_name,
            "job_title": employee.job_title,
            "department": employee.department,
            "location": employee.location,
            "level": employee.level,
            "employment_status": employee.employment_status,
            "email": employee.email,
            "team_name": employee.team_name,
            "photo_url": employee.photo_url,
            "start_date": employee.start_date,
            "current_manager_name": manager.full_name if manager else None,
            "direct_reports_count": len(child_ids),
            "max_direct_reports": max_direct_reports,
            "capacity_remaining": None if max_direct_reports is None else max_direct_reports - len(child_ids),
            "can_be_manager": employee.can_be_manager,
            "children_ids": child_ids,
            "warnings": warnings,
            "manager_rule": {
                "allowed_departments": list(manager_constraint.allowed_departments),
                "allowed_locations": list(manager_constraint.allowed_locations),
                "min_child_level": manager_constraint.min_child_level,
                "max_child_level": manager_constraint.max_child_level,
                "rule_note": manager_constraint.rule_note,
            } if manager_constraint else None,
        })

    warning_count = sum(len(node["warnings"]) for node in nodes)

    return {
        "meta": {
            "root_employee_id": root_id,
            "employee_count": len(nodes),
            "constraint_count": len(constraint_by_manager),
            "warning_count": warning_count,
        },
        "nodes": nodes,
        "change_log": list(change_log or []),
    }


def materialize_org_tree_payload(employee_rows, constraint_rows=None, change_log=None):
    current_change_log = list(change_log or [])
    current_rows = _apply_change_log(employee_rows, current_change_log)
    return build_org_tree_payload(
        current_rows,
        constraint_rows,
        change_log=current_change_log,
    )


def build_org_snapshot_document(employee_rows, constraint_rows=None, change_log=None, source=None, snapshot_name=None, saved_at=None):
    normalized_saved_at = saved_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = materialize_org_tree_payload(
        employee_rows,
        constraint_rows,
        change_log=change_log,
    )
    payload["meta"]["source"] = source or {}

    return {
        "snapshot_version": 1,
        "snapshot_name": snapshot_name,
        "saved_at": normalized_saved_at,
        "source": source or {},
        "payload": payload,
    }


def export_org_hierarchy_rows(employee_rows, change_log=None):
    return _apply_change_log(employee_rows, list(change_log or []))


def export_move_log_rows(change_log=None):
    rows = []

    for index, entry in enumerate(change_log or [], start=1):
        rows.append({
            "sequence": index,
            "employee_id": entry.get("employee_id"),
            "employee_name": entry.get("employee_name"),
            "old_manager_id": entry.get("old_manager_id"),
            "old_manager_name": entry.get("old_manager_name"),
            "new_manager_id": entry.get("new_manager_id"),
            "new_manager_name": entry.get("new_manager_name"),
            "timestamp": entry.get("timestamp"),
            "status": entry.get("status"),
            "validation_note": entry.get("validation_note"),
        })

    return rows


def simulate_org_tree_move(employee_rows, constraint_rows=None, employee_id=None, new_manager_id=None, change_log=None):
    if not employee_id:
        raise ValueError("Request must include 'employee_id'.")
    if not new_manager_id:
        raise ValueError("Request must include 'new_manager_id'.")

    current_change_log = list(change_log or [])
    current_rows = _apply_change_log(employee_rows, current_change_log)

    employees = parse_employee_rows(current_rows)
    constraints = parse_constraint_rows(constraint_rows or [])

    issues, employee_by_id, children_by_manager, constraint_by_manager, root_id = _collect_issues(
        employees, constraints
    )
    if issues:
        raise EmployeeTreeValidationError(issues)

    move_issues = _validate_proposed_move(
        employee_id=employee_id,
        new_manager_id=new_manager_id,
        employee_by_id=employee_by_id,
        children_by_manager=children_by_manager,
        constraint_by_manager=constraint_by_manager,
        root_id=root_id,
    )
    if move_issues:
        raise EmployeeTreeValidationError(move_issues)

    updated_rows = _apply_manager_change(current_rows, employee_id, new_manager_id)
    updated_change_log = current_change_log + [
        _build_change_log_entry(employee_id, new_manager_id, employee_by_id)
    ]

    return build_org_tree_payload(
        updated_rows,
        constraint_rows,
        change_log=updated_change_log,
    )


def _collect_issues(employees, constraints):
    issues = []
    employee_by_id = {}
    children_by_manager = defaultdict(list)
    constraint_by_manager = {}

    duplicate_employee_ids = _find_duplicates([employee.employee_id for employee in employees])
    for duplicate_employee_id in duplicate_employee_ids:
        rows = [employee.row_number for employee in employees if employee.employee_id == duplicate_employee_id]
        issues.append({
            "code": "duplicate_employee_id",
            "severity": "error",
            "employee_id": duplicate_employee_id,
            "row_numbers": rows,
            "message": "Employee '{0}' appears more than once in the employee dataset (rows: {1}).".format(
                duplicate_employee_id, ", ".join(str(row) for row in rows)
            ),
        })

    for employee in employees:
        employee_by_id.setdefault(employee.employee_id, employee)

    duplicate_constraint_ids = _find_duplicates([constraint.manager_id for constraint in constraints])
    for manager_id in duplicate_constraint_ids:
        rows = [constraint.row_number for constraint in constraints if constraint.manager_id == manager_id]
        issues.append({
            "code": "duplicate_manager_constraint",
            "severity": "error",
            "manager_id": manager_id,
            "row_numbers": rows,
            "message": "Manager '{0}' has more than one constraints row (rows: {1}).".format(
                manager_id, ", ".join(str(row) for row in rows)
            ),
        })

    for constraint in constraints:
        constraint_by_manager.setdefault(constraint.manager_id, constraint)

    root_ids = []
    for employee in employee_by_id.values():
        if employee.manager_id is None:
            root_ids.append(employee.employee_id)
            continue

        if employee.manager_id == employee.employee_id:
            issues.append({
                "code": "self_manager",
                "severity": "error",
                "employee_id": employee.employee_id,
                "row_number": employee.row_number,
                "message": "Employee '{0}' cannot manage themselves.".format(employee.employee_id),
            })
            continue

        if employee.manager_id not in employee_by_id:
            issues.append({
                "code": "missing_manager",
                "severity": "error",
                "employee_id": employee.employee_id,
                "manager_id": employee.manager_id,
                "row_number": employee.row_number,
                "message": "Employee '{0}' references missing manager '{1}'.".format(
                    employee.employee_id, employee.manager_id
                ),
            })
            continue

        children_by_manager[employee.manager_id].append(employee)

    if len(root_ids) != 1:
        issues.append({
            "code": "invalid_root_count",
            "severity": "error",
            "root_employee_ids": sorted(root_ids),
            "message": "Expected exactly one root employee with an empty manager_id, found {0}.".format(
                len(root_ids)
            ),
        })

    cycle_issues = _find_cycle_issues(employee_by_id)
    issues.extend(cycle_issues)

    for manager_id, children in children_by_manager.items():
        manager = employee_by_id[manager_id]
        effective_capacity = _resolve_max_direct_reports(manager, constraint_by_manager)
        if effective_capacity is not None and len(children) > effective_capacity:
            issues.append({
                "code": "manager_capacity_exceeded",
                "severity": "error",
                "manager_id": manager_id,
                "message": "Manager '{0}' has {1} direct reports but capacity is {2}.".format(
                    manager_id, len(children), effective_capacity
                ),
            })

        if not manager.can_be_manager and children:
            issues.append({
                "code": "manager_not_allowed",
                "severity": "error",
                "manager_id": manager_id,
                "message": "Manager '{0}' is marked as unable to manage direct reports.".format(manager_id),
            })

        if manager.employment_status.lower() != "active" and children:
            issues.append({
                "code": "inactive_manager",
                "severity": "error",
                "manager_id": manager_id,
                "message": "Manager '{0}' has direct reports but employment_status is '{1}'.".format(
                    manager_id, manager.employment_status
                ),
            })

    for manager_id, constraint in constraint_by_manager.items():
        if manager_id not in employee_by_id:
            issues.append({
                "code": "constraint_manager_missing",
                "severity": "error",
                "manager_id": manager_id,
                "row_number": constraint.row_number,
                "message": "Constraints row for manager '{0}' does not match any employee.".format(manager_id),
            })
            continue

        for child in children_by_manager.get(manager_id, []):
            issues.extend(_validate_child_against_constraint(child, constraint))

    root_id = root_ids[0] if len(root_ids) == 1 else None
    return issues, employee_by_id, _sort_children(children_by_manager), constraint_by_manager, root_id


def _validate_child_against_constraint(child, constraint):
    issues = []

    if constraint.allowed_departments and child.department not in constraint.allowed_departments:
        issues.append({
            "code": "department_not_allowed",
            "severity": "error",
            "employee_id": child.employee_id,
            "manager_id": constraint.manager_id,
            "message": "Employee '{0}' is in department '{1}', which is not allowed for manager '{2}'.".format(
                child.employee_id, child.department, constraint.manager_id
            ),
        })

    if constraint.allowed_locations and child.location not in constraint.allowed_locations:
        issues.append({
            "code": "location_not_allowed",
            "severity": "error",
            "employee_id": child.employee_id,
            "manager_id": constraint.manager_id,
            "message": "Employee '{0}' is in location '{1}', which is not allowed for manager '{2}'.".format(
                child.employee_id, child.location, constraint.manager_id
            ),
        })

    if constraint.min_child_level and _compare_levels(child.level, constraint.min_child_level) < 0:
        issues.append({
            "code": "child_level_below_minimum",
            "severity": "error",
            "employee_id": child.employee_id,
            "manager_id": constraint.manager_id,
            "message": "Employee '{0}' level '{1}' is below manager '{2}' minimum child level '{3}'.".format(
                child.employee_id, child.level, constraint.manager_id, constraint.min_child_level
            ),
        })

    if constraint.max_child_level and _compare_levels(child.level, constraint.max_child_level) > 0:
        issues.append({
            "code": "child_level_above_maximum",
            "severity": "error",
            "employee_id": child.employee_id,
            "manager_id": constraint.manager_id,
            "message": "Employee '{0}' level '{1}' exceeds manager '{2}' maximum child level '{3}'.".format(
                child.employee_id, child.level, constraint.manager_id, constraint.max_child_level
            ),
        })

    return issues


def _find_duplicates(values):
    seen = set()
    duplicates = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


def _find_cycle_issues(employee_by_id):
    issues = []
    seen_cycles = set()

    for start_employee_id in employee_by_id:
        chain = []
        positions = {}
        current_employee_id = start_employee_id

        while current_employee_id in employee_by_id:
            if current_employee_id in positions:
                cycle = chain[positions[current_employee_id]:] + [current_employee_id]
                cycle_key = tuple(cycle)
                if cycle_key not in seen_cycles:
                    seen_cycles.add(cycle_key)
                    issues.append({
                        "code": "hierarchy_cycle",
                        "severity": "error",
                        "employee_id": start_employee_id,
                        "cycle": cycle,
                        "message": "Cycle detected in the manager chain: {0}.".format(" -> ".join(cycle)),
                    })
                break

            positions[current_employee_id] = len(chain)
            chain.append(current_employee_id)
            manager_id = employee_by_id[current_employee_id].manager_id
            if manager_id is None:
                break
            current_employee_id = manager_id

    return issues


def _resolve_max_direct_reports(employee, constraint_by_manager):
    constraint = constraint_by_manager.get(employee.employee_id)
    if constraint and constraint.max_direct_reports is not None:
        return constraint.max_direct_reports
    return employee.max_direct_reports


def _apply_change_log(employee_rows, change_log):
    updated_rows = [dict(row) for row in employee_rows]
    rows_by_id = {}

    for row in updated_rows:
        employee_id = row.get("employee_id")
        if employee_id is not None:
            rows_by_id[str(employee_id).strip()] = row

    for entry in change_log:
        employee_id = entry.get("employee_id")
        new_manager_id = entry.get("new_manager_id")

        if not employee_id or employee_id not in rows_by_id:
            raise ValueError("Change log references unknown employee '{0}'.".format(employee_id))
        if not new_manager_id or new_manager_id not in rows_by_id:
            raise ValueError("Change log references unknown manager '{0}'.".format(new_manager_id))

        rows_by_id[employee_id]["manager_id"] = new_manager_id

    return updated_rows


def _apply_manager_change(employee_rows, employee_id, new_manager_id):
    updated_rows = [dict(row) for row in employee_rows]

    for row in updated_rows:
        if str(row.get("employee_id")).strip() == employee_id:
            row["manager_id"] = new_manager_id
            return updated_rows

    raise ValueError("Unknown employee '{0}'.".format(employee_id))


def _validate_proposed_move(employee_id, new_manager_id, employee_by_id, children_by_manager, constraint_by_manager, root_id):
    employee = employee_by_id.get(employee_id)
    new_manager = employee_by_id.get(new_manager_id)

    if employee is None:
        return [_build_move_issue(
            "move_employee_missing",
            "Employee '{0}' was not found in the current org tree.".format(employee_id),
            employee_id=employee_id,
        )]

    if new_manager is None:
        return [_build_move_issue(
            "move_manager_missing",
            "Manager '{0}' was not found in the current org tree.".format(new_manager_id),
            employee_id=employee_id,
            manager_id=new_manager_id,
        )]

    if employee.employee_id == root_id or employee.manager_id is None:
        return [_build_move_issue(
            "root_move_forbidden",
            "Root employee '{0}' cannot be moved under another manager.".format(employee.employee_id),
            employee_id=employee.employee_id,
            manager_id=new_manager.employee_id,
        )]

    if employee.manager_id == new_manager.employee_id:
        return [_build_move_issue(
            "no_manager_change",
            "Employee '{0}' already reports to manager '{1}'.".format(employee.employee_id, new_manager.employee_id),
            employee_id=employee.employee_id,
            manager_id=new_manager.employee_id,
        )]

    if employee.employee_id == new_manager.employee_id:
        return [_build_move_issue(
            "self_manager",
            "Employee '{0}' cannot report to themselves.".format(employee.employee_id),
            employee_id=employee.employee_id,
            manager_id=new_manager.employee_id,
        )]

    if _is_descendant(employee.employee_id, new_manager.employee_id, children_by_manager):
        return [_build_move_issue(
            "move_would_create_cycle",
            "Employee '{0}' cannot be moved under '{1}' because that manager is inside their subtree.".format(
                employee.employee_id, new_manager.employee_id
            ),
            employee_id=employee.employee_id,
            manager_id=new_manager.employee_id,
        )]

    if not new_manager.can_be_manager:
        return [_build_move_issue(
            "manager_not_allowed",
            "Manager '{0}' is marked as unable to manage direct reports.".format(new_manager.employee_id),
            employee_id=employee.employee_id,
            manager_id=new_manager.employee_id,
        )]

    if new_manager.employment_status.lower() != "active":
        return [_build_move_issue(
            "inactive_manager",
            "Manager '{0}' cannot receive direct reports because employment_status is '{1}'.".format(
                new_manager.employee_id, new_manager.employment_status
            ),
            employee_id=employee.employee_id,
            manager_id=new_manager.employee_id,
        )]

    effective_capacity = _resolve_max_direct_reports(new_manager, constraint_by_manager)
    future_direct_reports = len(children_by_manager.get(new_manager.employee_id, [])) + 1
    if effective_capacity is not None and future_direct_reports > effective_capacity:
        return [_build_move_issue(
            "manager_capacity_exceeded",
            "Manager '{0}' would have {1} direct reports after this move but capacity is {2}.".format(
                new_manager.employee_id, future_direct_reports, effective_capacity
            ),
            employee_id=employee.employee_id,
            manager_id=new_manager.employee_id,
        )]

    constraint = constraint_by_manager.get(new_manager.employee_id)
    if constraint:
        return _validate_child_against_constraint(employee, constraint)

    return []


def _is_descendant(root_employee_id, target_employee_id, children_by_manager):
    stack = [root_employee_id]

    while stack:
        employee_id = stack.pop()
        for child in children_by_manager.get(employee_id, []):
            if child.employee_id == target_employee_id:
                return True
            stack.append(child.employee_id)

    return False


def _build_move_issue(code, message, employee_id=None, manager_id=None):
    issue = {
        "code": code,
        "severity": "error",
        "message": message,
    }
    if employee_id is not None:
        issue["employee_id"] = employee_id
    if manager_id is not None:
        issue["manager_id"] = manager_id
    return issue


def _build_change_log_entry(employee_id, new_manager_id, employee_by_id):
    employee = employee_by_id[employee_id]
    old_manager = employee_by_id.get(employee.manager_id)
    new_manager = employee_by_id[new_manager_id]

    return {
        "employee_id": employee.employee_id,
        "employee_name": employee.full_name,
        "old_manager_id": employee.manager_id,
        "old_manager_name": old_manager.full_name if old_manager else None,
        "new_manager_id": new_manager.employee_id,
        "new_manager_name": new_manager.full_name,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "pending_save",
        "validation_note": "Move validated against hierarchy, capacity, and manager-rule constraints.",
    }


def _build_node_warnings(employee, direct_reports_count, max_direct_reports):
    warnings = []

    if max_direct_reports is not None and max_direct_reports > 0 and direct_reports_count >= max_direct_reports:
        warnings.append({
            "code": "at_capacity",
            "severity": "warning",
            "message": "Manager is at direct-report capacity ({0}/{1}).".format(
                direct_reports_count, max_direct_reports
            ),
        })

    if employee.employment_status.lower() != "active":
        warnings.append({
            "code": "employment_status_attention",
            "severity": "warning",
            "message": "Employee status is '{0}'.".format(employee.employment_status),
        })

    return warnings


def _sort_children(children_by_manager):
    sorted_children = {}
    for manager_id, children in children_by_manager.items():
        sorted_children[manager_id] = sorted(
            children,
            key=lambda child: (
                child.sort_order if child.sort_order is not None else 10 ** 9,
                child.full_name.lower(),
                child.employee_id,
            ),
        )
    return sorted_children


def _traverse_tree(root_id, children_by_manager, employee_by_id):
    ordered = []
    stack = [root_id]

    while stack:
        employee_id = stack.pop()
        ordered.append(employee_id)
        children = list(children_by_manager.get(employee_id, []))
        for child in reversed(children):
            stack.append(child.employee_id)

    if len(ordered) != len(employee_by_id):
        missing_ids = sorted(set(employee_by_id) - set(ordered))
        raise EmployeeTreeValidationError([{
            "code": "disconnected_hierarchy",
            "severity": "error",
            "employee_ids": missing_ids,
            "message": "The hierarchy is disconnected. Unreachable employees: {0}.".format(", ".join(missing_ids)),
        }])

    return ordered


def _compare_levels(left, right):
    left_key = _level_sort_key(left)
    right_key = _level_sort_key(right)
    if left_key < right_key:
        return -1
    if left_key > right_key:
        return 1
    return 0


def _level_sort_key(level):
    match = re.search(r"(\d+)", level or "")
    if match:
        return int(match.group(1))
    return level or ""
