---
description: Interview the user and build their JSearch profile
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

Run the JSearch setup interview described under "Setup flow" in CLAUDE.md.

Rules for this session:
- Ask one block at a time. Do not dump all seven blocks at once.
- Speak the user's language.
- If they have a CV or LinkedIn export, offer to read it and extract blocks 2
  through 5, then confirm what you found instead of asking them to retype it.
- Push for numbers in every achievement. An achievement without a number is a
  sentence a recruiter skips.
- Write `config/profile.json` only, validated against
  `config/profile.schema.json`. Then run:
  `python3 scripts/import_profile.py --force`
- Never write `config/profile.yaml` or `config/search-criteria.yaml` by hand.
- Never invent a fact the user did not give you. Leave a field out instead.

$ARGUMENTS
