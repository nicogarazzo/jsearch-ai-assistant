---
description: Build a job list from your profile, with Clay or any LLM
allowed-tools: Read, Write, Bash, WebSearch, WebFetch
---

Run the "Build my job list" flow from CLAUDE.md.

1. `python3 scripts/build_search_prompt.py`
2. Ask the user one question: do they have Clay?
   - Yes: show `search-prompts/clay.md` and walk them through it.
   - No: show `search-prompts/web-search.md` and say it works in any LLM with
     web search. Offer to run it here instead with WebSearch, writing the
     result as a CSV into `inbox/clay-exports/`.
3. When a CSV lands in `inbox/clay-exports/`, offer to run /process-inbox.

Never invent a listing. Every row needs a URL that was actually opened.

$ARGUMENTS
