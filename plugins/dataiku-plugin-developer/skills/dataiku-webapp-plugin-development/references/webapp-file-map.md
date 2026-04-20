# Webapp File Map

## Component Files

From the official Dataiku webapp component reference:

- HTML/Javascript webapp plugin:
  - `webapp.json`
  - `app.js`
  - `body.html`
  - `style.css`
- Python Bokeh, Streamlit, or Dash webapp plugin:
  - `webapp.json`
  - `backend.py`
- R Shiny webapp plugin:
  - `webapp.json`
  - `server.R`
  - `ui.R`

## Config Access

- HTML/JS: `dataiku.getWebAppConfig()`
- Python: `get_webapp_config()`
- R Shiny: `dataiku::dkuPluginConfig()`

## Dependencies

- Define Python dependencies in `code-env/python/spec/requirements.txt`.
- Build or update the plugin code environment from the plugin summary/admin view after changing requirements.

## Reuse Pattern

- Thin UI layer in the webapp files.
- Thin DSS backend in `backend.py`.
- Reusable logic in `python-lib/`.
- Small, typed `params` surface in `webapp.json`.
