# Employee Org Tree Editor

This repository is a Dataiku DSS plugin for loading, validating, visualizing, editing, saving, and exporting employee reporting hierarchies.

## What The Plugin Does

The webapp supports one org-tree workflow end to end:

- Load an employee dataset from DSS or the bundled demo files.
- Build a validated hierarchy from `employee_id` and `manager_id`.
- Render the hierarchy as an interactive employee card canvas.
- Inspect employee details, warnings, and manager-specific rules.
- Re-parent employees through drag-and-drop with backend validation.
- Save and reload org snapshots.
- Export the current hierarchy and move audit trail as CSV artifacts.

## Inputs

- Required employee dataset
- Optional manager-constraints dataset
- Optional snapshot folder for DSS persistence

Reference material:

- [docs/employee-tree-input-spec.md](docs/employee-tree-input-spec.md)
- [docs/employee-tree-mockup.md](docs/employee-tree-mockup.md)
- [demo/README.md](demo/README.md)

## Repository Guide

- [plugin.json](plugin.json) defines the plugin identity and release version.
- [webapps/employee-org-tree-editor](webapps/employee-org-tree-editor) contains the DSS webapp UI and backend entrypoint.
- [python-lib/employee_tree](python-lib/employee_tree) contains the reusable hierarchy parsing, validation, move simulation, and serialization logic.
- [code-env/python](code-env/python) contains the bundled plugin code environment definition.
- [tests/python/unit](tests/python/unit) covers validation, move simulation, persistence, and synthetic-org hardening.
- [docs/sprint-0-legacy-audit.md](docs/sprint-0-legacy-audit.md) records the legacy cleanup decisions that led to the current release shape.

## Local Validation

- `PYTHONPATH=python-lib pytest tests/python/unit`
- `node --check webapps/employee-org-tree-editor/app.js`
- `python3 -m py_compile python-lib/employee_tree/service.py webapps/employee-org-tree-editor/backend.py`
- `python3 /Users/orperets/.codex/plugins/cache/local-workspace/dataiku-plugin-developer/0.1.0/scripts/verify_dataiku_plugin.py .`

## Packaging

Use `make plugin` to build a ZIP under `dist/`. The Makefile now falls back to a filesystem ZIP when the repo is not inside a Git worktree, which keeps local DSS upload packaging working in this workspace.

## License

This project is distributed under the [LICENSE](LICENSE) file included in the repository.
