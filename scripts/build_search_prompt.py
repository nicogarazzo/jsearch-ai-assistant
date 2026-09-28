#!/usr/bin/env python3
"""
JSearch search prompt builder.

Turns config/search-criteria.yaml into ready-to-paste prompts that build a job
list, so you do not need a job board API:

    search-prompts/clay.md        For Clay (Claygent / AI column), if you have it.
    search-prompts/web-search.md  For any LLM with web search (Claude, ChatGPT,
                                  Gemini, Perplexity...), if you do not.

Both ask for the answer as CSV with the exact headers process_inbox.py reads,
so the result goes straight into inbox/clay-exports/.

Usage:
    python3 scripts/build_search_prompt.py              # write both files
    python3 scripts/build_search_prompt.py --print web  # also print one
    python3 scripts/build_search_prompt.py --count 40   # listings per batch

Run from the project root. Requires PyYAML.
"""

import argparse
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import get_project_root, load_yaml

CSV_HEADERS = "Company Name,Job Title,Location,Company Domain,Job LinkedIn URL,Posted On,Employee Count"


def bullets(items):
    items = [str(i) for i in (items or []) if str(i).strip()]
    return "\n".join(f"- {i}" for i in items) if items else "- (none given)"


def criteria_block(c):
    roles = c.get("target_roles", {}) or {}
    ind = c.get("target_industries", {}) or {}
    loc = c.get("location_preferences", {}) or {}
    comp = c.get("company_preferences", {}) or {}
    size = comp.get("size", {}) or {}
    size_txt = ", ".join(
        f"{k.replace('_employees', '')} {v}" for k, v in size.items() if v
    ) or "any"
    return f"""Target titles:
{bullets(roles.get('titles'))}

Seniority: {', '.join(roles.get('seniority') or []) or 'any'}

Preferred industries:
{bullets(ind.get('preferred'))}

Acceptable industries:
{bullets(ind.get('acceptable'))}

Industries to exclude:
{bullets(ind.get('avoid'))}

Preferred locations:
{bullets(loc.get('preferred_locations'))}

Acceptable regions:
{bullets(loc.get('acceptable_regions'))}

Company size (employees): {size_txt}

Deal-breakers, exclude any listing that hits one:
{bullets(c.get('deal_breakers'))}

Nice to have (rank these higher):
{bullets(c.get('bonus_signals'))}"""


def web_prompt(c, count, since):
    return f"""You are helping me build a list of open jobs to apply to. Use web search.
Only include listings you actually opened and saw open, posted on or after {since}.
Never invent a company, a title, a URL or a date. If you cannot verify a field,
leave it empty.

{criteria_block(c)}

Where to look: company career pages, LinkedIn Jobs, Wellfound, Greenhouse,
Lever, Ashby, Workable, and communities or niche boards for these roles.
Prefer the original posting URL over an aggregator copy.

Return up to {count} listings as CSV in one code block, with exactly this
header row and nothing else inside the block:

{CSV_HEADERS}

Rules for the CSV:
- Quote any field that contains a comma.
- "Job LinkedIn URL" holds the posting URL, even if it is not LinkedIn.
- "Posted On" in YYYY-MM-DD.
- "Company Domain" as example.com, no https://.
- One row per listing, no duplicates.

After the block, list in one line each any listing you excluded for a
deal-breaker and why.

This is a conversation, not a single answer. When I say "more", search again
and return the next batch in the same format, never repeating a URL you
already gave me. When I say "narrow to X" or "drop Y", apply it to the next
batch."""


def clay_prompt(c, count, since):
    roles = (c.get("target_roles", {}) or {}).get("titles") or []
    loc = c.get("location_preferences", {}) or {}
    return f"""Clay setup (two steps):

1. Find jobs. In a new Clay table use "Find Jobs" (or the LinkedIn Jobs source)
   with these filters:
   - Job titles: {', '.join(roles) or '(set your titles)'}
   - Locations: {', '.join((loc.get('preferred_locations') or []) + (loc.get('acceptable_regions') or [])) or 'any'}
   - Posted after: {since}
   - Limit: {count}

2. Qualify each row. Add an AI column (Claygent) with the prompt below, then
   filter out rows where it answers EXCLUDE.

---

Read this job posting: /Job LinkedIn URL
Company: /Company Name   Title: /Job Title   Location: /Location

Decide if it fits this candidate's criteria.

{criteria_block(c)}

Answer with one word on the first line, KEEP or EXCLUDE, then one line saying
why. Answer EXCLUDE if any deal-breaker applies or the industry is on the
exclude list. Do not guess: if the posting does not say, treat it as unknown,
not as a match.

---

3. Export. Keep these columns, named exactly like this, and export as CSV
   into inbox/clay-exports/:

{CSV_HEADERS}

Then run /process-inbox in Claude Code."""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--count", type=int, default=25, help="listings per batch")
    ap.add_argument("--days", type=int, default=21, help="only postings this recent")
    ap.add_argument("--print", choices=["web", "clay"], dest="show")
    args = ap.parse_args()

    root = get_project_root()
    crit_path = os.path.join(root, "config", "search-criteria.yaml")
    if not os.path.exists(crit_path):
        print("No config/search-criteria.yaml yet. Run /setup-profile first,")
        print("or: python3 scripts/import_profile.py")
        return 1
    c = load_yaml(crit_path) or {}
    since = (date.today() - timedelta(days=args.days)).isoformat()

    out_dir = os.path.join(root, "search-prompts")
    os.makedirs(out_dir, exist_ok=True)
    files = {
        "web": ("web-search.md", web_prompt(c, args.count, since)),
        "clay": ("clay.md", clay_prompt(c, args.count, since)),
    }
    for key, (name, text) in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"Wrote search-prompts/{name}")

    if args.show:
        print("\n" + files[args.show][1])
    print("\nPaste one into Clay or any LLM, save the CSV it returns in")
    print("inbox/clay-exports/, then run /process-inbox.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
