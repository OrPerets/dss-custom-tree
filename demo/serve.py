"""Run the real webapp against bundled sample data on localhost, without DSS."""

import argparse
import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from flask import Response, send_from_directory


ROOT = Path(__file__).resolve().parents[1]
WEBAPP = ROOT / "webapps" / "employee-org-tree-editor"
sys.path.insert(0, str(ROOT / "python-lib"))
spec = importlib.util.spec_from_file_location("org_tree_demo_backend", WEBAPP / "backend.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)
backend.dataiku = None


def load_demo_dataset(name):
    files = {
        "Sample workforce": ROOT / "demo" / "employees-demo.csv",
        "Sample manager rules": ROOT / "demo" / "manager-constraints-demo.csv",
    }
    if name not in files:
        raise ValueError("The local preview only supports bundled sample datasets.")
    return backend._load_demo_records(files[name])


backend._load_dataset_records = load_demo_dataset
app = backend.app


@app.route("/")
def index():
    html = (WEBAPP / "body.html").read_text()
    html = html.replace('<link rel="stylesheet" href="/static/public/styles/1.0.0/fonts.css" />', "")
    html = html.replace('<link rel="stylesheet" href="/static/public/styles/1.0.0/variables.css" />', "")
    html = html.replace("</head>", """
        <link rel="stylesheet" href="/preview/style.css">
        <script>
        window.dataiku = {getWebAppConfig: function() { return {
            default_employee_dataset: "Sample workforce",
            default_constraints_dataset: "Sample manager rules",
            snapshot_folder: "Local preview snapshots"
        }; }};
        window.getWebAppBackendUrl = function(path) { return "/" + path; };
        </script>
        <script defer src="/preview/app.js"></script>
    </head>""")
    return Response(html, mimetype="text/html")


@app.route("/preview/<filename>")
def assets(filename):
    if filename not in {"app.js", "style.css"}:
        return "Not found", 404
    return send_from_directory(WEBAPP, filename)


@app.route("/plugins/employee-org-tree-visualizer/resource/angular.min.js")
def angular():
    return send_from_directory(ROOT / "resource", "angular.min.js")


@app.route("/favicon.ico")
def favicon():
    return "", 204


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="org-tree-preview-") as storage:
        backend.REPO_ROOT = Path(storage)
        backend.DEMO_SNAPSHOTS_PATH = Path(storage) / "snapshots"
        app.run(host="127.0.0.1", port=args.port, debug=False)
