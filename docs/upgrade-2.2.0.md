# Update the Dataiku organization editor to 2.2.0

Use the workforce dataset you already created in your Dataiku project. No new SQL, warehouse connection or Snowflake configuration is required by the plugin.

1. Update the installed **Amdocs Workforce Org Designer** plugin using `dss-plugin-employee-org-tree-visualizer-2.2.0.zip`. The plugin and webapp component IDs are unchanged.
2. In the webapp settings, keep your prepared dataset selected as **Input workforce dataset**. Leave **Default rules dataset** blank unless you have a rules dataset to apply.
3. Restart the webapp backend and reload the webapp. Use **Changes & versions → Data source → Refresh from source** to load the prepared dataset. Save any current draft before refreshing.

The updated editor loads a valid reporting hierarchy even if names or descriptive fields are incomplete:

- Missing names display as `Employee <ID>`.
- Missing titles, departments, locations, levels and statuses use explicit placeholders.
- The review badge filters affected people. Select an employee to see which fields are missing.
- Names can be corrected in the Dataiku source dataset whenever available. Refresh to show those corrections.

Keep the `employee_id` and `manager_id` columns as strings in the Dataiku schema. Employee ID values must be unique and nonblank. Only one employee has a blank manager ID; every other manager must exist in the dataset. The plugin accepts uppercase/lowercase column names and surrounding whitespace, and rejects ambiguous duplicate names.

Move checks remain active. Unknown employment status, an explicitly blank `can_be_manager`, or a missing department/location/level needed by the target manager's rules blocks that proposed move. Existing relationships with unknown policy inputs can be viewed with a review notice; known inactive/ineligible managers, known rule violations, invalid reporting links and cycles still produce errors. Omitting the optional `can_be_manager` column retains its previous true default.

Source rows are read through Dataiku's [dataset row API](https://developer.dataiku.com/latest/concepts-and-examples/datasets/datasets-data.html#using-the-streaming-api), avoiding pandas type inference for text IDs. The plugin keeps the whole hierarchy in memory for validation and rendering. Display placeholders do not overwrite source values or replace missing names in exports.

Local verification on 2026-09-09: 42 Python tests and 16 browser tests passed. These cover incomplete inputs, Dataiku dataset reads through a simulated adapter, manager moves, warnings, rule rejection, snapshots, exports, responsive controls and keyboard interaction. The partial-data browser view was visually inspected. Plugin descriptor validation reported zero errors. The updated package has not yet been installed or verified in your DSS instance.
