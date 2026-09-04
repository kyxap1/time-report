# work-report

A Claude Code skill that builds a paste-ready monthly timesheet. You name a month; it gathers your
GitHub PRs/commits in your configured org, your own Slack activity and your Google Calendar
meetings, reconciles everything by your local date, and writes `report-<month>.txt`. A spreadsheet
notes file is optional.

The skill lives in `.claude/skills/work-report/`.

## Prerequisites

- **Python 3.9+** — runs the scripts (standard library only, no installs).
- **GitHub access — one of:**
  - an authenticated **`gh` CLI** with access to your org's private repos (`gh auth status`) — used
    by the bundled `fetch_github.py`; **or**
  - the **GitHub MCP server** connected — there's no script path for it, so the skill (the agent)
    queries PRs/commits through `mcp__github__*` itself and does the timezone math by hand. Works,
    just slower and more token-heavy than `gh`.
- **Slack MCP server connected — required** for the Slack step. There is no script for Slack; the
  skill reads your own messages (incl. private DMs) directly via `mcp__claude_ai_Slack__*`,
  read-only. Without it, the report is built from GitHub + notes only and misses non-PR work
  (reviews, investigations, helping teammates, dashboards).
- **Google Calendar MCP server connected — required** for the meetings step. The skill lists your
  own calendar events for the period (read-only) so days spent in meetings get honest hours instead
  of looking empty. Zoom calls are covered only as their calendar invites — there is no Zoom MCP, so
  an ad-hoc Zoom with no invite stays invisible. Note this connector needs OAuth twice: once via
  `/mcp`, then once more through the link the first calendar call returns.
- **`config.json`** in the skill dir — set your `github_org` (copy from `config.example.json`).
  Stays local, not committed.
- *(optional)* **Atlassian and Linear MCP servers** — when connected, the skill also reads your
  Jira / Confluence / Linear activity for the period (read-only) as extra context for what each day
  was spent on; ticket/page events themselves never appear as report lines.
- *(optional)* **notes file** — rows of `date · hours · note`; adds your logged hours and task hints.

Connect the GitHub, Slack and Google Calendar MCP servers in your Claude setup before running
(check with `/mcp`). Your GitHub user and Slack ID are auto-detected.

## Use

Ask for the month, e.g. *"build my time report for June"*. You get `report-<month>.txt` plus a
summary of judgment calls. Load it with `pbcopy < report-june.txt`, then paste at the first Date
cell in your sheet. Point it at a notes file if you have one.
