#!/usr/bin/env python3
"""Lightweight structural verifier for Dataiku DSS plugin repositories."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$")


def add(finding_list: list[str], level: str, message: str) -> None:
    finding_list.append(f"{level}: {message}")


def verify_plugin(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    plugin_json = root / "plugin.json"
    if not plugin_json.exists():
        add(errors, "ERROR", f"Missing plugin.json in {root}")
        return errors, warnings

    try:
        data = json.loads(plugin_json.read_text())
    except json.JSONDecodeError as exc:
        add(errors, "ERROR", f"plugin.json is not valid JSON: {exc}")
        return errors, warnings

    plugin_id = data.get("id")
    if not plugin_id:
        add(errors, "ERROR", "plugin.json is missing top-level 'id'")
    elif not isinstance(plugin_id, str) or not ID_RE.match(plugin_id):
        add(errors, "ERROR", f"plugin id is invalid: {plugin_id!r}")
    elif plugin_id != root.name:
        add(warnings, "WARN", f"plugin id '{plugin_id}' does not match folder '{root.name}'")

    version = data.get("version")
    if not version:
        add(errors, "ERROR", "plugin.json is missing top-level 'version'")
    elif not isinstance(version, str) or not SEMVER_RE.match(version):
        add(warnings, "WARN", f"version does not look like semantic versioning: {version!r}")

    meta = data.get("meta")
    if not isinstance(meta, dict):
        add(errors, "ERROR", "plugin.json is missing top-level 'meta' object")
    else:
        for field in ("label", "description", "author", "icon", "licenseInfo"):
            if not meta.get(field):
                add(warnings, "WARN", f"plugin meta.{field} is empty or missing")

    component_dirs = {
        "webapps": root / "webapps",
        "custom-recipes": root / "custom-recipes",
        "python-lib": root / "python-lib",
        "resource": root / "resource",
        "tests": root / "tests",
    }

    if not component_dirs["tests"].exists():
        add(warnings, "WARN", "tests/ directory is missing")

    if not component_dirs["python-lib"].exists():
        add(warnings, "WARN", "python-lib/ directory is missing")

    webapps_dir = component_dirs["webapps"]
    if webapps_dir.exists():
        for webapp_dir in sorted(p for p in webapps_dir.iterdir() if p.is_dir()):
            descriptor = webapp_dir / "webapp.json"
            if not descriptor.exists():
                add(errors, "ERROR", f"webapp '{webapp_dir.name}' is missing webapp.json")
                continue
            runtime_files = (
                "app.js",
                "body.html",
                "style.css",
                "backend.py",
                "server.R",
                "ui.R",
            )
            if not any((webapp_dir / name).exists() for name in runtime_files):
                add(
                    errors,
                    "ERROR",
                    f"webapp '{webapp_dir.name}' has no recognized runtime files",
                )

    recipes_dir = component_dirs["custom-recipes"]
    if recipes_dir.exists():
        for recipe_dir in sorted(p for p in recipes_dir.iterdir() if p.is_dir()):
            descriptor = recipe_dir / "recipe.json"
            if not descriptor.exists():
                add(errors, "ERROR", f"recipe '{recipe_dir.name}' is missing recipe.json")
            if not any((recipe_dir / name).exists() for name in ("recipe.py", "recipe.R")):
                add(errors, "ERROR", f"recipe '{recipe_dir.name}' is missing recipe.py or recipe.R")

    code_env_dir = root / "code-env" / "python"
    if code_env_dir.exists():
        if not (code_env_dir / "desc.json").exists():
            add(errors, "ERROR", "code-env/python/desc.json is missing")
        if not (code_env_dir / "spec" / "requirements.txt").exists():
            add(warnings, "WARN", "code-env/python/spec/requirements.txt is missing")
    else:
        add(warnings, "WARN", "plugin has no bundled Python code environment definition")

    if not (root / "requirements.json").exists():
        add(warnings, "WARN", "requirements.json is missing at plugin root")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a Dataiku DSS plugin structure.")
    parser.add_argument("plugin_root", help="Path to the Dataiku plugin root directory")
    args = parser.parse_args()

    root = Path(args.plugin_root).expanduser().resolve()
    if not root.exists():
        print(f"ERROR: path does not exist: {root}")
        return 2
    if not root.is_dir():
        print(f"ERROR: path is not a directory: {root}")
        return 2

    errors, warnings = verify_plugin(root)
    print(f"Plugin root: {root}")
    for finding in errors + warnings:
        print(finding)

    if not errors and not warnings:
        print("OK: no structural issues found")
        return 0

    print(f"Summary: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
