# Plugin Structure And Release

## Core Structure

Minimum useful structure for a Python-based Dataiku plugin:

```text
plugin-root/
├── plugin.json
├── python-lib/
├── resource/
├── webapps/ or custom-recipes/ or other component dirs
├── code-env/
│   └── python/
│       ├── desc.json
│       └── spec/
│           └── requirements.txt
└── tests/
```

Important details from Dataiku docs:

- `plugin.json.id` should match the top-level plugin directory as a best practice.
- Use semantic versioning in `plugin.json.version`.
- Keep plugin and component names lowercase and hyphenated in DSS.
- Dataiku advises not to include the words `plugin` or `custom` in DSS plugin/component names.

## Shared Code

- Put reusable logic in `python-lib/`.
- Prefer pure Python modules in `python-lib/` and keep `dataiku` imports in the thin component entrypoints.
- This makes local tests simpler and reduces coupling to DSS runtime objects.

## Dependencies

- Preferred mode: ship a plugin code environment definition in `code-env/python/`.
- Add `requirements.txt` under `code-env/python/spec/`.
- Keep `desc.json` explicit so admins can build the environment after install.
- Optional: add root `requirements.json` to declare dependencies to administrators.

## Release Checklist

- Bump `plugin.json.version`.
- Confirm metadata is accurate and user-facing labels are clean.
- Verify component IDs and directory names are stable.
- Review code-env contents and rebuild in DSS if requirements changed.
- Run local tests and targeted manual validation in a development DSS instance.
- Keep release work on a dedicated branch and tag the shipped version.
