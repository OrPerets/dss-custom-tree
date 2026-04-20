# Demo Data Notes

## Files

- `employees-demo.csv`: flat employee hierarchy input
- `manager-constraints-demo.csv`: optional manager-specific validation rules
- `snapshots/`: created on demand when Sprint 5 snapshot save/load is used outside DSS

## Intended Demo Outcomes

- `E009 -> E005` should be valid.
- `E014 -> E010` should fail because `People` is not in `E010`'s allowed departments.
- `E002 -> E005` should fail because it would create a cycle.
- Adding any extra direct report under `E013` should fail because `E013` already has `2 / 2` reports.

## Why This Demo Is Useful

- It includes one root employee.
- It includes multiple departments and locations.
- It includes manager nodes with explicit capacity.
- It includes enough structure to test both valid and invalid drag-and-drop moves.
