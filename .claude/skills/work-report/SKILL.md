---
name: work-report
description: >-
  Generate or update a monthly work-time report (timesheet) for a given month. Given a target
  month (e.g. "build my time report for June"), this skill automatically gathers the user's GitHub
  PRs and commits in their configured GitHub org, mines their own Slack messages (including
  private DMs) for the period, and (when connected) reads their Jira, Confluence, and Linear
  activity as read-only context signals, reconciles everything by the configured local date (default
  America/New_York), and writes a paste-ready tab-separated report file plus a short summary of
  judgment calls. An optional spreadsheet notes file (rows of date, logged hours, short task notes)
  is used when provided to supply authoritative logged hours and task hints, but is NOT required to
  run. Use this whenever the user wants to build, assemble, fill in, or update their monthly work
  report / timesheet / "time report" / "work report" for a month, or hands over hours+notes to
  format. Trigger even if they don't say "skill" — phrases like "build my time report for jun",
  "assemble my monthly timesheet", "turn my hours notes into the report", "what did I work on this
  month for the report" all apply. Do not trigger for ad-hoc GitHub or Slack lookups unrelated to
  building the report.
---

# Work report builder

Turn a month of real activity into a complete, audit-safe work report by pulling in what the user
actually did (GitHub + Slack) and writing it in the exact paste-ready format their spreadsheet
expects.

The user names the month; everything else is automatic. A spreadsheet notes file is optional —
when present it supplies the user's logged hours and task hints; without it, hours are estimated
from activity and flagged for the user to confirm.

The exact output format and all the writing/hours rules live in **`references/format-spec.md`** —
read it in full before assembling the report; it is the spec, not background reading.

## Configuration

Read `config.json` in the skill directory for the org-specific settings (it is kept local and not
committed — see `config.example.json` for the shape):

```json
{ "github_org": "your-org", "timezone": "America/New_York" }
```

- `github_org` — the GitHub org all PR/commit searches are scoped to. **Required.** If `config.json`
  is missing, ask the user for the org once and offer to save it.
- `timezone` — IANA zone for every report date (default `America/New_York`).

Identity is auto-detected, not configured: the GitHub user via `gh api user -q .login`, and the
Slack user is whoever is logged in (the Slack search tool reports the current `user_id`). Mine only
the user's OWN messages.

## What this produces

A tab-separated file `report-<month>.txt` (e.g. `report-june.txt`) that the user copies
(`pbcopy < report-june.txt`) and pastes into their sheet — one row per weekday, columns
**Date | Hours | Work Type | Description** — plus a short chat summary of judgment calls (filled
days, blank days, days left for the user to fill).

## Process

Work through these in order. Steps 3–5 are independent — run them in parallel.

### 1. Establish the month, then read any notes file

Determine the report month from the user's request (e.g. "June"). Load `config.json` for the org
and timezone.

If the user provided a spreadsheet notes file, parse it — it is TSV-ish:
`date <tab> hours <tab> [work type] <tab> notes`. Build a map `{local_date: {hours, work_type,
notes}}`. Treat the user's **logged hours as sacred** — they are paid, audited time. Note which
days are blank (no hours) and which carry a weekly rollup (one day logged with a large number and a
note like "worked all week on X").

If there is **no notes file**, that's fine: derive the days and hours entirely from GitHub + Slack
activity (see the hours rules), and flag the whole Hours column in the summary so the user can
confirm — nothing is user-verified in that case.

### 2. Set the period window

Search a little wider than the month so timezone-shifted edge work is caught: `since = first day of
month minus 1`, `until = last day of month plus 1` (or today, if the month is current).

### 3. Gather GitHub activity (run the script)

```bash
python scripts/fetch_github.py --since 2026-06-01 --until 2026-06-30 > _cctmp.gh.json
```

It reads the org + timezone from `config.json`, searches PRs the user authored in the org
(created/merged/updated in range), pulls each PR's commits, and separately searches PRs the user
**reviewed** (including other people's PRs) to pull the actual review state (approved / changes
requested / commented) and date from each review. It shifts every timestamp to the configured
zone and emits JSON with per-PR dates, a top-level `reviews` list, and a `by_date` index of what
happened each local day (`kind: "commit"` or `kind: "review"`). If `gh` is not authenticated it
exits with a message — in that case use the GitHub MCP tools instead: `search_pull_requests` with
`author:<user> org:<github_org> created:.. / merged:.. / updated:..` for authored PRs, and
`reviewed-by:<user> org:<github_org> updated:..` for reviewed PRs, then `pull_request_read` method
`get_commits` (authored) or `get_reviews` (reviewed, filter to entries by `<user>`), and shift all
dates to the configured zone yourself.

### 4. Mine Slack (always; read-only)

Mine the user's own messages for the period to capture work that never shows up in a PR —
investigations, reviews of other people's PRs, dashboard work, helping teammates, deploy
coordination, decisions. This is high-value: it's the difference between "what got merged" and
"what the day was actually spent on".

- **Read-only. Never post, reply, react, or schedule anything in Slack.**
- Load `mcp__claude_ai_Slack__slack_search_public_and_private`. Search
  `from:<@SELF> after:<start-1d> before:<end+1d>`, sort by timestamp, **paginate through every
  page** (follow the `pagination_info` cursor). Include private channels and DMs.
- Timestamps render in the user's local zone — bucket each message by that date.
- A month is a lot of messages. To keep your own context clean, fan out: spawn 2+ read-only
  subagents, each covering a slice of the date range, each returning a per-day digest of
  work-relevant bullets (with PR links and named collaborators). Tell them to ignore social chatter
  and to never post to Slack.

### 5. Pull Jira / Confluence / Linear signals (context only; read-only)

Widen the view with the user's tracker and wiki activity for the period — a day spent triaging
Jira tickets, writing a Confluence page, or grooming Linear issues often leaves no PR or Slack
trace. These are **observability signals for your analysis, not report content**: they tell you
what a day was about and corroborate hours, but ticket/page events never become their own bullets
(see the rule in `references/format-spec.md`).

- **Jira** — the Atlassian MCP `searchJiraIssuesUsingJql`, e.g.
  `(assignee = currentUser() OR reporter = currentUser()) AND updated >= "<since>" AND updated <= "<until>"`.
- **Confluence** — the Atlassian MCP `searchConfluenceUsingCql` with
  `contributor = currentUser() and lastmodified >= "<since>" and lastmodified <= "<until>"`.
- **Linear** — the Linear MCP tools: list issues updated in the window where the user is assignee
  or creator.

Bucket what you find into a short per-day digest (issue keys, page titles, what changed). If a
server isn't connected, skip it and move on — these sources are optional enrichment, not a
required input.

### 6. Reconcile everything by local date

For each day, merge the available sources: notes (authoritative for hours + intent, when present),
GitHub (authoritative for what shipped, what was reviewed, and dates), Slack (activities not in
PRs), plus the Jira/Confluence/Linear digest as background — it sharpens descriptions and hours
judgment but contributes no bullets of its own. Collapse to the **subject of work**, not commit
minutiae. Apply the writing and hours rules in
`references/format-spec.md` exactly — they encode the required verb tone, altitude, honesty about
hours, and how to handle forgotten/light/empty days, weekly rollups, and holidays.

### 7. Build the file (run the script)

Produce a JSON array of day entries and hand it to the formatter so the tab/quote format is always
correct:

```bash
python scripts/build_report.py --input _cctmp.days.json --output report-june.txt
```

Each entry: `{"date":"6/9/2026","hours":"8.00","work_type":"","lines":["- worked on ...","- created https://github.com/your-org/repo/pull/123"]}`.
- Write each line in `lines` exactly as it should read in the cell, including the leading `- `. The
  formatter joins them with newlines and wraps the cell — it does not add dashes. (A holiday row is
  `"lines":["holiday"]`.)
- Empty hours → `"hours":""`. Light-day marker → `"work_type":"review"` (etc.). Truly empty day →
  `{"date":"6/15/2026"}` with no hours/work_type/lines.

### 8. Deliver

Tell the user the file is ready and how to use it (`pbcopy < report-<month>.txt`, paste at the first
date cell). Then give a short summary of judgment calls: which forgotten days you filled and why,
which days you left blank for them to fill (light/uncertain), any weekly rollup you spread, and any
borderline hours worth their eye. Honesty here matters — these reports are audited.

## Guardrails

- **Configured org only.** Drop personal/other-org repos from the report (mention them once if
  found, don't list them).
- **Slack is read-only.** Searching and reading is fine; sending anything is not.
- **Jira, Confluence, and Linear are read-only, context-only.** Never create, edit, comment on, or
  transition anything there, and never report ticket/page events as tasks in the report.
- **Hours are paid time — never inflate and never reduce.** Don't round a light day up to 8h. Don't
  invent hours for days with little visible work; give a conservative estimate plus a Work Type
  marker, or leave blank for the user. See `references/format-spec.md`.
