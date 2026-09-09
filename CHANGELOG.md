# Changelog

## Version 2.2.0 (2026-09-09)
* Load prepared Dataiku datasets with missing employee names, titles, departments, locations, levels or statuses. Missing names display as Employee followed by the ID; other absent details show explicit placeholders and review notices.
* Accept column names regardless of casing and outer whitespace, including move replay and export. Keep employee IDs, reporting links, duplicate columns and cycles strict.
* Preserve text IDs when reading project datasets through the DSS row API. No direct warehouse connection is required.
* Keep unknown status, explicit blank manager eligibility and missing rule inputs from authorizing new reports. Existing relationships with incomplete policy inputs remain visible with review notices; known violations still fail validation.

## Version 2.1.1 (2026-09-07)
* Reduced header, title and toolbar height to give the organization editor more space.
* Combined the organization title and counts into one row and removed introductory text.
* Expanded the chart viewport and retained responsive controls and dropdowns.

## Version 2.1.0 (2026-09-07)
* Simplified the organization workspace, card content, controls and Amdocs styling.
* Added expandable reporting levels, full-organization search and on-demand employee details.
* Added an accessible manager-change form using the existing move validation.
* Added touch panning, a local sample-data preview and browser regression coverage.

## Version 2.0.0 (2026-04-20)
* Rebuilt the plugin as an employee org-tree editor for Dataiku DSS
* Added hierarchy validation, drag-and-drop re-parenting, snapshot save/load, and CSV exports
* Bundled a plugin Python code environment definition and dependency notice for upload-ready packaging
* Removed obsolete decision-tree recipes, assets, and shared Python modules from the shipped plugin
* Hardened the webapp layout for narrow and wide screens and added large synthetic-org validation tests

## Version 1.1.3 (2025-12-10)
* Bump angularjs to 1.8.2
* Include jquery in plugin resources, rather than relying on angularjs jquerylite
* Fix js NPE when checking non-numeric values


## Version 1.1.2 (2025-05-14)
* Fix issue with webapp not displaying correctly
* Fix bug in pandas > 2
* Fix plugin make command

## Version 1.1.1 (2024-05-07)
* Scoring recipe: Specify array content type for decision_rules in output schema

## Version 1.1.0 (2023-05-11)
* Webapp: Fix autosplit (outdated kwarg in sklearn's DecisionTreeClassifier)
* Evaluation recipe: Fix recipe with multiclass tasks + import error
* Scoring recipe: Fix recipe for trees with only one node

## Version 1.0.7 (2022-11-10)
* Webapp: Display node id in node info panel
* Scoring/Evaluation recipes: Add two columns (one with the decision rule, one with the leaf id)

## Version 1.0.6 (2022-10-06)
* Webapp: Many UI improvements
* Webapp: Allow to treat features as numerical when less than 10 distinct values

## Version 1.0.5 (2022-01-28)
* Evaluation recipe: Fix broken import
* Minor UI improvement in webapp: fix font in buttons & input fields

## Version 1.0.4 (2021-10)
* Evaluation recipe: Fix broken import
* Evaluation recipe: Fix containerized execution (missing import)
* Evaluation recipe: Add missing key costMatrixWeights in metrics dict
* Fix wrong documentation link
