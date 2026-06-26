# work-report

A Claude Code skill that builds a paste-ready monthly timesheet. You name a month; it gathers your
GitHub PRs/commits in your configured org plus your own Slack activity, reconciles everything by
your local date, and writes `report-<month>.txt`. A spreadsheet notes file is optional — when
present it supplies your logged hours and task hints.

The skill lives in `.claude/skills/work-report/`.

## Prerequisites

- **Python 3.9+** — runs the scripts (standard library only, no installs).
- **`gh` CLI authenticated** with access to your org's private repos — check with `gh auth status`.
- **Slack connector active** — mines your own messages incl. private DMs, read-only.
- **`config.json`** in the skill dir — set your `github_org` (copy `config.example.json`). Kept
  local, not committed.
- *(optional)* **spreadsheet notes file** — rows of `date · hours · note`; adds your logged hours
  and task hints.

Your GitHub user and Slack ID are auto-detected. The GitHub MCP works as a fallback if `gh` is missing.

## Use

Ask for the month, e.g. *"build my time report for June"*. You get `report-<month>.txt` plus a
summary of judgment calls. Load it into your sheet with `pbcopy < report-june.txt`, then paste at
the first Date cell. Point it at a notes file if you have one.
