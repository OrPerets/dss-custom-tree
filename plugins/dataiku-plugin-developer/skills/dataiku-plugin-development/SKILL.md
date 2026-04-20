---
name: dataiku-plugin-development
description: Create, extend, or refactor Dataiku DSS plugins and components. Use when building plugin.json, component folders, python-lib shared code, code environments, packaging structure, or upload-ready plugin repos for Dataiku.
---

# Dataiku Plugin Development

Use this skill for general Dataiku DSS plugin work. If the task is specifically about reusable web apps, also use `dataiku-webapp-plugin-development`.

## Workflow

1. Inspect the plugin root first: `plugin.json`, component directories, `python-lib/`, `resource/`, `code-env/`, and `tests/`.
2. Prefer the directory layout that Dataiku initializes from the DSS UI. Dataiku explicitly recommends letting DSS create the initial plugin structure instead of hand-rolling it from scratch.
3. Keep the plugin identifier, top-level directory, and Git repository aligned. Treat `plugin.json.id` as stable and version with semantic versioning.
4. Keep reusable business logic in `python-lib/` and keep Dataiku entrypoints thin. When possible, keep shared modules independent from `dataiku` imports so they are easier to test locally.
5. Validate every user parameter before execution. Use defensive reads such as `config.get("key", default)` rather than assuming fields exist.
6. Sanitize strings and handle dates and time zones deliberately. These are common sources of plugin defects and security issues.
7. If the plugin needs non-core packages, prefer a bundled plugin code environment under `code-env/python/` and keep `requirements.txt` explicit.
8. For release work, keep one repository per plugin when practical and use Git branches/tags for versioned releases.

## What To Read

- Read [official-docs.md](references/official-docs.md) first for the canonical Dataiku sources.
- Read [plugin-structure-and-release.md](references/plugin-structure-and-release.md) when you need file layout, shared-code guidance, code-env setup, or packaging decisions.

## Output Expectations

- Produce edits directly in the plugin repo.
- Keep Dataiku-facing metadata concise and user-facing.
- When reviewing, separate blockers from warnings.
