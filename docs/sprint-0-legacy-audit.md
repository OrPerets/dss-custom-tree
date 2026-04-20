# Sprint 0 Legacy Asset Audit

This audit records the baseline cleanup decisions made before the employee org tree implementation begins in earnest.

| Area | Current paths | Decision | Reasoning |
| --- | --- | --- | --- |
| Plugin identity | `plugin.json` | Replace | The plugin now needs a single employee-org-tree identity in DSS. |
| Main webapp component | `webapps/interactive-decision-tree-builder/` | Replace | Renamed to `webapps/employee-org-tree-editor/` to match the new product boundary. |
| Webapp UI scaffold | `webapps/employee-org-tree-editor/*`, `resource/templates/*`, `resource/js/*` | Replaced in Sprint 6 | The org-tree webapp now ships only the active HTML, CSS, JS, and backend files under the component itself. |
| Shared static libraries | `resource/jquery.min.js`, `resource/angular.min.js`, `resource/spin.min.js` | Reduced in Sprint 6 | Angular remains for the DSS webapp shell. Unused jquery and spinner assets were removed from the shipped plugin payload. |
| Legacy screenshots and icons | `resource/img-doc/*`, `resource/img/sunburst.png`, `resource/img/fit.png`, `resource/img/100.png` | Removed in Sprint 6 | They described the pre-rewrite experience and no longer belong in the employee-org-tree package. |
| Legacy custom recipes | `custom-recipes/decision-tree-builder-tree-scoring/`, `custom-recipes/decision-tree-builder-tree-evaluation/` | Removed in Sprint 6 | They were reference-only and out of scope for the webapp-first delivery. |
| Legacy Python domain modules | `python-lib/dku_idtb_decision_tree/`, `python-lib/dku_idtb_scoring/`, `python-lib/dku_idtb_compatibility/` | Removed in Sprint 6 | The plugin now ships only the employee-hierarchy domain modules under `python-lib/employee_tree/`. |
| Legacy unit tests | `tests/python/unit/test_tree.py`, `tests/python/unit/test_score.py`, `tests/python/unit/test_autosplit.py` | Replace | The test suite needs to validate employee parsing, hierarchy building, and rule enforcement instead. |
| Employee-tree docs and demo files | `docs/employee-tree-*`, `demo/*` | Keep | These already define the intended target product and sample inputs for the rewrite. |
