import csv
import io
import json
import logging
import re
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request

from employee_tree import (
    build_org_snapshot_document,
    build_org_tree_payload,
    EmployeeTreeValidationError,
    export_move_log_rows,
    export_org_hierarchy_rows,
    materialize_org_tree_payload,
    simulate_org_tree_move,
    validate_org_tree_rows,
)

try:
    import dataiku
except ImportError:
    dataiku = None


try:
    app
except NameError:
    app = Flask(__name__)


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="ORGTREE %(levelname)s - %(message)s")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_EMPLOYEES_PATH = REPO_ROOT / "demo" / "employees-demo.csv"
DEMO_CONSTRAINTS_PATH = REPO_ROOT / "demo" / "manager-constraints-demo.csv"
DEMO_SNAPSHOTS_PATH = REPO_ROOT / "demo" / "snapshots"


def _load_demo_records(path):
    return pd.read_csv(str(path)).to_dict("records")


def _get_payload():
    return request.get_json(silent=True) or {}


def _get_value(payload, snake_case_key, camel_case_key=None):
    if snake_case_key in payload:
        return payload[snake_case_key]
    if camel_case_key and camel_case_key in payload:
        return payload[camel_case_key]
    return None


def _load_dataset_records(dataset_name):
    if dataiku is None:
        raise RuntimeError("Dataiku runtime is not available. Use demo mode outside DSS.")
    return dataiku.Dataset(dataset_name).get_dataframe().to_dict("records")


def _resolve_input_rows(payload):
    use_demo = bool(payload.get("use_demo") or payload.get("useDemo"))
    if use_demo:
        employee_rows = _load_demo_records(DEMO_EMPLOYEES_PATH)
        load_demo_constraints = payload.get("load_demo_constraints", payload.get("loadDemoConstraints", True))
        constraint_rows = _load_demo_records(DEMO_CONSTRAINTS_PATH) if load_demo_constraints else []
        return {
            "employee_rows": employee_rows,
            "constraint_rows": constraint_rows,
            "source": {
                "mode": "demo",
                "employee_dataset": "demo/employees-demo.csv",
                "constraints_dataset": "demo/manager-constraints-demo.csv" if load_demo_constraints else None,
            },
        }

    employee_dataset = _get_value(payload, "employee_dataset", "employeeDataset")
    constraints_dataset = _get_value(payload, "constraints_dataset", "constraintsDataset")
    if not employee_dataset:
        raise ValueError("Request must include 'employee_dataset' or set 'use_demo' to true.")

    return {
        "employee_rows": _load_dataset_records(employee_dataset),
        "constraint_rows": _load_dataset_records(constraints_dataset) if constraints_dataset else [],
        "source": {
            "mode": "dataiku",
            "employee_dataset": employee_dataset,
            "constraints_dataset": constraints_dataset,
        },
    }


def _schema_from_records(records):
    if not records:
        return []
    return sorted(records[0].keys())


def _validation_error_response(error):
    return jsonify(error.to_dict()), 400


def _bad_request_response(message, error_code="bad_request"):
    return jsonify({
        "error": error_code,
        "message": message,
    }), 400


def _unexpected_error_response(error):
    logger.error(traceback.format_exc())
    return jsonify({
        "error": "backend_error",
        "message": str(error),
    }), 500


def _utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _snapshot_folder_id(payload):
    return _get_value(payload, "snapshot_folder", "snapshotFolder")


def _slugify_snapshot_name(snapshot_name):
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", (snapshot_name or "").strip()).strip("-")
    if not normalized:
        normalized = "org-tree-snapshot-{0}".format(datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    if not normalized.endswith(".json"):
        normalized += ".json"
    return normalized


def _resolve_snapshot_storage(snapshot_folder_id):
    if dataiku is not None:
        if not snapshot_folder_id:
            raise ValueError("Configure 'snapshot_folder' in the webapp settings before saving or loading snapshots in DSS.")
        return {
            "mode": "dataiku_folder",
            "folder_id": snapshot_folder_id,
            "label": snapshot_folder_id,
        }

    DEMO_SNAPSHOTS_PATH.mkdir(parents=True, exist_ok=True)
    return {
        "mode": "demo_local_folder",
        "path": DEMO_SNAPSHOTS_PATH,
        "label": str(DEMO_SNAPSHOTS_PATH),
    }


def _snapshot_summary_from_document(path, snapshot_document):
    payload = snapshot_document.get("payload", {})
    return {
        "path": path,
        "name": snapshot_document.get("snapshot_name") or Path(path).name,
        "saved_at": snapshot_document.get("saved_at"),
        "employee_count": payload.get("meta", {}).get("employee_count"),
        "change_log_count": len(payload.get("change_log", [])),
        "source_label": (snapshot_document.get("source") or {}).get("employee_dataset"),
    }


def _write_snapshot_document(snapshot_folder_id, snapshot_file_name, snapshot_document):
    storage = _resolve_snapshot_storage(snapshot_folder_id)

    if storage["mode"] == "dataiku_folder":
        folder = dataiku.Folder(storage["folder_id"])
        stream = io.BytesIO(json.dumps(snapshot_document, indent=2, sort_keys=True).encode("utf-8"))
        folder.upload_stream(snapshot_file_name, stream)
        return {
            "path": snapshot_file_name,
            "storage_label": storage["label"],
        }

    snapshot_path = storage["path"] / snapshot_file_name
    snapshot_path.write_text(json.dumps(snapshot_document, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "path": str(snapshot_path.relative_to(REPO_ROOT)),
        "storage_label": storage["label"],
    }


def _read_snapshot_document(snapshot_folder_id, snapshot_path):
    storage = _resolve_snapshot_storage(snapshot_folder_id)

    if storage["mode"] == "dataiku_folder":
        folder = dataiku.Folder(storage["folder_id"])
        return folder.read_json(snapshot_path)

    local_path = (REPO_ROOT / snapshot_path).resolve()
    if not local_path.exists():
        raise ValueError("Snapshot '{0}' was not found.".format(snapshot_path))
    return json.loads(local_path.read_text(encoding="utf-8"))


def _list_snapshot_documents(snapshot_folder_id):
    storage = _resolve_snapshot_storage(snapshot_folder_id)
    snapshots = []

    if storage["mode"] == "dataiku_folder":
        folder = dataiku.Folder(storage["folder_id"])
        for path in sorted(folder.list_paths_in_partition(), reverse=True):
            if not path.endswith(".json"):
                continue
            snapshots.append(_snapshot_summary_from_document(path, folder.read_json(path)))
        return snapshots

    for snapshot_file in sorted(DEMO_SNAPSHOTS_PATH.glob("*.json"), reverse=True):
        snapshots.append(_snapshot_summary_from_document(
            str(snapshot_file.relative_to(REPO_ROOT)),
            json.loads(snapshot_file.read_text(encoding="utf-8")),
        ))
    return snapshots


def _csv_payload(rows):
    output = io.StringIO()
    fieldnames = list(rows[0].keys()) if rows else []
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    if fieldnames:
        writer.writeheader()
        writer.writerows(rows)
    return output.getvalue()


@app.route("/health")
def health():
    return jsonify(status="ok")


@app.route("/get-datasets")
def get_datasets():
    try:
        datasets = dataiku.Dataset.list() if dataiku is not None else []
        return jsonify(
            mode="dataiku" if dataiku is not None else "demo",
            datasets=datasets,
            demoDatasets=[
                "demo/employees-demo.csv",
                "demo/manager-constraints-demo.csv",
            ],
        )
    except Exception as error:
        return _unexpected_error_response(error)


@app.route("/get-schema/<path:dataset_name>")
def get_schema(dataset_name):
    try:
        if dataset_name == "demo/employees-demo.csv":
            return jsonify(columns=_schema_from_records(_load_demo_records(DEMO_EMPLOYEES_PATH)))
        if dataset_name == "demo/manager-constraints-demo.csv":
            return jsonify(columns=_schema_from_records(_load_demo_records(DEMO_CONSTRAINTS_PATH)))
        if dataiku is None:
            raise RuntimeError("Dataiku runtime is not available. Use one of the demo datasets.")
        schema = dataiku.Dataset(dataset_name).read_schema()
        return jsonify(columns=[column["name"] for column in schema])
    except Exception as error:
        return _unexpected_error_response(error)


@app.route("/validate-input", methods=["POST"])
def validate_input():
    try:
        resolved_input = _resolve_input_rows(_get_payload())
        summary = validate_org_tree_rows(
            resolved_input["employee_rows"],
            resolved_input["constraint_rows"],
        )
        summary["source"] = resolved_input["source"]
        return jsonify(summary)
    except EmployeeTreeValidationError as error:
        return _validation_error_response(error)
    except Exception as error:
        return _unexpected_error_response(error)


@app.route("/load-org-tree", methods=["POST"])
def load_org_tree():
    try:
        resolved_input = _resolve_input_rows(_get_payload())
        payload = build_org_tree_payload(
            resolved_input["employee_rows"],
            resolved_input["constraint_rows"],
        )
        payload["meta"]["source"] = resolved_input["source"]
        return jsonify(payload)
    except EmployeeTreeValidationError as error:
        return _validation_error_response(error)
    except Exception as error:
        return _unexpected_error_response(error)


@app.route("/move-employee", methods=["POST"])
def move_employee():
    try:
        request_payload = _get_payload()
        resolved_input = _resolve_input_rows(request_payload)
        payload = simulate_org_tree_move(
            resolved_input["employee_rows"],
            resolved_input["constraint_rows"],
            employee_id=_get_value(request_payload, "employee_id", "employeeId"),
            new_manager_id=_get_value(request_payload, "new_manager_id", "newManagerId"),
            change_log=request_payload.get("change_log", request_payload.get("changeLog", [])),
        )
        payload["meta"]["source"] = resolved_input["source"]
        return jsonify(payload)
    except EmployeeTreeValidationError as error:
        return _validation_error_response(error)
    except ValueError as error:
        return _bad_request_response(str(error))
    except Exception as error:
        return _unexpected_error_response(error)


@app.route("/list-snapshots", methods=["POST"])
def list_snapshots():
    try:
        request_payload = _get_payload()
        storage = _resolve_snapshot_storage(_snapshot_folder_id(request_payload))
        return jsonify(
            snapshots=_list_snapshot_documents(_snapshot_folder_id(request_payload)),
            storage_label=storage["label"],
        )
    except ValueError as error:
        return _bad_request_response(str(error))
    except Exception as error:
        return _unexpected_error_response(error)


@app.route("/save-snapshot", methods=["POST"])
def save_snapshot():
    try:
        request_payload = _get_payload()
        resolved_input = _resolve_input_rows(request_payload)
        change_log = request_payload.get("change_log", request_payload.get("changeLog", []))
        saved_at = _utc_now()
        snapshot_document = build_org_snapshot_document(
            resolved_input["employee_rows"],
            resolved_input["constraint_rows"],
            change_log=change_log,
            source=resolved_input["source"],
            snapshot_name=_slugify_snapshot_name(_get_value(request_payload, "snapshot_name", "snapshotName")),
            saved_at=saved_at,
        )
        snapshot_ref = _write_snapshot_document(
            _snapshot_folder_id(request_payload),
            snapshot_document["snapshot_name"],
            snapshot_document,
        )
        return jsonify(
            snapshot={
                "path": snapshot_ref["path"],
                "name": snapshot_document["snapshot_name"],
                "saved_at": saved_at,
                "storage_label": snapshot_ref["storage_label"],
            },
            payload=snapshot_document["payload"],
        )
    except EmployeeTreeValidationError as error:
        return _validation_error_response(error)
    except ValueError as error:
        return _bad_request_response(str(error))
    except Exception as error:
        return _unexpected_error_response(error)


@app.route("/load-snapshot", methods=["POST"])
def load_snapshot():
    try:
        request_payload = _get_payload()
        snapshot_path = _get_value(request_payload, "snapshot_path", "snapshotPath")
        if not snapshot_path:
            raise ValueError("Choose a saved snapshot before loading.")
        snapshot_document = _read_snapshot_document(
            _snapshot_folder_id(request_payload),
            snapshot_path,
        )
        payload = snapshot_document.get("payload")
        if not payload:
            raise ValueError("Snapshot '{0}' does not contain an org-tree payload.".format(snapshot_path))
        return jsonify(
            snapshot=_snapshot_summary_from_document(snapshot_path, snapshot_document),
            payload=payload,
        )
    except ValueError as error:
        return _bad_request_response(str(error))
    except Exception as error:
        return _unexpected_error_response(error)


@app.route("/export-flat-table", methods=["POST"])
def export_flat_table():
    try:
        request_payload = _get_payload()
        resolved_input = _resolve_input_rows(request_payload)
        rows = export_org_hierarchy_rows(
            resolved_input["employee_rows"],
            change_log=request_payload.get("change_log", request_payload.get("changeLog", [])),
        )
        return jsonify(
            filename="employee-org-hierarchy-{0}.csv".format(datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")),
            content_type="text/csv",
            content=_csv_payload(rows),
            row_count=len(rows),
        )
    except ValueError as error:
        return _bad_request_response(str(error))
    except Exception as error:
        return _unexpected_error_response(error)


@app.route("/export-move-log", methods=["POST"])
def export_move_log():
    try:
        request_payload = _get_payload()
        rows = export_move_log_rows(request_payload.get("change_log", request_payload.get("changeLog", [])))
        return jsonify(
            filename="employee-org-move-log-{0}.csv".format(datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")),
            content_type="text/csv",
            content=_csv_payload(rows),
            row_count=len(rows),
        )
    except ValueError as error:
        return _bad_request_response(str(error))
    except Exception as error:
        return _unexpected_error_response(error)
