#!/usr/bin/env python3
"""dae-gherkin — parse a feature's spec.md into the canonical JSON IR.

Front end of the DAE acceptance pipeline (Foundation Design Section 7).
Reads `spec.md` — standard Gherkin embedded in a markdown file — and emits
`.build/spec.json`, the IR every downstream consumer (test generator,
mutator) reads. Implements the JSON IR shape of Uncle Bob's
Acceptance-Pipeline-Specification.

Stdlib-only. Portable: Gherkin is a standard, so this one parser serves
every project — only the *generator* (IR -> tests) is project-specific.

DAE-specific notes vs Uncle Bob's .feature parser:
- The input is markdown. Non-Gherkin lines (prose, ``` fences) are ignored,
  exactly as the spec says free-form lines are ignored.
- A leading markdown heading marker (`#`, `##`, ...) is stripped before
  keyword matching, so `## Scenario: X` and plain `Scenario: X` both work.
  (Uncle Bob's "lines starting with # are comments" rule does NOT apply —
  in markdown `#` is a heading.)

Usage:
    dae_gherkin.py SPEC_MD [OUT_JSON]      # OUT_JSON omitted -> stdout

Exit codes:
    0  parsed; IR written
    1  spec error (no Feature, Examples outside a scenario, bad table, ...)
    2  input/output error
    3  usage error
"""

import json
import os
import re
import sys

STEP_KEYWORDS = ("Given", "When", "Then", "And")
_HEADING = re.compile(r"^#+\s*")
_PARAM = re.compile(r"<([A-Za-z0-9_]+)>")


class GherkinError(Exception):
    """A spec.md that violates the supported Gherkin subset."""


def _params(text):
    """Parameter names in `text`, in order of appearance, repeats kept."""
    return _PARAM.findall(text)


def _split_row(line):
    """A pipe-delimited table row -> list of trimmed cells."""
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [c.strip() for c in inner.split("|")]


def parse_spec(text):
    """Parse spec.md text into the canonical JSON IR (a dict). Raises GherkinError."""
    feature_name = None
    background = []
    scenarios = []
    current = None          # the scenario dict being built
    step_target = None      # list that steps append to: background or current["steps"]
    in_examples = False
    example_headers = None

    for raw in text.splitlines():
        line = _HEADING.sub("", raw.strip())
        if not line:
            continue

        if line.startswith("Feature:"):
            feature_name = line[len("Feature:"):].strip()
            current, step_target, in_examples = None, None, False
            continue

        if line == "Background:" or line.startswith("Background:"):
            background = []
            current, step_target, in_examples = None, background, False
            continue

        if line.startswith("Scenario Outline:") or line.startswith("Scenario:"):
            name = line.split(":", 1)[1].strip()
            current = {"name": name, "steps": [], "examples": []}
            scenarios.append(current)
            step_target, in_examples, example_headers = current["steps"], False, None
            continue

        if line.startswith("Examples:"):
            if current is None:
                raise GherkinError("Examples: outside a scenario")
            in_examples, example_headers = True, None
            continue

        if line.startswith("|"):
            if not in_examples:
                continue  # a stray table line outside Examples — ignore
            cells = _split_row(line)
            if example_headers is None:
                example_headers = cells
            else:
                if len(cells) != len(example_headers):
                    raise GherkinError(
                        "Examples row has %d cells, header has %d: %r"
                        % (len(cells), len(example_headers), line))
                current["examples"].append(dict(zip(example_headers, cells)))
            continue

        first = line.split(" ", 1)[0]
        if first in STEP_KEYWORDS:
            step_text = line[len(first):].strip()
            if step_target is None:
                raise GherkinError("step outside a background or scenario: %r" % line)
            step_target.append({
                "keyword": first,
                "text": step_text,
                "parameters": _params(step_text),
            })
            in_examples = False
            continue

        # Any other line — markdown prose, fences, descriptions — ignored.

    if feature_name is None:
        raise GherkinError("no 'Feature:' declaration found")

    return {"name": feature_name, "background": background, "scenarios": scenarios}


def main(argv):
    args = argv[1:]
    if not (1 <= len(args) <= 2):
        sys.stderr.write("usage: dae_gherkin.py SPEC_MD [OUT_JSON]\n")
        return 3
    spec_path = args[0]
    out_path = args[1] if len(args) > 1 else None

    try:
        with open(spec_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        sys.stderr.write("cannot read %s: %s\n" % (spec_path, exc))
        return 2

    try:
        ir = parse_spec(text)
    except GherkinError as exc:
        sys.stderr.write("spec error in %s: %s\n" % (spec_path, exc))
        return 1

    rendered = json.dumps(ir, indent=2, sort_keys=True) + "\n"
    if out_path is None:
        sys.stdout.write(rendered)
    else:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(rendered)
        except OSError as exc:
            sys.stderr.write("cannot write %s: %s\n" % (out_path, exc))
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
