# Review Checklist

## Metadata

- `plugin.json` exists and parses.
- `id` is stable and preferably matches the folder name.
- `version` follows semantic versioning.
- `meta.label`, `meta.description`, `meta.author`, `meta.icon`, and `meta.licenseInfo` are present and user-facing.

## Structure

- Component directories exist and contain their required descriptor/runtime files.
- `python-lib/` exists when logic is shared across components.
- `resource/` exists when the plugin ships static or data assets.
- `tests/` exists for non-trivial logic.

## Safety And Quality

- User inputs are validated before use.
- Config values use defensive reads where appropriate.
- String inputs are sanitized.
- Timezone and date handling are explicit.
- Error messages are actionable for DSS users.

## Dependencies

- Python/R requirements are declared.
- Plugin code environment exists when non-core packages are needed.
- Changes to dependencies are reflected in the environment spec.

## Release Readiness

- Version bumped for release.
- Repository is clean and branch strategy is sensible.
- Manual DSS validation done on a dedicated development instance.
