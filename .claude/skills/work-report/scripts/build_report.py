#!/usr/bin/env python3
"""Assemble the paste-ready TSV work report from a JSON list of day entries.

Guarantees the exact 4-column tab format (Date, Hours, Work Type, Description) with
multi-line, double-quoted Description cells that paste into a SINGLE spreadsheet cell.
The format is fiddly (tabs + quoting + empty-day handling) and easy to get wrong by hand,
so it is encoded once here.

Input JSON: a list of day entries, in the order they should appear:
  [
    {"date": "6/9/2026", "hours": "8.00", "work_type": "", "lines": ["- worked on ...", "- created https://..."]},
    {"date": "6/23/2026", "hours": "3.00", "work_type": "review", "lines": ["- investigated ..."]},
    {"date": "6/19/2026", "lines": ["holiday"]},
    {"date": "6/15/2026"}
  ]

Rules:
  - `lines` are written verbatim into the cell (include the leading "- " yourself); joined
    with newlines and wrapped in quotes. No dashes are added.
  - Missing/empty hours -> empty Hours cell. Missing/empty work_type -> empty Work Type cell.
  - A day with no hours, no work_type and no lines is a truly-empty day: emitted as date only.

Usage:
  python build_report.py --input days.json --output report-june.txt
"""
import argparse
import json


def quote_cell(text):
    """RFC4180-style quoting so embedded newlines stay inside one spreadsheet cell."""
    return '"' + text.replace('"', '""') + '"'


def render_row(day):
    date = day["date"]
    hours = (day.get("hours") or "").strip()
    work_type = (day.get("work_type") or "").strip()
    lines = day.get("lines") or []

    if not hours and not work_type and not lines:
        return date  # truly-empty day: date only, no trailing whitespace

    desc = quote_cell("\n".join(lines)) if lines else ""
    row = "%s\t%s\t%s\t%s" % (date, hours, work_type, desc)
    return row.rstrip("\t")  # avoid trailing tabs when later columns are empty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        days = json.load(f)

    rows = [render_row(d) for d in days]
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")

    print("wrote %d rows to %s" % (len(days), args.output))


if __name__ == "__main__":
    main()
