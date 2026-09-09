# Amdocs Workforce Org Designer

This repository is a Dataiku DSS plugin for loading, validating, visualizing, editing, saving, and exporting employee reporting hierarchies from DSS datasets.

## What The Plugin Does

The webapp supports one org-tree workflow end to end:

- Load an employee dataset from DSS.
- Build a validated hierarchy from `employee_id` and `manager_id`.
- Render the hierarchy as an interactive employee card canvas.
- Inspect employee details, warnings, and manager-specific rules.
- Re-parent employees through drag-and-drop with backend validation.
- Save and reload org snapshots.
- Export the current hierarchy and move audit trail as CSV artifacts.

## Organization workspace

The chart starts with three reporting levels. Expand a manager’s direct reports or choose **All levels** to explore further. Search includes people in collapsed teams. Select a person for employee details, reporting rules, or a validated manager change.

**Changes & versions** contains recent changes, saved versions and the source controls. **Save version** requires a configured baseline folder. **Export** downloads the current hierarchy.

- [UI review and verification](docs/ui-review-2026-09-07.md)
- [Local interactive preview](demo/README.md)

## Inputs

Select the workforce dataset you already created in your Dataiku project. The plugin has no direct DWH/Snowflake connection or SQL dependency. The Snowflake starter below is an optional, separate preparation aid.

- Required employee dataset
- Optional manager-constraints dataset
- Optional snapshot folder for DSS persistence

Since version 2.2.0, only `employee_id` and `manager_id` columns are required to display a valid hierarchy (manager ID is blank only for the root). Missing names use `Employee <ID>`; other incomplete details show placeholders and review notices. Column casing and surrounding whitespace are accepted. Missing information required to approve a move still blocks that move. See the input specification for status, eligibility and rule behavior.

To update an installed copy, upload the 2.2.0 plugin ZIP using the same plugin ID, restart the webapp backend, keep your prepared dataset selected as **Input workforce dataset**, and refresh from source. Local source changes do not update the installed DSS copy automatically.

Reference material:

- [docs/employee-tree-input-spec.md](docs/employee-tree-input-spec.md)
- [docs/employee-tree-mockup.md](docs/employee-tree-mockup.md)
- [Snowflake DWH.HR mapping, extraction SQL and validation](integrations/snowflake/README.md)

## Repository Guide

- [plugin.json](plugin.json) defines the plugin identity and package version.
- [webapps/employee-org-tree-editor](webapps/employee-org-tree-editor) contains the DSS webapp UI and backend entrypoint.
- [python-lib/employee_tree](python-lib/employee_tree) contains the reusable hierarchy parsing, validation, move simulation, and serialization logic.
- [code-env/python](code-env/python) contains the bundled plugin code environment definition.
- [tests/python/unit](tests/python/unit) covers validation, move simulation, persistence, and synthetic-org hardening.
- [docs/sprint-0-legacy-audit.md](docs/sprint-0-legacy-audit.md) records the legacy cleanup decisions behind the current implementation.

## Local Validation

- `PYTHONPATH=python-lib pytest tests/python/unit`
- `node --check webapps/employee-org-tree-editor/app.js`
- `python3 -m py_compile python-lib/employee_tree/service.py webapps/employee-org-tree-editor/backend.py`
- `python3 plugins/dataiku-plugin-developer/scripts/verify_dataiku_plugin.py .`

## Packaging

Use `make plugin` to build a ZIP under `dist/`. The Makefile now falls back to a filesystem ZIP when the repo is not inside a Git worktree, which keeps local DSS upload packaging working in this workspace.

## License

This project is distributed under the [LICENSE](LICENSE) file included in the repository.
