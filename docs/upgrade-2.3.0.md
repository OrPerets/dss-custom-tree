# Inspect and resolve missing manager records

The error `Employee X references missing manager Y` means a row has `manager_id = Y`, but no employee row has `employee_id = Y` after normalizing outer whitespace. Repeated manager IDs across employees are normal; the missing employee row is the problem.

One possible cause in the earlier extraction is its active-job filter: employees can reference managers who are absent from that filtered population. A project dataset may also have been filtered or sampled, or its ID columns may have been imported with different formats. The plugin cannot determine the cause or recover absent employee details without the complete source records.

## Use the new review view

1. Update the installed plugin using `dss-plugin-employee-org-tree-visualizer-2.3.0.zip`, restart the webapp backend and reload the page.
2. Keep the prepared employee dataset selected under **Input workforce dataset**. Leave **Default rules dataset** empty unless it contains actual manager policies with one row per manager.
3. On the missing-manager error, select **Review available employees**.
4. Expand a review group or search for an employee ID, name or manager ID. The view starts with groups collapsed to avoid rendering a large incomplete organization all at once.
5. Select **Download missing managers** to get one row per missing manager ID, its direct-report count in this dataset, and the affected employee IDs.

The view is explicitly read-only. Missing managers are reference cards, not recovered employee records. **Imported workforce** is a display group, and its dashed links do not represent real reporting relationships. The people counter and ordinary hierarchy export include only source employees. Original employee-manager IDs and blank root values are retained. The plugin does not write anything back to the dataset or contact a separate warehouse connection.

Moves and **Save version** remain disabled until the reporting links are complete. The strict move and save endpoints continue rejecting incomplete source hierarchies. Duplicate employees, self-management, cycles and known policy violations remain errors; review does not hide them.

## Complete the prepared Dataiku dataset

- Look up each reported missing manager ID in the source population. Add the actual employee row if it belongs to the intended organization, and include its own manager chain as needed.
- Keep both `employee_id` and `manager_id` as text with the same identifier convention. Check examples such as `00123` versus `123`, or `123` versus `123.0`. Correct the import or mapping based on the real identifier definition; the plugin does not merge these values automatically.
- Check any active-status, department or sampling filters that may have excluded managers.
- For an intentionally scoped organization, explicitly choose its real head and the desired reporting population. Do not replace every missing manager ID with null or assign everyone to an assumed CEO.

After correction, use **Changes & versions → Data source → Refresh from source**. Normal editing resumes when the hierarchy has one root, complete parent references and no remaining validation errors.

Local checks on 2026-09-09: 54 Python tests and 18 browser tests passed, including a 24,000-employee incomplete hierarchy, strict move/save rejection and report/export preservation. Browser verification covers the review action, reference labels, source-only counts, disabled editing, report download, responsive layout and bounded error display. The rendered review view was visually inspected. This package has not been installed or tested in your DSS instance.
