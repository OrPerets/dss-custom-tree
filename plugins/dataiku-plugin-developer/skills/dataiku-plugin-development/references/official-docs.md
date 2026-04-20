# Official Docs

Use official Dataiku sources only unless the user explicitly asks for broader research.

- Plugin tutorials index: [developer.dataiku.com/latest/tutorials/plugins/index.html](https://developer.dataiku.com/latest/tutorials/plugins/index.html)
- Creating and configuring a plugin: [developer.dataiku.com/latest/tutorials/plugins/creation-configuration/index.html](https://developer.dataiku.com/latest/tutorials/plugins/creation-configuration/index.html)
- Dedicated plugin dev instance and best practices: [developer.dataiku.com/latest/tutorials/plugins/setup-a-dev-env/index.html](https://developer.dataiku.com/latest/tutorials/plugins/setup-a-dev-env/index.html)
- Plugin components reference: [doc.dataiku.com/dss/latest/plugins/reference/plugins-components.html](https://doc.dataiku.com/dss/latest/plugins/reference/plugins-components.html)
- Other plugin topics: code envs, shared code, resources, custom settings UI: [doc.dataiku.com/dss/latest/plugins/reference/other.html](https://doc.dataiku.com/dss/latest/plugins/reference/other.html)
- Plugins code environments: [doc.dataiku.com/dss/latest/code-envs/plugins.html](https://doc.dataiku.com/dss/latest/code-envs/plugins.html)
- Plugin Git versioning: [developer.dataiku.com/latest/tutorials/plugins/git-versioning/plugin-versioning/index.html](https://developer.dataiku.com/latest/tutorials/plugins/git-versioning/plugin-versioning/index.html)

Key points encoded from those docs:

- Dataiku recommends using a dedicated instance for plugin development.
- Dataiku recommends letting DSS create the initial plugin structure.
- `python-lib/` is the right place for reusable shared code.
- Bundled plugin code environments are the preferred dependency mode.
- Separate repositories per plugin are recommended.
