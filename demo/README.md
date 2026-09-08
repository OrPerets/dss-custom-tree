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

## Run the interactive preview

Use a Python environment with Flask and pandas installed:

```sh
python3 demo/serve.py --port 8765
```

Open `http://127.0.0.1:8765`. This serves the plugin’s actual HTML, CSS, JavaScript and backend with the bundled sample CSVs; it never connects to DSS. Saved versions exist in a temporary directory for the lifetime of the preview server.

To run the browser regression checks, use an environment with Flask, pandas, pytest and Playwright:

```sh
python3 -m playwright install chromium
python3 -m pytest tests/browser -q
```

The browser suite launches its own localhost preview server on an available port.
