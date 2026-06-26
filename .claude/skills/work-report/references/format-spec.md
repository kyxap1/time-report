# Format & rules spec

This is the contract for the report. The output is pasted straight into a spreadsheet and the
report is audited, so both the mechanical format and the honesty rules matter.

## Table of contents
1. File format (TSV, paste behavior)
2. Description rules (altitude, verbs, what to leave out)
3. Hours rules (the audited part — read carefully)
4. Dates, timezone, which days appear
5. Worked examples

---

## 1. File format

Tab-separated, one row per weekday. Four columns:

| Col | Field | Notes |
|-----|-------|-------|
| A | Date | `M/D/YYYY`, no leading zeros (`6/1/2026`, not `06/01/2026`) |
| B | Hours | decimal like `8.00`, or empty |
| C | Work Type | usually empty; a marker word for light days (see §3) |
| D | Description | multi-line bullets, wrapped in double quotes |

The literal layout of a normal row is `date<TAB>hours<TAB><TAB>"description"` — note the two
consecutive tabs because Work Type is empty. The description cell is wrapped in `"..."` with real
newlines inside, which is what makes a multi-line cell paste into ONE spreadsheet cell instead of
spilling into new rows. Internal `"` are doubled (`""`). The `scripts/build_report.py` formatter
handles all of this — feed it JSON, don't hand-write the tabs (it's easy to get wrong).

Row shapes:
- Normal day: `6/9/2026⇥8.00⇥⇥"- worked on ...\n- created ..."`
- Light day with marker: `6/23/2026⇥3.00⇥review⇥"- investigated ..."`
- Holiday / no-hours but has a note: `6/19/2026⇥⇥⇥"holiday"`
- Truly empty day: `6/15/2026` (date only — see §3/§4)

Validated paste path: `pbcopy < report-<month>.txt`, then click the first Date cell in the sheet
and paste. Columns and multi-line cells land correctly.

---

## 2. Description rules

Each day is a **summary of what the person worked on** — a few high-altitude bullets, not a commit
log. Target **3–6 bullets per day**; a full day should read like a full day of substantive work.

**Altitude — describe the subject of work, not the mechanics.** The reader should understand what
the day was spent on. Avoid bullets that read like a commit diff or "changed 3 values in config A
and B". Collapse a day's many small commits into the thing they add up to.

- Good: `- optimized the integration-test CI pipeline`
- Bad:  `- bumped three cache keys and a runner image in the test workflow` (commit-level mechanics)

- Good: `- discussed test-data provisioning with Alex`
- Bad:  `- proposed a multi-year anonymized data slice to mirror prod in staging` (a single message dressed up as an accomplishment)

**Start each bullet with a verb**, not a repo or PR name. Put the link at the end of the line.
- Good: `- created https://github.com/your-org/service-b/pull/231`
- Bad:  `- service-b https://github.com/your-org/service-b/pull/231`

**No "merged" mentions.** Don't report merges as the work ("merged PR #X"). Report the work itself;
attach the PR link to the relevant bullet as context. `created https://...` and `reviewed
https://...` are fine.

**Name collaborators** when relevant — it reads as real, grounded work: `helped Sam with ...`,
`discussed ... with Alex`, `consulted Jordan on ...`.

**Verb tone — strong but not grandiose.** Use plain, factual verbs. Avoid loud, self-promotional
ones; they read as inflated in an audited report.
- Use: worked on, continued, started, prepared, built, implemented, configured, investigated,
  diagnosed, fixed, resolved, refactored, optimized, validated, hardened, enabled, standardized,
  reconciled, pinned, scoped, migrated, retired, finished, created, reviewed, experimented, helped,
  assisted, consulted, discussed, agreed to help.
- Avoid (too loud): drove, led, advanced, progressed, launched, spearheaded, championed,
  orchestrated, delivered (borderline — prefer finished/shipped/completed), volunteered (prefer
  "agreed to help").

**Links:** configured org only. Use full `https://github.com/<org>/<repo>/pull/<n>` URLs.

---

## 3. Hours rules (audited — get this right)

The hours are paid time and the reports are checked. Two unbreakable rules: **never reduce hours
the user actually logged**, and **never inflate** (no padding a light day to 8h, no inventing hours
for work that wasn't there). Lies get caught.

If **no notes file was provided**, there are no logged hours to anchor on — estimate every day from
activity using the rules below, and flag the whole Hours column in the summary so the user can
confirm or correct, since none of it is user-verified.

Decide each day's hours like this:

**a. Day has logged hours in the notes → use them verbatim.** Sacred. `4.00` stays `4.00`, `12.00`
stays `12.00`, `10.00` stays `10.00`. Do not normalize toward 8.

**b. Weekly rollup** (one day logged with a large number and a note like "worked all week on X"):
spread that total across the actual days it covers (the adjacent days that show commits/notes for
that work), e.g. 24h → `8 + 8 + 8` across three days. This conserves the total and stops a single
day from claiming an impossible figure. Sharing across **adjacent** days is the intended mechanism.

**c. Blank day, but there IS activity (commits / Slack / a note).** The user simply forgot to log
it — it is not a zero day. Fill it by fact:
   - Clear full day of substantive work (multiple PRs/commits, real Slack activity) → `8.00`.
   - Light or uncertain work (e.g. only a small revert plus an investigation, few commits, no clear
     deliverable) → **do not write 8h**. Put a conservative estimate in Hours and a marker word in
     **Work Type (C)** explaining the lighter load (e.g. `review`, `investigation`, `debugging`,
     `meetings`). Keeping the number in B keeps the sheet's TOTAL formula working. If you genuinely
     can't justify a number, leave Hours blank and flag the day in the summary for the user to fill
     — only they know how long the investigation took.

**d. Truly empty day — no commits, no Slack, no note.** Leave it empty: **the row must still exist
in the file** (so the structure is complete), but with date only, no hours, no description.

**e. Holiday.** Date + `"holiday"` in the description, no hours.

When in doubt between b/c/d, prefer honesty over completeness: a blank cell the user fills is better
than a fabricated 8.

---

## 4. Dates, timezone, which days appear

- **Every date is in the configured timezone** (default `America/New_York`). GitHub timestamps are
  UTC — shift them. A commit at `2026-06-10T02:00Z` is `6/9` in US Eastern, not `6/10`. The user's
  notes and Slack are already in their local zone. Getting this wrong puts work on the wrong day and
  contradicts the user's own records.
- **One row per weekday** of the month, in order. Empty weekdays still appear (date-only rows) so
  the markup is complete and aligns with the user's sheet.
- **Weekends** are omitted unless there was real activity that day (then include them).
- Mark **holidays** as `"holiday"`.

---

## 5. Worked examples

A normal full day reconciled from GitHub + Slack + notes:

```
6/9/2026	8.00		"- worked on the integration-test data provisioner https://github.com/your-org/service-a/pull/482
- created https://github.com/your-org/infra/pull/210 for the deploy-role permissions
- investigated how test users are seeded in the staging database
- helped Sam debug a canary deployment"
```

A light day — conservative hours + Work Type marker (no fabricated 8h):

```
6/23/2026	3.00	review	"- investigated intermittent test timeouts on staging
- worked on a request-timeout fix"
```

A logged-as-is short day (notes said 4h — keep it):

```
6/10/2026	4.00		"- diagnosed why the service image failed the security-scan gate
- created https://github.com/your-org/service-a/pull/487 to refresh the build cache so patches land
- continued the integration-test work https://github.com/your-org/service-a/pull/482"
```

Empty weekday (present, date only) and a holiday:

```
6/15/2026
6/19/2026			"holiday"
```
