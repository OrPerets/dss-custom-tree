# Employee Org Tree Mockup

## Primary Screen

```text
+--------------------------------------------------------------------------------------+
| Employee Org Tree                                             Search [__________]   |
| Dataset: employees-demo      Constraints: manager-rules       Zoom  Fit  Save Export |
+-----------------------------+--------------------------------------------------------+
| Filters                     |                                                        |
| - Department                |                    ORG TREE CANVAS                      |
| - Location                  |                                                        |
| - Status                    |          [ Nora Levin | CEO | Exec | L1 ]             |
| - Only warnings             |                Reports 3 / 4                           |
|                             |                       |                                 |
| Validation / Change Log     |        +--------------+---------------+                |
| - 1 pending move            |        |                              |                |
| - 0 blocking errors         | [ Amir Cohen ]                [ Maya Azulay ]          |
|                             | VP Engineering                VP Sales                 |
| Selected Employee           | Reports 2 / 3                 Reports 1 / 3            |
| Name: Amir Cohen            |        |                              |                |
| Title: VP Engineering       |   [ Daniel Katz ]                [ Shira Azul ]        |
| Dept: Engineering           |   Eng Manager                    Sales Manager         |
| Location: Tel Aviv          |   Reports 2 / 3                  Reports 2 / 2         |
| Level: L2                   |                                                        |
| Manager: Nora Levin         |                                                        |
| Reports: 2 / 3              |                                                        |
| Status: active              |                                                        |
| Warnings: none              |                                                        |
+-----------------------------+--------------------------------------------------------+
```

## Node Design

Each node card should show:

- Full name
- Job title
- Department
- Level
- Direct reports count and max capacity
- Status badge

Recommended visual treatments:

- Use color accents by department or validation state.
- Show warning or error badge when the node is over capacity or violates a rule.
- Use a visible drag affordance so the card does not feel accidentally draggable.

## Drag And Drop Behavior

- Dragging starts from a handle or the full card.
- Potential managers highlight on hover.
- Invalid targets show a blocked state before drop.
- On drop, the backend validates the move before the UI finalizes it.
- The selected employee panel updates with old manager, new manager, and validation status.

## Demo Scenarios

Use the demo CSV files to verify these flows:

- Valid move: move `E009` from `E006` to `E005`.
- Invalid move: move `E014` under `E010` because the department rule should fail.
- Invalid move: move `E002` under `E005` because that creates a cycle.
- Capacity warning: attempt to move another employee under `E013` when its capacity is already full.

## Save And Export Expectations

- `Save snapshot` writes the current org-tree JSON plus change log.
- `Export hierarchy` writes a flat table with updated `manager_id`.
- `Export moves` writes one row per accepted move.

