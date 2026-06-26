#!/usr/bin/env python3
"""Gather a user's GitHub PRs and commits in an org over a date range, bucketed by
local date (configurable timezone). Uses the `gh` CLI. Emits JSON to stdout.

Why this exists: the report dates are local time, but GitHub timestamps are UTC.
Shifting commit dates by hand is error-prone (a 02:00 UTC commit is the previous
evening in US Eastern), so the conversion is done once, here, deterministically.

Org and timezone come from `config.json` next to the skill (see config.example.json);
override with --org / --tz. Usage:
  python fetch_github.py --since 2026-06-01 --until 2026-06-30 [--org ORG] [--author LOGIN] [--tz ZONE] [--config PATH]

If `gh` is not authenticated it exits non-zero; fall back to the GitHub MCP tools (see SKILL.md).
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo


def run(cmd, retries=4):
    """Run a command, retrying with backoff on GitHub secondary-rate-limit / 403."""
    for attempt in range(retries):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout
        err = (r.stderr or "").strip()
        transient = "rate limit" in err.lower() or "HTTP 403" in err or "was submitted too quickly" in err
        if transient and attempt < retries - 1:
            wait = 30 * (attempt + 1)
            print("rate limited; sleeping %ds before retry..." % wait, file=sys.stderr)
            time.sleep(wait)
            continue
        raise RuntimeError("command failed: %s\n%s" % (" ".join(cmd), err))
    raise RuntimeError("command failed after %d retries: %s" % (retries, " ".join(cmd)))


def gh_json(args):
    return json.loads(run(["gh"] + args))


def ny_date(iso_utc, tz):
    """'2026-06-10T02:00:37Z' -> '6/9/2026' in the target zone (no leading zeros)."""
    dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00")).astimezone(tz)
    return "%d/%d/%d" % (dt.month, dt.day, dt.year)


def ymd(mdy):
    """'6/9/2026' -> (2026, 6, 9) for sorting / range checks."""
    m, d, y = (int(x) for x in mdy.split("/"))
    return (y, m, d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True, help="inclusive local start, YYYY-MM-DD")
    ap.add_argument("--until", required=True, help="inclusive local end, YYYY-MM-DD")
    ap.add_argument("--org", default=None, help="GitHub org; defaults to github_org in config.json")
    ap.add_argument("--author", default=None, help="defaults to the authenticated gh user")
    ap.add_argument("--tz", default=None, help="IANA timezone; defaults to config.json or America/New_York")
    ap.add_argument("--config", default=None, help="path to config.json (default: ../config.json next to this script)")
    args = ap.parse_args()

    cfg_path = args.config or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")
    cfg = {}
    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        pass

    org = args.org or cfg.get("github_org")
    if not org:
        sys.exit('No GitHub org. Pass --org or set "github_org" in %s (see config.example.json).' % cfg_path)
    tz = ZoneInfo(args.tz or cfg.get("timezone") or "America/New_York")

    rng = "%s..%s" % (args.since, args.until)
    since_key = (int(args.since[:4]), int(args.since[5:7]), int(args.since[8:10]))
    until_key = (int(args.until[:4]), int(args.until[5:7]), int(args.until[8:10]))

    if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode != 0:
        sys.exit("gh is not authenticated. Run `gh auth login`, or use the GitHub MCP fallback (see SKILL.md).")

    author = args.author or run(["gh", "api", "user", "-q", ".login"]).strip()

    # PRs the user touched in the window: created OR merged OR updated in range.
    # Use gh flags (not query-string qualifiers, which gh mangles). Dedupe by repo+number.
    fields = "repository,number,title,url,state,createdAt,closedAt,isDraft"
    base = ["search", "prs", "--author", author, "--owner", org, "--limit", "200", "--json", fields]
    seen = {}
    for date_flag, val in (("--created", rng), ("--merged-at", rng), ("--updated", rng)):
        try:
            items = gh_json(base + [date_flag, val])
        except RuntimeError as e:
            print("warning: search %s failed: %s" % (date_flag, e), file=sys.stderr)
            continue
        for it in items:
            repo = it["repository"].get("nameWithOwner") or ("%s/%s" % (org, it["repository"]["name"]))
            seen[(repo, it["number"])] = (repo, it)
        time.sleep(1)  # be gentle with the search API

    prs = []
    by_date = {}
    for (repo, number) in sorted(seen.keys()):
        _, it = seen[(repo, number)]
        created = ny_date(it["createdAt"], tz) if it.get("createdAt") else None
        # gh reports PR state as "merged" (vs "closed" = closed-unmerged); closedAt is the merge time.
        merged = ny_date(it["closedAt"], tz) if (it.get("state") == "merged" and it.get("closedAt")) else None
        commit_days = {}
        try:
            commits = gh_json(["api", "repos/%s/pulls/%d/commits?per_page=100" % (repo, number)])
            for c in commits:
                day = ny_date(c["commit"]["author"]["date"], tz)
                if since_key <= ymd(day) <= until_key:
                    commit_days[day] = commit_days.get(day, 0) + 1
        except RuntimeError as e:
            print("warning: commits for %s#%d failed: %s" % (repo, number, e), file=sys.stderr)
        time.sleep(0.5)

        prs.append({
            "repo": repo, "number": number, "title": it.get("title"), "url": it.get("url"),
            "state": it.get("state"), "draft": it.get("isDraft", False),
            "created_local": created, "merged_local": merged, "commit_days": commit_days,
        })
        for day, n in commit_days.items():
            by_date.setdefault(day, []).append(
                {"repo": repo, "number": number, "title": it.get("title"), "url": it.get("url"), "commits": n})

    out = {
        "author": author, "org": org, "tz": str(tz), "range": [args.since, args.until],
        "prs": prs,
        "by_date": dict(sorted(by_date.items(), key=lambda kv: ymd(kv[0]))),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
