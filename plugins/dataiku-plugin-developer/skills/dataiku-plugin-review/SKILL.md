---
name: dataiku-plugin-review
description: Review a Dataiku DSS plugin repo for quality and upload readiness. Use when checking plugin.json metadata, component structure, webapp or recipe descriptors, code environments, shared code boundaries, testing gaps, and packaging risks before publishing or uploading to DSS.
---

# Dataiku Plugin Review

Use this skill when the task is to audit an existing Dataiku plugin rather than create one from scratch.

## Workflow

1. Run the local verifier first:

```bash
python3 plugins/dataiku-plugin-developer/scripts/verify_dataiku_plugin.py <plugin-root>
```

2. Review `plugin.json` metadata and versioning.
3. Review each component directory for missing descriptor or runtime files.
4. Check whether shared logic belongs in `python-lib/` instead of component entrypoints.
5. Check input validation, string sanitization, timezone handling, and defensive config reads.
6. Check dependency declaration and code environment setup.
7. Confirm the plugin is ready for version control and release packaging.

## What To Read

- Read [review-checklist.md](references/review-checklist.md) when doing a full audit.

## Output Expectations

- Report blockers first.
- Then report warnings and missing tests.
- Keep findings tied to concrete files and component IDs.
