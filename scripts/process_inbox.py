#!/usr/bin/env python3
"""
JSearch Inbox Processor
Parses Clay.com CSV exports and creates application folders.
Usage: python3 scripts/process_inbox.py [--dry-run]
Run from the jsearch/ project root.
"""

import csv
import os
import sys
from datetime import datetime, timezone

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import get_project_root, slugify, make_folder_name, now_iso, load_yaml, save_yaml

# Flexible column mapping: each key maps to possible column names in Clay exports
COLUMN_MAP = {
    "company_name": ["Company Name", "company_name", "Company", "Empresa"],
    "job_title": ["Job Title", "job_title", "Title", "Role", "Titulo"],
    "location": ["Location", "location", "Job Location", "Ubicacion"],
    "company_domain": ["Company Domain", "company_domain", "Domain", "Website"],
    "linkedin_url": ["Job LinkedIn URL", "linkedin_url", "LinkedIn URL", "URL"],
    "posted_on": ["Posted On", "posted_on", "Date Posted", "Posted"],
    "enrich_company": ["Enrich Company", "enrich_company"],
    "employee_count": ["Employee Count", "employee_count", "Employees"],
    "founded": ["Founded", "founded"],
    "follower_count": ["Follower Count", "follower_count", "Followers"],
    "news": ["News", "Find News Results", "Company News"],
}


def resolve_columns(headers):
    """Map our standard field names to actual CSV column indices."""
    mapping = {}
    for field, aliases in COLUMN_MAP.items():
        for alias in aliases:
            if alias in headers:
                mapping[field] = headers.index(alias)
                break
    return mapping


def get_field(row, col_map, field, default=""):
    """Safely get a field from a row using the column mapping."""
    idx = col_map.get(field)
    if idx is None or idx >= len(row):
        return default
    return row[idx].strip() if row[idx] else default


def get_existing_urls(applications_dir):
    """Collect all LinkedIn URLs from existing application folders for dedup."""
    urls = set()
    if not os.path.exists(applications_dir):
        return urls
    for folder in os.listdir(applications_dir):
        job_path = os.path.join(applications_dir, folder, "job.yaml")
        if os.path.exists(job_path):
            data = load_yaml(job_path)
            url = (data.get("urls") or {}).get("linkedin", "")
            if url:
                urls.add(url)
    return urls


def parse_csv(filepath):
    """Parse a Clay CSV export. Returns list of row dicts."""
    rows = []
    encodings = ["utf-8-sig", "utf-8", "latin-1"]

    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                reader = csv.reader(f)
                headers = next(reader)
                col_map = resolve_columns(headers)

                if "job_title" not in col_map:
                    print(f"  WARNING: No 'Job Title' column found in {filepath}")
                    return []

                for row in reader:
                    title = get_field(row, col_map, "job_title")
                    if not title:
                        continue

                    employee_count = get_field(row, col_map, "employee_count")
                    founded = get_field(row, col_map, "founded")

                    rows.append({
                        "company_name": get_field(row, col_map, "company_name"),
                        "job_title": title,
                        "location": get_field(row, col_map, "location"),
                        "company_domain": get_field(row, col_map, "company_domain"),
                        "linkedin_url": get_field(row, col_map, "linkedin_url"),
                        "posted_on": get_field(row, col_map, "posted_on"),
                        "enrich_company": get_field(row, col_map, "enrich_company"),
                        "employee_count": int(employee_count) if employee_count.isdigit() else None,
                        "founded": int(founded) if founded.isdigit() else None,
                        "follower_count": get_field(row, col_map, "follower_count"),
                    })
            break  # encoding worked
        except UnicodeDecodeError:
            continue

    return rows


def create_application(job_data, applications_dir, source_file):
    """Create an application folder with job.yaml and status.yaml."""
    folder_name = make_folder_name(
        job_data["posted_on"],
        job_data["company_name"],
        job_data["job_title"],
    )
    folder_path = os.path.join(applications_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    job_yaml = {
        "id": folder_name,
        "source": "clay",
        "source_file": os.path.basename(source_file),
        "ingested_at": now_iso(),
        "company": {
            "name": job_data["company_name"],
            "domain": job_data["company_domain"] or None,
            "employee_count": job_data["employee_count"],
            "founded": job_data["founded"],
            "industry": "",
        },
        "role": {
            "title": job_data["job_title"],
            "location": job_data["location"],
            "remote": _guess_remote(job_data["job_title"], job_data["location"]),
            "seniority": _guess_seniority(job_data["job_title"]),
            "posted_on": job_data["posted_on"] or None,
        },
        "urls": {
            "linkedin": job_data["linkedin_url"] or None,
            "company_careers": None,
            "posting_direct": None,
        },
        "description": "",
        "requirements": {
            "must_have": [],
            "nice_to_have": [],
            "skills_mentioned": [],
        },
        "enrichment": {
            "news": None,
            "company_about": None,
            "enriched_at": None,
        },
        "tags": [],
        "notes": "",
    }

    status_yaml = {
        "current_status": "new",
        "score": None,
        "tier": None,
        "timeline": [
            {
                "status": "new",
                "date": now_iso(),
                "notes": f"Ingested from Clay export: {os.path.basename(source_file)}",
            }
        ],
        "materials": {
            "cv_generated": False,
            "cover_letter_generated": False,
            "cv_path": "",
            "cover_letter_path": "",
        },
        "application": {
            "applied_on": None,
            "applied_via": "",
            "confirmation": "",
        },
        "follow_ups": [],
        "response": {
            "received_on": None,
            "type": "",
            "details": "",
        },
        "next_action": "Awaiting analysis",
        "next_action_date": None,
    }

    save_yaml(os.path.join(folder_path, "job.yaml"), job_yaml)
    save_yaml(os.path.join(folder_path, "status.yaml"), status_yaml)

    return folder_name


def _guess_remote(title, location):
    """Heuristic: check if job seems remote."""
    text = f"{title} {location}".lower()
    remote_signals = ["remote", "remoto", "anywhere", "work from home", "wfh"]
    return any(s in text for s in remote_signals)


def _guess_seniority(title):
    """Heuristic: guess seniority from title."""
    title_lower = title.lower()
    if any(w in title_lower for w in ["chief", "cro", "cto", "cmo", "ceo", "cfo", "cio"]):
        return "c-level"
    if any(w in title_lower for w in ["vp ", "vice president"]):
        return "vp"
    if any(w in title_lower for w in ["director", "gerente"]):
        return "director"
    if any(w in title_lower for w in ["head of", "head", "lider", "líder"]):
        return "lead"
    if any(w in title_lower for w in ["senior", "sr.", "sr "]):
        return "senior"
    if any(w in title_lower for w in ["manager"]):
        return "manager"
    if any(w in title_lower for w in ["junior", "jr.", "jr ", "intern", "practicante"]):
        return "junior"
    return "mid"


def main():
    root = get_project_root()
    inbox_dir = os.path.join(root, "inbox", "clay-exports")
    applications_dir = os.path.join(root, "applications")
    logs_dir = os.path.join(root, "logs", "runs")
    dry_run = "--dry-run" in sys.argv

    os.makedirs(applications_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    # Find unprocessed CSVs
    csv_files = [
        f for f in os.listdir(inbox_dir)
        if f.endswith(".csv") and not f.endswith(".processed.csv")
    ] if os.path.exists(inbox_dir) else []

    if not csv_files:
        print("No new CSV files found in inbox/clay-exports/")
        return

    # Get existing URLs for dedup
    existing_urls = get_existing_urls(applications_dir)
    total_created = 0
    total_skipped = 0
    total_dupes = 0
    created_folders = []

    for csv_file in csv_files:
        csv_path = os.path.join(inbox_dir, csv_file)
        print(f"\nProcessing: {csv_file}")

        jobs = parse_csv(csv_path)
        print(f"  Found {len(jobs)} job listings")

        for job in jobs:
            url = job.get("linkedin_url", "")

            # Dedup
            if url and url in existing_urls:
                total_dupes += 1
                continue

            if not job["job_title"]:
                total_skipped += 1
                continue

            if dry_run:
                folder = make_folder_name(job["posted_on"], job["company_name"], job["job_title"])
                print(f"  [DRY RUN] Would create: {folder}")
                total_created += 1
            else:
                folder = create_application(job, applications_dir, csv_path)
                created_folders.append(folder)
                if url:
                    existing_urls.add(url)
                total_created += 1
                print(f"  Created: {folder}")

        # Rename to .processed.csv
        if not dry_run:
            processed_path = csv_path.replace(".csv", ".processed.csv")
            os.rename(csv_path, processed_path)
            print(f"  Marked as processed: {csv_file}")

    # Write log
    log_content = {
        "run_at": now_iso(),
        "csvs_processed": csv_files,
        "jobs_created": total_created,
        "jobs_skipped": total_skipped,
        "duplicates_found": total_dupes,
        "folders_created": created_folders,
    }

    if not dry_run:
        log_file = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M") + ".yaml"
        save_yaml(os.path.join(logs_dir, log_file), log_content)

    # Summary
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Summary:")
    print(f"  CSVs processed: {len(csv_files)}")
    print(f"  Jobs created: {total_created}")
    print(f"  Duplicates skipped: {total_dupes}")
    print(f"  Invalid rows skipped: {total_skipped}")


if __name__ == "__main__":
    main()
