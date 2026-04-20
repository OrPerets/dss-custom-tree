# Employee Org Tree Rewrite Tasks

## Objective

Rebuild this repository end-to-end as a Dataiku DSS plugin for visualizing and editing an employee org tree. The current decision-tree plugin is reference material only. Keep the Dataiku plugin structure as a guide, but replace the product logic, data model, backend API, UI flows, and user-facing copy with employee-org-tree behavior.

## Working Rules For The Agent

- Treat the current decision-tree code as legacy reference, not as the implementation baseline.
- Reuse only the Dataiku plugin structure and any generic utility patterns that still make sense after review.
- Do not keep decision-tree concepts in the final product: no targets, splits, probabilities, scoring, evaluation, histograms, or sunburst mode.
- Keep the DSS entrypoints thin and move reusable business logic into `python-lib/`.
- Build the new webapp around employee hierarchy editing, constraint validation, and drag-and-drop re-parenting.
- Keep the scope webapp-first. Legacy custom recipes can be removed, disabled, or archived unless a later sprint explicitly reintroduces a recipe for export or validation.

## Target Product

The final plugin should let a user:

- Load an employee dataset from Dataiku.
- Build a hierarchy from `employee_id` / `manager_id`.
- Render the org tree visually.
- Inspect each employee node.
- Drag an employee onto another employee to propose a manager change.
- Validate the move against hierarchy and business constraints.
- Save or export the modified org structure and a move log.

## Core Functional Requirements

- One row in the dataset represents one employee.
- Exactly zero or one manager per employee.
- One root employee is allowed per organization snapshot.
- No hierarchy cycles.
- Drag-and-drop must support re-parenting an employee under a new manager.
- Failed moves must return clear validation errors.
- The UI must show direct reports count and capacity.
- The UI must expose unsaved changes and allow reset/save/export.

## Node Content Requirements

Each rendered node should include at least:

- Employee full name
- Job title
- Department
- Location
- Level or grade
- Employee ID
- Current manager name or ID
- Direct reports count
- Max direct reports capacity
- Employment status badge

Optional nice-to-have fields:

- Email
- Start date / tenure
- Photo URL or initials avatar
- Team name
- Warnings badge when the node is violating a rule

## Recommended Plugin Shape

- `plugin.json`: rename metadata from decision-tree language to employee-org-tree language.
- `webapps/<new-webapp-id>/webapp.json`: narrow config surface to the employee dataset, optional constraints dataset, and optional snapshot folder.
- `webapps/<new-webapp-id>/app.js`: rewrite client logic from scratch around org-tree state and drag/drop.
- `webapps/<new-webapp-id>/body.html`: replace the current split-editor layout with org-tree layout.
- `webapps/<new-webapp-id>/style.css`: replace styling with card-based org-chart UI.
- `webapps/<new-webapp-id>/backend.py`: replace endpoints with employee/constraint/tree operations.
- `python-lib/employee_tree/`: add pure-Python modules for parsing, validation, move simulation, serialization, and export.
- `tests/python/unit/`: replace decision-tree unit tests with org-tree parser and validator tests.

## Data Inputs

Use two inputs:

- Required employee dataset
- Optional manager-constraints dataset

See:

- `docs/employee-tree-input-spec.md`
- `docs/employee-tree-mockup.md`
- `demo/employees-demo.csv`
- `demo/manager-constraints-demo.csv`
- `demo/README.md`

## Sprint Plan

## Sprint 0 - Baseline Cleanup And Naming

Goal: remove decision-tree identity from the plugin and define the new boundaries.

Todo:

- [x] Rename plugin metadata and descriptions in `plugin.json`.
- [x] Rename the webapp component ID to an employee-org-tree name.
- [x] Audit legacy assets and decide per item: delete, archive, or replace.
- [x] Mark `custom-recipes/decision-tree-builder-*` as out of scope for the first delivery.
- [x] Update `README.md` to describe the new plugin rather than the decision-tree template.


Done when:

- No user-facing label still says decision tree.
- The repo has a single clear product identity.

## Sprint 1 - Domain Model And Backend Skeleton

Goal: establish the employee hierarchy model independently from the current tree implementation.

Todo:

- [x] Create new modules under `python-lib/employee_tree/`.
- [x] Implement employee record parsing from Dataiku dataframe rows.
- [x] Implement hierarchy builder from `employee_id` and `manager_id`.
- [x] Implement validation for duplicate employees, missing managers, multiple roots, and cycles.
- [x] Implement capacity validation using `max_direct_reports`.
- [x] Implement optional rule checks from the constraints dataset.
- [x] Define a normalized JSON payload for the frontend.
- [x] Add unit tests for parsing and validation.

Done when:

- Backend can load the demo datasets and produce a stable org-tree JSON document.
- Invalid datasets fail with specific, actionable error messages.

## Sprint 2 - Webapp Bootstrap And Loading Flow

Goal: replace the landing flow with employee data loading instead of tree creation/loading by target column.

Todo:

- [x] Rewrite `webapp.json` params for employee use cases.
- [x] Build a landing screen that lets the user select the employee dataset and optional constraints dataset.
- [x] Add a demo mode that loads the sample files or sample JSON when running outside DSS constraints.
- [x] Add backend endpoints such as `get-datasets`, `get-schema`, `load-org-tree`, and `validate-input`.
- [x] Surface backend loading errors clearly in the UI.

Done when:

- A user can select the demo employee dataset and reach the org-tree canvas without any decision-tree terminology.

## Sprint 3 - Org Tree Visualization

Goal: render the employee hierarchy as a clean, navigable org-tree view.

Todo:

- [x] Implement a tree canvas using D3 or another lightweight layout library already compatible with DSS.
- [x] Render nodes as employee cards rather than abstract circles or split boxes.
- [x] Add zoom, pan, fit-to-screen, and selected-node focus.
- [x] Add side panel details for the selected employee.
- [x] Show rule badges and capacity information on nodes or in the details panel.
- [x] Add search and filter support by name, department, location, and status.

Done when:

- The demo dataset renders as a readable org chart on a laptop screen.
- Selecting a node updates a detail panel with the required fields.

## Sprint 4 - Drag And Drop Re-Parenting

Goal: let users move employees under another manager safely.

Todo:

- [x] Add drag handles or drag behavior for employee nodes.
- [x] Define drop targets and hover states.
- [x] Simulate the move in the backend before committing UI state.
- [x] Reject moves that create cycles, exceed manager capacity, violate scope rules, or move the root under a child.
- [x] Add user-facing confirmation and validation messages.
- [x] Track unsaved moves in a change log.

Done when:

- Valid moves update the tree immediately.
- Invalid moves keep the tree unchanged and explain why the move failed.

## Sprint 5 - Save, Export, And Audit Trail

Goal: persist the edited org structure in a way that works well in Dataiku projects.

Todo:

- [x] Decide the persistence format: folder snapshot JSON, exported dataset, or both.
- [x] Implement save/load for org snapshots.
- [x] Implement export of the current hierarchy back to a flat table.
- [x] Implement export of a move log with `employee_id`, `old_manager_id`, `new_manager_id`, timestamp, and validation notes.
- [x] Add dirty-state handling and reset-to-last-saved behavior.

Done when:

- A user can save the modified org tree, reload it, and export the final hierarchy plus move history.

## Sprint 6 - Hardening, Packaging, And Release

Goal: make the plugin upload-ready for DSS.

Todo:

- [x] Add plugin code environment files if extra dependencies are required.
- [x] Add tests for move validation and serialization.
- [x] Test with larger synthetic orgs for performance.
- [x] Verify frontend behavior on narrow and wide screens.
- [x] Remove obsolete decision-tree docs, screenshots, and dead code.
- [x] Bump plugin version and verify packaging structure.

Done when:

- The plugin can be packaged cleanly and installed as an employee org-tree plugin.

## Recommended Backend API

The new backend should expose endpoints close to the following:

- `GET /get-datasets`
- `GET /get-schema/<dataset>`
- `POST /load-org-tree`
- `POST /validate-input`
- `POST /move-employee`
- `POST /save-snapshot`
- `POST /load-snapshot`
- `POST /export-flat-table`
- `GET /get-change-log`

## Acceptance Criteria For The First Usable Milestone

- The plugin loads the demo employee dataset.
- The tree renders with employee cards.
- Selecting a node shows the required node fields.
- One valid drag-and-drop move succeeds.
- One invalid drag-and-drop move is rejected for capacity or hierarchy reasons.
- The edited hierarchy can be exported as a flat table.

## Open Decisions The Agent Should Resolve Early

- Whether to keep AngularJS for state management or switch to vanilla JS while keeping DSS-compatible dependencies light.
- Whether the first release should support only one org root or multiple independent roots grouped under a virtual root.
- Whether snapshot storage should live only in a folder or also as a Dataiku dataset export.
- Whether manager-specific rules beyond direct-report capacity should be implemented in v1 or hidden behind optional config.

## Recommended Default Decisions

- Keep one real root employee in v1.
- Use employee dataset plus optional constraints dataset in v1.
- Save snapshots to a folder and export the flattened hierarchy as a dataset-compatible CSV/JSON artifact.
- Implement direct-report capacity, no-cycle, active-manager, department-scope, and location-scope checks in v1.
