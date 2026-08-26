#!/usr/bin/env python3
"""
JSearch profile importer.

Reads config/profile.json (written by the setup assistant, or by hand from
config/profile.example.json), validates it against config/profile.schema.json,
and expands it into the two files the pipeline reads:

    config/profile.yaml
    config/search-criteria.yaml

Usage:
    python3 scripts/import_profile.py                    # import config/profile.json
    python3 scripts/import_profile.py --check            # validate only, write nothing
    python3 scripts/import_profile.py --input path.json  # import from elsewhere
    python3 scripts/import_profile.py --force            # overwrite without asking

Run from the project root. Requires PyYAML.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import get_project_root, save_yaml


# --------------------------------------------------------------------------
# Minimal JSON Schema validator (the subset profile.schema.json actually uses)
# --------------------------------------------------------------------------

JSON_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _type_ok(value, expected):
    names = expected if isinstance(expected, list) else [expected]
    for name in names:
        py = JSON_TYPES.get(name)
        if py is None:
            continue
        # bool is a subclass of int in Python; JSON treats them as distinct
        if name in ("integer", "number") and isinstance(value, bool):
            continue
        if isinstance(value, py):
            return True
    return False


def validate(node, schema, path="profile", errors=None):
    """Collect human-readable validation errors. Returns the list."""
    import re

    if errors is None:
        errors = []

    if "type" in schema and not _type_ok(node, schema["type"]):
        want = schema["type"]
        want = " or ".join(want) if isinstance(want, list) else want
        errors.append(f"{path}: expected {want}, got {type(node).__name__}")
        return errors

    if "enum" in schema and node not in schema["enum"]:
        errors.append(f"{path}: {node!r} is not one of {schema['enum']}")

    if isinstance(node, str) and "pattern" in schema:
        if not re.match(schema["pattern"], node):
            errors.append(f"{path}: {node!r} does not match {schema['pattern']}")

    if isinstance(node, (int, float)) and not isinstance(node, bool):
        if "minimum" in schema and node < schema["minimum"]:
            errors.append(f"{path}: {node} is below minimum {schema['minimum']}")
        if "maximum" in schema and node > schema["maximum"]:
            errors.append(f"{path}: {node} is above maximum {schema['maximum']}")

    if isinstance(node, dict):
        for key in schema.get("required", []):
            if key not in node or node[key] in (None, "", [], {}):
                errors.append(f"{path}.{key}: required, and it cannot be empty")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in node:
                if key not in props:
                    errors.append(f"{path}.{key}: unknown field (check the schema for typos)")
        for key, sub in props.items():
            if key in node and node[key] is not None:
                validate(node[key], sub, f"{path}.{key}", errors)

    if isinstance(node, list):
        if "minItems" in schema and len(node) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} item(s), got {len(node)}")
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(node):
                validate(item, item_schema, f"{path}[{i}]", errors)

    return errors


# --------------------------------------------------------------------------
# Expansion: profile.json -> profile.yaml + search-criteria.yaml
# --------------------------------------------------------------------------

def drop_empty(value):
    """Recursively remove None and empty containers so the YAML stays readable."""
    if isinstance(value, dict):
        cleaned = {k: drop_empty(v) for k, v in value.items()}
        return {k: v for k, v in cleaned.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        cleaned = [drop_empty(v) for v in value]
        return [v for v in cleaned if v not in (None, "", [], {})]
    return value


def build_profile_yaml(data):
    ident = data.get("identity", {})
    profile = {
        "name": ident.get("full_name"),
        "birth_date": ident.get("birth_date"),
        "email": ident.get("email"),
        "phone": ident.get("phone"),
        "location": ident.get("location"),
        "linkedin": ident.get("linkedin"),
        "website": ident.get("website"),
        "github": ident.get("github"),
        "languages": ident.get("languages", []),
        "current_role": data.get("current_role", {}),
        "total_experience_years": data.get("total_experience_years"),
        "professional_summary": data.get("professional_summary"),
        "work_history": data.get("work_history", []),
        "education": data.get("education", []),
        "skills": data.get("skills", {}),
        "certifications": data.get("certifications", []),
        "notable_achievements": data.get("notable_achievements", []),
        "work_preferences": data.get("work_preferences", {}),
        "salary_expectations": data.get("salary_expectations", {}),
        "narrative_rules": data.get("narrative_rules", {}),
    }
    return drop_empty(profile)


def build_criteria_yaml(data):
    crit = dict(data.get("search_criteria", {}))
    crit.setdefault("minimum_score", 50)
    crit.setdefault("auto_prepare_threshold", 85)
    crit.setdefault("materials_language", "English")
    return drop_empty(crit)


HEADER_PROFILE = (
    "# JSearch professional profile\n"
    "# GENERATED FILE. Edit config/profile.json and re-run:\n"
    "#   python3 scripts/import_profile.py\n"
)
HEADER_CRITERIA = (
    "# JSearch job search criteria\n"
    "# GENERATED FILE. Edit config/profile.json and re-run:\n"
    "#   python3 scripts/import_profile.py\n"
)


def write_with_header(path, header, data):
    save_yaml(path, data)
    with open(path, "r", encoding="utf-8") as f:
        body = f.read()
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n" + body)


def confirm_overwrite(paths, force):
    existing = [p for p in paths if os.path.exists(p)]
    if not existing or force:
        return True
    print("These files already exist and will be overwritten:")
    for p in existing:
        print(f"  {os.path.relpath(p)}")
    if not sys.stdin.isatty():
        print("Not a terminal. Re-run with --force to overwrite.")
        return False
    return input("Overwrite? [y/N] ").strip().lower() in ("y", "yes")


def show(path, root):
    """Show a path relative to the project root when it lives inside it."""
    rel = os.path.relpath(path, root)
    return path if rel.startswith("..") else rel


def main():
    parser = argparse.ArgumentParser(description="Import a JSearch profile JSON into the config YAMLs.")
    parser.add_argument("--input", help="Path to the profile JSON (default: config/profile.json)")
    parser.add_argument("--check", action="store_true", help="Validate only, write nothing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing YAML without asking")
    args = parser.parse_args()

    root = get_project_root()
    src = args.input or os.path.join(root, "config", "profile.json")
    schema_path = os.path.join(root, "config", "profile.schema.json")

    if not os.path.exists(src):
        print(f"Not found: {show(src, root)}")
        print("Start from the example:")
        print("  cp config/profile.example.json config/profile.json")
        print('Or open Claude Code here and say: "Set up my JSearch profile"')
        return 1

    try:
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"{show(src, root)} is not valid JSON.")
        print(f"  line {e.lineno}, column {e.colno}: {e.msg}")
        return 1

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    errors = validate(data, schema)
    if errors:
        print(f"{len(errors)} problem(s) in {show(src, root)}:\n")
        for e in errors:
            print(f"  - {e}")
        print("\nSee config/profile.schema.json for the full contract.")
        return 1

    name = data["identity"]["full_name"]
    roles = len(data.get("work_history", []))
    titles = len(data["search_criteria"]["target_roles"]["titles"])
    print(f"Profile valid: {name}, {roles} role(s), {titles} target title(s).")

    if args.check:
        return 0

    profile_path = os.path.join(root, "config", "profile.yaml")
    criteria_path = os.path.join(root, "config", "search-criteria.yaml")

    if not confirm_overwrite([profile_path, criteria_path], args.force):
        print("Nothing written.")
        return 1

    write_with_header(profile_path, HEADER_PROFILE, build_profile_yaml(data))
    write_with_header(criteria_path, HEADER_CRITERIA, build_criteria_yaml(data))

    print("Wrote config/profile.yaml")
    print("Wrote config/search-criteria.yaml")
    print("\nNext: drop a CSV in inbox/clay-exports/ (or a .txt in inbox/manual/)")
    print('then say "Process my inbox" in Claude Code.')
    return 0


if __name__ == "__main__":
    sys.exit(main())
