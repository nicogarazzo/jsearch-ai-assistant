#!/bin/bash
# JSearch daily scan. Run manually, from cron, or from launchd.
#
#   ./scripts/daily_scan.sh
#
# It skips the Claude invocation entirely when there is nothing new to do,
# so scheduling it every weekday morning is cheap.

set -uo pipefail

JSEARCH_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${JSEARCH_DIR}/logs/runs"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M)
LOG_FILE="${LOG_DIR}/scan_${TIMESTAMP}.log"

# Override with: JSEARCH_MODEL=opus JSEARCH_BUDGET=5.00 ./scripts/daily_scan.sh
MODEL="${JSEARCH_MODEL:-sonnet}"
BUDGET="${JSEARCH_BUDGET:-2.00}"

mkdir -p "$LOG_DIR"

echo "=== JSearch daily scan: $(date) ===" | tee "$LOG_FILE"
echo "Project: ${JSEARCH_DIR}" | tee -a "$LOG_FILE"

if [ ! -f "${JSEARCH_DIR}/config/profile.yaml" ]; then
    echo "No config/profile.yaml yet. Run the setup assistant first:" | tee -a "$LOG_FILE"
    echo "  claude   then say: Set up my JSearch profile" | tee -a "$LOG_FILE"
    exit 1
fi

# Count work before paying for a model call
NEW_CSVS=$(find "${JSEARCH_DIR}/inbox/clay-exports" -name "*.csv" ! -name "*.processed.csv" 2>/dev/null | wc -l | tr -d ' ')
NEW_MANUAL=$(find "${JSEARCH_DIR}/inbox/manual" -type f ! -name ".gitkeep" ! -name "*.processed*" 2>/dev/null | wc -l | tr -d ' ')
UNANALYZED=$(find "${JSEARCH_DIR}/applications" -name "job.yaml" -exec sh -c 'dir=$(dirname "$1"); [ ! -f "$dir/analysis.md" ] && echo "$dir"' _ {} \; 2>/dev/null | wc -l | tr -d ' ')

if [ "$NEW_CSVS" -eq 0 ] && [ "$NEW_MANUAL" -eq 0 ] && [ "$UNANALYZED" -eq 0 ]; then
    echo "Nothing new. Regenerating the dashboard only." | tee -a "$LOG_FILE"
    (cd "$JSEARCH_DIR" && python3 scripts/generate_dashboard.py) >> "$LOG_FILE" 2>&1
    echo "Done." | tee -a "$LOG_FILE"
    exit 0
fi

echo "Found ${NEW_CSVS} CSV(s), ${NEW_MANUAL} manual posting(s), ${UNANALYZED} unanalyzed job(s)" | tee -a "$LOG_FILE"

claude -p \
    --model "$MODEL" \
    --max-budget-usd "$BUDGET" \
    --permission-mode auto \
    --allowedTools "Bash Read Write Edit Glob Grep WebFetch WebSearch" \
    "You are the JSearch assistant. Working directory: ${JSEARCH_DIR}

Follow CLAUDE.md in that directory and run the pipeline unattended:

1. cd to ${JSEARCH_DIR}
2. INGEST: python3 scripts/process_inbox.py
3. ANALYZE: for every application folder that has job.yaml but no analysis.md,
   read config/profile.yaml and config/search-criteria.yaml, fetch the full
   posting from its URL with WebFetch, score it 0-100 using the scoring system
   in CLAUDE.md, then write analysis.md and set status.yaml to analyzed.
   Respect narrative_rules.fact_guards in profile.yaml: never move a number
   from one employer to another, and never invent experience.
4. python3 scripts/generate_dashboard.py
5. For jobs at or above search-criteria.yaml > auto_prepare_threshold, generate
   cv.md and cover-letter.md in the language of the posting, then run
   python3 scripts/generate_pdf.py --cover-letters
6. Print a summary: new listings, top 5 by score, deal-breakers hit.

Never mark anything as applied. Applying is always the user's action." \
    2>&1 | tee -a "$LOG_FILE"

echo "=== Scan complete: $(date) ===" | tee -a "$LOG_FILE"
