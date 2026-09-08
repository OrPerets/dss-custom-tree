# Sample datasets for the organization editor

These are fictional sample records, not Amdocs employee data. They match the movement examples used for testing the plugin.

## Upload and configure

Upload each CSV as a separate dataset in the same Dataiku project as the webapp. Use a comma separator, UTF-8 encoding, and the first row as column names. Preserve the column names and blank cells.

| CSV file | Suggested Dataiku dataset name | Webapp setting |
| --- | --- | --- |
| `employees-demo.csv` | `org_employees_demo` | **Input workforce dataset** |
| `manager-constraints-demo.csv` | `org_manager_rules_demo` | **Default rules dataset** |

The employee file has 15 employees across five departments. The rules file has eight manager-specific rule rows. The rules dataset is optional for the plugin, but select it to reproduce the examples below.

To test **Save version**, create an empty managed folder, such as `org_tree_versions`, and select it as the **Baseline folder**. This is a folder, not a third dataset; no sample snapshot file is needed.

## Column handling

- Keep IDs, names, departments, locations, levels and statuses as text.
- `manager_id` is blank only for Nora Levin (`E001`), the head of the organization.
- `max_direct_reports` and `sort_order` are optional integer fields. Blank capacity means there is no limit unless the rules dataset supplies one.
- `can_be_manager` contains `true` or `false` and can be imported as a boolean.
- `allowed_departments` and `allowed_locations` are text fields containing pipe-separated lists. For example, `Engineering|Data` is one cell. Do not use the pipe character as the CSV separator.
- A nonblank capacity in the rules dataset overrides the employee-row capacity. Shira Azul (`E010`) deliberately demonstrates this: employee capacity 2, rules capacity 3.
- `rule_note` explains a rule; its wording does not affect validation.

## Expected first view

The organization has one root and opens with three reporting levels. Choose **All levels** to see all 15 employees. Ella Peleg (`E013`) has two reports and capacity two, so one item needs review. This is an expected capacity warning; the hierarchy is valid.

## Moves to test

Start each example from the original demo organization. After a successful test, use **Changes & versions → Discard unsaved changes** before trying the next example.

| Move | Expected result |
| --- | --- |
| Tomer Niv (`E009`) → Daniel Katz (`E005`) | Accepted |
| Daniel Katz (`E005`) → Nora Levin (`E001`) | Accepted; Roni Sela and Gal Mor remain in Daniel's team |
| Omer Tzur (`E014`) → Shira Azul (`E010`) | Rejected: department/location restrictions |
| Roni Sela (`E007`) → Lior Shani (`E006`) | Rejected: location restriction |
| Amir Cohen (`E002`) → Daniel Katz (`E005`) | Rejected: reporting cycle |
| Tomer Niv (`E009`) → Ella Peleg (`E013`) | Rejected: manager at capacity |

The editor can change reporting relationships. To edit employee attributes or rules, update the respective source dataset, then use **Changes & versions → Data source → Refresh from source**. Save any draft you want to retain before refreshing. Saving a version creates a snapshot and does not overwrite either input dataset.
