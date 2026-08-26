"""JSearch shared utilities."""

import os
import re
import unicodedata
from datetime import datetime, timezone


def get_project_root():
    """Return the jsearch project root (parent of scripts/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def slugify(text, max_length=40):
    """Convert text to a URL-safe slug."""
    if not text:
        return "unknown"
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    text = text.strip("-")
    return text[:max_length] if text else "unknown"


def make_folder_name(posted_on, company, role):
    """Generate application folder name: YYYY-MM-DD_company-slug_role-slug."""
    try:
        dt = datetime.fromisoformat(posted_on.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return f"{date_str}_{slugify(company)}_{slugify(role)}"


def now_iso():
    """Return current UTC time in ISO 8601."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path):
    """Load a YAML file. Returns empty dict if file doesn't exist."""
    import yaml
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path, data):
    """Save data to a YAML file."""
    import yaml
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
