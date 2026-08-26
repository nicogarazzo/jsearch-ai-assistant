---
description: Ingest, score and report new job listings
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch
---

Run the "Process my inbox" flow from CLAUDE.md end to end:

1. `python3 scripts/process_inbox.py`
2. Handle anything in `inbox/manual/` by hand, same folder shape.
3. Score every folder that has `job.yaml` but no `analysis.md`, using the
   scoring system in CLAUDE.md. Fetch the full posting first when a URL exists.
4. `python3 scripts/generate_dashboard.py`
5. Report the top matches by score, plus anything that hit a deal-breaker.

Respect `narrative_rules` in `config/profile.yaml`. Do not prepare materials
unless asked, and never mark anything as applied.

$ARGUMENTS
