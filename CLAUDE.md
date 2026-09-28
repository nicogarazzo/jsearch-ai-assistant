# JSearch AI Assistant

## What this project is
A semi-automated job search pipeline driven from Claude Code. It ingests job
listings (CSV export or a pasted posting), scores each one against the user's
profile, drafts tailored application materials, and tracks status in a local
HTML dashboard. Everything lives in plain files in this repo. Nothing is sent
anywhere the user did not send it.

## Directory contract
```
config/         Profile and preferences. profile.json is the source of truth.
inbox/          Input. clay-exports/ for CSVs, manual/ for pasted postings.
applications/   Output. One folder per job.
dashboard/      Generated HTML dashboard (single self-contained file).
templates/      Base CV and cover letter templates.
scripts/        Python. Standard library plus PyYAML, nothing else.
logs/runs/      Timestamped execution logs.
```

## Configuration model
`config/profile.json` is the single source of truth, validated by
`config/profile.schema.json`. The pipeline reads two generated YAML files:

```
config/profile.json  --(scripts/import_profile.py)-->  config/profile.yaml
                                                       config/search-criteria.yaml
```

Never hand-edit the generated YAML. Edit `profile.json` and re-run the importer.
`config/settings.yaml` is separate and hand-edited: scoring weights, batch size,
dashboard theme.

## Core commands

### "Set up my JSearch profile"
Run the setup interview. See the Setup Flow section at the bottom.

### "Process my inbox" / "Check for new jobs"
1. `python3 scripts/process_inbox.py` (add `--dry-run` to preview)
2. For each folder created with status `new`, analyze it against the profile:
   fetch the full posting from its URL with WebFetch when one exists, otherwise
   use whatever text the folder has.
3. Score 0 to 100 using the scoring system below.
4. Write `analysis.md`: score, per-dimension breakdown, reasoning, ATS keywords,
   gaps, and how to frame them honestly.
5. Set `status.yaml` to `analyzed`.
6. `python3 scripts/generate_dashboard.py`
7. Present the top matches sorted by score.

Postings dropped as text files in `inbox/manual/` are not handled by the Python
script. Read them, create the application folder by hand following the naming
convention, write `job.yaml` and `status.yaml` in the same shape the script
produces, then rename the source to `*.processed.txt`.

### "Prepare application for {company}" / "Prepare top N"
1. Read the folder's `job.yaml` and `analysis.md`.
2. Read `config/profile.yaml` and the templates.
3. Extract 10 to 15 ATS keywords: must-have, strong-signal, nice-to-have.
4. Write `cv.md` and `cover-letter.md`.
5. `python3 scripts/generate_pdf.py {company} --cover-letters`
6. Set `status.yaml` to `ready` and flip the materials flags.
7. `python3 scripts/generate_dashboard.py`

### "Generate PDFs"
`python3 scripts/generate_pdf.py --cover-letters`, or scope it to one company by
passing a partial folder name. Requires pandoc and xelatex.

### "Mark {company} as applied" / "Update {company} status to {status}"
Update `status.yaml`, append a timeline entry, regenerate the dashboard.

### "Refresh dashboard"
`python3 scripts/generate_dashboard.py`

## Scoring system
Fit score is 0 to 100 across five dimensions. Weights live in
`config/settings.yaml`; the point ceilings below assume the defaults.

**Role match (30).** Compare the job title to `search-criteria.yaml >
target_roles.titles`. Exact match 30. Semantic match 20. Partial keyword overlap
10. No title match but skills align 5.

**Skills match (25).** Extract required skills from the posting and compare
against every category in `profile.yaml > skills`.
`score = (matched / required) * 25`, with a floor of 5 if anything matched. Add
3 for each `bonus_signals` hit, capped at 25.

**Industry fit (15).** Preferred 15. Acceptable 10. Unlisted 7. On the avoid
list 0.

**Location and remote (15).** Remote when the user wants remote 15. Preferred
location 15. Acceptable region 10. Neither, but no deal-breaker 5. Excluded
location 0.

**Company signals (15).** Size in range 5. Stage matches 5. Positive culture
signals +3. Negative culture signals -3. Bonus signals +2 each, capped at 5.

**Deal-breaker override.** If any entry in `deal_breakers` matches, cap the
score at 30 and force the tier to low, whatever the dimensions said.

**Tiers.** 85 to 100 excellent, auto-recommend preparation. 70 to 84 good,
recommend review. 50 to 69 moderate. Below 50 low, skip unless the user
disagrees.

## Status lifecycle
`new` > `analyzed` > `preparing` > `ready` > `applied` > `follow_up` >
`response` > `interview` > `offer` | `rejected` | `withdrawn`

## Writing application materials

**Language.** In priority order: an explicit request from the user; the language
of the posting; the country of the company when the posting has no English; then
`search-criteria.yaml > materials_language`. Record the choice in `job.yaml`
under `language`.

**CV.** Professional summary carrying the top ATS keywords. Work history
reordered so the relevant experience reads first. Skills section mirroring the
posting's own vocabulary. Never a skill the profile does not list.

**Cover letter.** Open with a quantified achievement, not a greeting about
excitement. Body maps three or four stated requirements to specific evidence
from the profile. Close with genuine interest and availability. Direct and
credible, no filler.

**Honesty rules, non-negotiable.**
- Never invent or inflate experience, a skill, a title, a date, or a number.
- Every claim must trace to something in `profile.yaml`.
- When the profile is genuinely short of a requirement, say so in `analysis.md`
  and frame the nearest real evidence. Do not paper over it.
- Never mark anything as applied on the user's behalf. Applying is their action.

**Profile-driven guardrails.** `profile.yaml > narrative_rules` is binding when
present:
- `lead_with_company`: every narrative opens with this employer.
- `de_emphasize_companies`: brief historical context only, never the closing
  point of a paragraph.
- `fact_guards`: each `claim` belongs to exactly one `owner`. Never move a
  number from one employer to another. This is the most common way these
  documents become false.
- `style_bans`: things never to write, honored literally.

**Age.** Only when a form explicitly asks. Compute it from
`profile.yaml > birth_date` and today's date, subtracting one if the birthday
has not yet occurred this year. Never hardcode an age. Never volunteer it in a
CV or cover letter.

## Data enrichment
When `job.yaml` has a company domain and the user asks, or while preparing an
application, use WebFetch on the careers or about page and WebSearch for recent
news. Store the result under `enrichment` in `job.yaml`. Do not enrich the whole
inbox unprompted; it is slow and mostly wasted.

## CSV parsing
Exports vary. The parser maps by column name, never by position, and tolerates
missing optional columns. Recognized names, with aliases, are in `COLUMN_MAP` in
`scripts/process_inbox.py`. The useful ones are Company Name, Job Title,
Location, Company Domain, Job LinkedIn URL and Posted On; only Job Title is
strictly required. UTF-8 with BOM, Latin-1 fallback. Duplicates are detected by
job URL. Processed files are renamed to `*.processed.csv`.

## Engineering rules
- Every path relative to the project root. No absolute paths, ever.
- Python is standard library plus PyYAML.
- The dashboard stays a single self-contained HTML file, no external requests.
- Dates in ISO 8601. YAML at 2-space indentation.
- `config/profile.json` and everything under `applications/` is the user's
  private data. Never commit it, never send it anywhere.
- The same data never goes into GitHub issues, PR descriptions or comments on
  this repo or a fork of it. Recruiter names, emails, salary figures and
  negotiation notes posted there are public on a public repo, and an edit keeps
  the old text in the edit history. When a session has no access to
  `applications/`, it hands the status update to the user in chat, not to an
  issue.

## Setup flow
Run when the user says "Set up my JSearch profile" or invokes `/setup-profile`.

Interview in seven blocks. Ask one block at a time, in the user's language, and
accept a pasted CV or LinkedIn export as a shortcut for blocks 2 through 5
rather than making them retype it. Confirm what you extracted before moving on.

1. **Identity.** Name, email, phone, location, LinkedIn, website, GitHub,
   languages and levels. Birth date only if they want age-asking forms handled;
   say it is optional and stays local.
2. **Current role.** Title, company, industry, years in role, total years of
   experience.
3. **Experience.** Iterate role by role until they say done. For each: company,
   title, period, location, achievements. Push for numbers. "Improved
   onboarding" is worth nothing; "cut onboarding from 5 days to 2" is the whole
   point.
4. **Skills.** Let them list freely, then sort into technical, domain, tools and
   soft yourself.
5. **Education and certifications.**
6. **Search criteria.** Target titles, seniority, industries preferred and to
   avoid, locations, company size and stage, culture signals, bonus signals.
7. **Deal-breakers and guardrails.** Absolute no-gos. Then the narrative rules:
   which employer must lead, which to keep brief, and which numbers belong to
   which employer.

Then:
- Draft `professional_summary` from what they told you, three to six sentences,
  and read it back for approval.
- Write `config/profile.json` against `config/profile.schema.json`.
- Run `python3 scripts/import_profile.py --force`.
- If the importer reports problems, fix `profile.json` and re-run. Do not edit
  the generated YAML to make an error go away.
- Confirm what was written and point them at the next step: drop a CSV in
  `inbox/clay-exports/` and say "Process my inbox".

Use `config/profile.example.json` as the shape reference. Never copy its content
into a real profile.
