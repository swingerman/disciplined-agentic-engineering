#!/usr/bin/env python3
"""dae-gherkin-convert — migrate a legacy atdd `.txt` spec to standard Gherkin.

The atdd plugin's original spec format was a `;===` comment-block GWT format
in `specs/*.txt`:

    ;===============================================================
    ; User can register with email and password.
    ;===============================================================
    GIVEN no registered users.
    WHEN a user registers with email "bob@example.com".
    THEN there is 1 registered user.
    THEN the user "bob@example.com" can log in.

DAE standardises on Gherkin in `spec.md`. This converter migrates an existing
`.txt` spec to that format:

    Feature: <from the file name>

    Scenario: User can register with email and password
      Given no registered users
      When a user registers with email "bob@example.com"
      Then there is 1 registered user
      And the user "bob@example.com" can log in

Conversion rules:
- A `;===` / `;---` rule line is a block separator — dropped.
- A `; <text>` comment line is the next scenario's name.
- `GIVEN` / `WHEN` / `THEN` / `AND` -> `Given` / `When` / `Then` / `And`.
- A repeated keyword (`GIVEN` then `GIVEN`) becomes `And`, the Gherkin idiom.
- A trailing `.` on a step line is stripped.
- The `Feature:` name is derived from the `.txt` file name.

Stdlib-only. Output is valid input for dae_gherkin.py.

Usage:
    dae_gherkin_convert.py SPEC_TXT [OUT_MD]      # OUT_MD default: SPEC_TXT with .md

Exit codes:
    0  converted
    1  nothing recognised (not an atdd .txt spec?)
    2  input/output error
    3  usage error
"""

import os
import re
import sys

_KEYWORDS = ("GIVEN", "WHEN", "THEN", "AND")
_SEPARATOR = re.compile(r"^;[=\-\s]*$")


def _feature_name(txt_path):
    stem = os.path.splitext(os.path.basename(txt_path))[0]
    words = re.split(r"[-_\s]+", stem.strip())
    return " ".join(w.capitalize() for w in words if w) or "Feature"


def convert(text, feature_name):
    """Convert legacy atdd `.txt` spec text to a standard Gherkin string.

    Returns the Gherkin text, or None if no scenarios/steps were recognised.
    """
    scenarios = []          # list of (name, [ (keyword, text), ... ])
    current = None
    prev_keyword = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if _SEPARATOR.match(line):
            continue
        if line.startswith(";"):
            # comment line with content -> a scenario name
            name = line.lstrip(";").strip()
            if name:
                current = (name, [])
                scenarios.append(current)
                prev_keyword = None
            continue

        first = line.split(" ", 1)[0].upper()
        if first in _KEYWORDS:
            step_text = line[len(first):].strip().rstrip(".").strip()
            if first == "AND":
                keyword = "And"
            elif first == prev_keyword:
                keyword = "And"          # repeated keyword -> Gherkin idiom
            else:
                keyword = first.capitalize()
            if current is None:           # steps before any ; name block
                current = ("Scenario", [])
                scenarios.append(current)
            current[1].append((keyword, step_text))
            prev_keyword = first if first != "AND" else prev_keyword
            continue

        # any other line — ignored

    if not scenarios or all(not steps for _, steps in scenarios):
        return None

    out = ["Feature: " + feature_name, ""]
    for name, steps in scenarios:
        out.append("Scenario: " + name)
        for keyword, step_text in steps:
            out.append("  %s %s" % (keyword, step_text))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main(argv):
    args = argv[1:]
    if not (1 <= len(args) <= 2):
        sys.stderr.write("usage: dae_gherkin_convert.py SPEC_TXT [OUT_MD]\n")
        return 3
    txt_path = args[0]
    out_path = args[1] if len(args) > 1 else os.path.splitext(txt_path)[0] + ".md"

    try:
        with open(txt_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        sys.stderr.write("cannot read %s: %s\n" % (txt_path, exc))
        return 2

    gherkin = convert(text, _feature_name(txt_path))
    if gherkin is None:
        sys.stderr.write("no scenarios/steps recognised in %s — "
                         "is it an atdd .txt spec?\n" % txt_path)
        return 1

    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(gherkin)
    except OSError as exc:
        sys.stderr.write("cannot write %s: %s\n" % (out_path, exc))
        return 2
    sys.stderr.write("converted %s -> %s\n" % (txt_path, out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
