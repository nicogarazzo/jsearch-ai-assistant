# JSearch AI Assistant

A job search pipeline that runs on your own machine, driven from [Claude Code](https://claude.com/claude-code).

Drop in a list of job postings. It scores each one against your profile, drafts a tailored CV and cover letter for the ones worth your time, and tracks every application in a local dashboard. Your data stays in plain files in this repo.

It is not a bot that applies for you. Applying is always your call.

```
CSV or posting  ->  ingest  ->  score  ->  you review  ->  draft CV + letter  ->  you apply  ->  track
```

## Setup

**Requirements**

- [Claude Code](https://claude.com/claude-code)
- Python 3.8 or newer
- Optional: `pandoc` and `xelatex` (MacTeX or TeX Live) if you want PDFs

```bash
git clone https://github.com/nicogarazzo/jsearch-ai-assistant.git
cd jsearch-ai-assistant
pip install -r requirements.txt
```

**Build your profile**

Open Claude Code in the project and run the setup assistant:

```bash
claude
```

```
/setup-profile
```

It interviews you in seven blocks (identity, current role, experience, skills, education, search criteria, deal-breakers), then writes `config/profile.json` and expands it into the two config files the pipeline reads. If you already have a CV or a LinkedIn export, hand it over and it will fill most of the blocks for you.

Prefer to skip the interview? Copy the example and edit it:

```bash
cp config/profile.example.json config/profile.json
# edit config/profile.json
python3 scripts/import_profile.py
```

Either path ends the same way:

```
config/profile.json  --(scripts/import_profile.py)-->  config/profile.yaml
                                                       config/search-criteria.yaml
```

`profile.json` is the one file you ever edit. It is validated against `config/profile.schema.json`, so a typo gets you a line number, not a silent wrong answer. Re-run the importer after any change.

## Daily use

**1. Add job listings.** Drop a CSV into `inbox/clay-exports/`. Any export with column headers works. `Job Title` is the only required column; `Company Name`, `Location`, `Company Domain`, `Job LinkedIn URL` and `Posted On` are used when present. There is a working file in `examples/sample-jobs.csv` to try it with.

For a one-off posting, paste it into a text file in `inbox/manual/`.

**2. Process and score.**

```
/process-inbox
```

Each listing becomes a folder under `applications/`, gets fetched, scored 0 to 100, and written up in `analysis.md` with the reasoning and the ATS keywords it found. Then it shows you the top matches.

**3. Prepare the ones worth preparing.**

> Prepare application for Halcyon Data

You get `cv.md` and `cover-letter.md` tailored to that posting, in the language of the posting, plus PDFs if you have pandoc installed.

**4. Track.** Open `dashboard/index.html`. Kanban by status, sortable table, response and interview rates.

> Mark Halcyon Data as applied

## How scoring works

Every listing gets 0 to 100 across five dimensions. Weights live in `config/settings.yaml`.

| Dimension | Weight | What it measures |
|---|---|---|
| Role match | 30% | Title and seniority against your target titles |
| Skills match | 25% | Required skills against yours, plus bonus signals |
| Industry fit | 15% | Preferred, acceptable, or on your avoid list |
| Location and remote | 15% | Geographic and remote compatibility |
| Company signals | 15% | Size, stage, culture signals |

Anything matching a `deal_breakers` entry is capped at 30 regardless of the rest.

**85+** excellent, prepare it. **70 to 84** good, worth a look. **50 to 69** moderate. **Below 50** skip.

Statuses run `new` > `analyzed` > `preparing` > `ready` > `applied` > `follow_up` > `response` > `interview` > `offer` | `rejected` | `withdrawn`.

## Guardrails

The generated documents are only useful if they are true, so the honesty rules are part of the contract, not a disclaimer:

- Nothing gets written that is not in your profile. No invented skills, titles, dates or numbers.
- When you are genuinely short of a requirement, the analysis says so instead of papering over it.
- `narrative_rules.fact_guards` in your profile pins each number to one employer, so a figure from a past job never quietly migrates into a paragraph about your current one. This is the most common way a tailored CV turns into a false one.
- `narrative_rules.lead_with_company` and `de_emphasize_companies` control which employer opens the story.
- `narrative_rules.style_bans` is honored literally. Put your own pet peeves there.
- Nothing is ever marked as applied for you.

## Running it unattended

`scripts/daily_scan.sh` ingests, scores, and prepares anything above your `auto_prepare_threshold`, then stops. It exits early without calling the model when there is nothing new, so scheduling it is cheap.

```bash
./scripts/daily_scan.sh
# JSEARCH_MODEL=opus JSEARCH_BUDGET=5.00 ./scripts/daily_scan.sh
```

Add it to cron or launchd for a weekday-morning run.

## What lives where

```
config/
  profile.json          Your data. The only file you edit. Gitignored.
  profile.schema.json   The contract profile.json is validated against.
  profile.example.json  A filled-in example to copy from.
  settings.yaml         Scoring weights, batch size, dashboard theme.
inbox/
  clay-exports/         Drop CSVs here.
  manual/               Drop single postings here.
applications/           One folder per job. Gitignored.
dashboard/index.html    Generated, self-contained, no external requests.
templates/              Base CV and cover letter.
scripts/
  import_profile.py     profile.json -> the two config YAMLs.
  process_inbox.py      CSV -> application folders.
  generate_dashboard.py Rebuild the dashboard.
  generate_pdf.py       Markdown -> PDF via pandoc and xelatex.
  daily_scan.sh         Unattended run.
logs/runs/              Timestamped execution logs.
```

Python is standard library plus PyYAML. Every path is relative to the project root. `CLAUDE.md` holds the full behavior spec the assistant follows, and it is worth reading if you want to change how scoring or drafting works.

## Privacy

Everything runs locally. `config/profile.json`, `applications/`, `inbox/` and `dashboard/index.html` are gitignored, so a `git push` from your fork cannot leak your CV or your job search. Job postings are fetched from the web when you ask for analysis; nothing about you is uploaded anywhere Claude Code does not already go.

One leak the gitignore cannot stop: GitHub issues and comments. If you fork this repo publicly, do not track your applications in its issues. Recruiter names, salary numbers and negotiation notes there are public, and editing them leaves the old text in the edit history. `CLAUDE.md` tells the assistant never to do it.

## License

MIT. See [LICENSE](LICENSE).
