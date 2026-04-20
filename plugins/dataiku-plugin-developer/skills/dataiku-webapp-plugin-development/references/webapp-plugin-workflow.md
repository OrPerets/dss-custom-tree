# Webapp Plugin Workflow

Official sources:

- Tutorial: [developer.dataiku.com/latest/tutorials/plugins/webapps/generality/index.html](https://developer.dataiku.com/latest/tutorials/plugins/webapps/generality/index.html)
- Reference: [doc.dataiku.com/dss/latest/plugins/reference/webapps.html](https://doc.dataiku.com/dss/latest/plugins/reference/webapps.html)

## Recommended Path

1. Build a normal DSS webapp first.
2. In DSS, convert it to a plugin webapp.
3. Choose an existing development plugin or create a new one.
4. Edit the generated `webapp.json`.
5. Move framework/runtime dependencies to the plugin code environment.
6. Test the webapp from a project object such as a dataset.

## What Matters In `webapp.json`

- The important surface is `params`.
- Unlike plugin recipes, there are no `input_roles` or `output_roles`.
- Use typed params and parameter dependencies such as `datasetParamName` for dataset-column selectors.

## Reload Behavior

- If `webapp.json` changes:
  - `Actions > Reload this plugin`
  - Refresh the DSS page in the browser
- If `backend.py` changes:
  - No full plugin reload is required
  - Restart the webapp backend
