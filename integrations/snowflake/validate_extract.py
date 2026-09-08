#!/usr/bin/env python3
"""Validate a candidate CSV before exporting the exact workforce input columns.

Uses the existing plugin validator. Does not connect to Snowflake or Dataiku.
"""
import argparse
import csv
import json
from pathlib import Path
import sys


EMPLOYEE_COLUMNS = (
    "employee_id", "manager_id", "full_name", "job_title", "department",
    "location", "level", "employment_status", "email", "team_name",
    "photo_url", "start_date", "max_direct_reports", "can_be_manager", "sort_order",
)


def read_csv(path, required_columns):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError("{} has duplicate column names".format(path.name))
        missing = sorted(set(required_columns) - set(headers))
        if missing:
            raise ValueError("{} is missing columns: {}".format(path.name, ", ".join(missing)))
        rows = list(reader)
        if any(None in row or any(value is None for value in row.values()) for row in rows):
            raise ValueError("{} contains rows with the wrong number of cells".format(path.name))
        return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", type=Path, help="CSV exported from 02_employee_candidates.sql")
    parser.add_argument("--rules", type=Path, help="Optional manager rules CSV")
    parser.add_argument("--output", type=Path, help="New workforce CSV; created only after all checks pass")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    library = here / "python-lib"  # Included in the standalone handoff ZIP.
    if not library.is_dir():
        library = here.parents[1] / "python-lib"  # Repository layout.
    sys.path.insert(0, str(library))
    try:
        from employee_tree import EmployeeTreeValidationError, validate_org_tree_rows
    except ImportError as error:
        parser.exit(2, "Plugin validation library and pandas are required: {}\n".format(error))

    try:
        rows = read_csv(args.candidates, EMPLOYEE_COLUMNS + ("source_issue_count", "source_issues"))
        rules = read_csv(args.rules, ("manager_id",)) if args.rules else []
        issues = []
        for number, row in enumerate(rows, start=2):
            if row["source_issue_count"].strip() != "0" or row["source_issues"].strip():
                issues.append({"row_number": number, "code": "unresolved_source_issues",
                               "details": row["source_issues"]})
            if row["can_be_manager"].strip().lower() not in {
                "true", "false", "1", "0", "yes", "no", "y", "n"
            }:
                issues.append({"row_number": number, "code": "unknown_manager_eligibility"})
        if issues:
            print(json.dumps({"valid": False, "issue_count": len(issues), "issues": issues[:50]}, indent=2))
            return 1

        summary = validate_org_tree_rows(rows, rules)
        if args.output:
            # Exclusive create prevents accidental replacement of a previous accepted export.
            with args.output.open("x", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=EMPLOYEE_COLUMNS, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
            summary["output"] = str(args.output.resolve())
        print(json.dumps(summary, indent=2))
        return 0
    except EmployeeTreeValidationError as error:
        print(json.dumps(error.to_dict(), indent=2))
        return 1
    except (OSError, ValueError) as error:
        print(json.dumps({"valid": False, "error": str(error)}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
