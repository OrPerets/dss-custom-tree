---
name: dataiku-webapp-plugin-development
description: Build or refactor Dataiku DSS webapp plugin components. Use when creating reusable HTML/Javascript, Bokeh, Dash, Streamlit, or Shiny webapp plugins, editing webapp.json parameters, wiring plugin code environments, or packaging webapps for DSS upload.
---

# Dataiku Webapp Plugin Development

Use this skill for reusable Dataiku webapp components inside plugins.

## Workflow

1. Prefer creating a normal DSS webapp first, then convert it to a plugin webapp from the DSS UI. That is the official Dataiku path.
2. Inspect `webapps/<webapp-id>/webapp.json` first. For plugin webapps, the main authoring surface is the `params` array.
3. Keep configuration generic and reusable. Webapp plugins do not use recipe-style `input_roles` or `output_roles`.
4. Pick the implementation model by framework:
   - Standard HTML/JS: `app.js`, `body.html`, `style.css`
   - Python frameworks: `backend.py`
   - R Shiny: `server.R`, `ui.R`
5. Read settings from the framework-specific config API instead of hard-coding project values.
6. Move heavy transformation logic into `python-lib/` where possible.
7. Put third-party Python packages in the plugin code environment, not ad hoc in the webapp.
8. After editing `webapp.json`, reload the plugin and refresh the DSS page. After editing `backend.py`, restart the webapp backend.

## What To Read

- Read [webapp-plugin-workflow.md](references/webapp-plugin-workflow.md) for the official step-by-step process.
- Read [webapp-file-map.md](references/webapp-file-map.md) for framework file layouts, config access, dependencies, and reload rules.

## Guardrails

- Keep parameter labels and descriptions generic enough for reuse.
- Avoid project-specific column names unless the plugin truly serves one domain only.
- Keep the DSS-facing configuration surface small; put optional behavior behind safe defaults.
