#!/usr/bin/env python3
"""dae-gherkin-mutate — IR example-value mutator for the DAE acceptance pipeline.

This is the *spec mutator* of Uncle Bob's Acceptance-Pipeline-Specification —
NOT classic source-code mutation. It alters example values in a feature's
JSON IR, one cell per mutation, so the project can regenerate the acceptance
tests from each mutated IR and confirm they FAIL. A mutation that doesn't
fail (survives) means the generated acceptance test isn't actually wired to
the application.

Distinct from `atdd:mutate`, which mutates *source code* to check the unit
suite. This mutates the *spec* to check the acceptance suite is connected.

Portable / stdlib-only. This script does the portable half — parse + enumerate
mutations + emit one mutated IR per mutation. Regenerating tests from each
mutated IR, running them, and classifying killed/survived/error is the
project pipeline's job (it needs the project-specific generator + runner).

Usage:
    dae_gherkin_mutate.py SPEC_MD [WORK_DIR]

Writes, under WORK_DIR (default: <spec dir>/.build/mutation/):
    mutations.json        the manifest — id, path, description, original, mutated
    mN/spec.json          the mutated IR for each mutation

Exit codes:
    0  mutations enumerated (0 or more)
    1  spec error
    2  input/output error
    3  usage error
"""

import copy
import datetime
import hashlib
import json
import os
import random
import re
import sys

import dae_gherkin

_INT = re.compile(r"^-?\d+$")
_FLOAT = re.compile(r"^-?\d+\.\d+$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _rng_for(path, original):
    """A deterministic RNG seeded by the mutation path + original value."""
    digest = hashlib.sha256((path + "|" + original).encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _dither(s, rng):
    """Return a string that differs from s by one small edit."""
    if s == "":
        return rng.choice("abcdefghijklmnopqrstuvwxyz")
    ops = ["insert", "delete", "replace", "swap", "case"]
    rng.shuffle(ops)
    for op in ops:
        i = rng.randrange(len(s))
        if op == "insert":
            cand = s[:i] + rng.choice("abcdefghijklmnopqrstuvwxyz") + s[i:]
        elif op == "delete" and len(s) > 1:
            cand = s[:i] + s[i + 1:]
        elif op == "replace":
            cand = s[:i] + rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") + s[i + 1:]
        elif op == "swap" and len(s) > 1 and i < len(s) - 1:
            cand = s[:i] + s[i + 1] + s[i] + s[i + 2:]
        elif op == "case":
            cand = s[:i] + s[i].swapcase() + s[i + 1:]
        else:
            continue
        if cand != s:
            return cand
    return s + rng.choice("abcdefghijklmnopqrstuvwxyz")  # last resort


def mutate_value(value, rng):
    """Mutate one example value per the Acceptance-Pipeline value rules.

    Rules applied in order; first match wins. Returns the mutated string.
    """
    trimmed = value.strip()

    # 1. comma-delimited list — mutate one selected item recursively
    if "," in trimmed:
        items = [x.strip() for x in trimmed.split(",")]
        idx = rng.randrange(len(items))
        items[idx] = mutate_value(items[idx], rng)
        return ", ".join(items)

    low = trimmed.lower()
    # 2. boolean
    if low in ("true", "false"):
        return "false" if low == "true" else "true"
    # 3. null-like
    if low in ("null", "nil", "none"):
        return _dither("mutant", rng)
    # 4. integer — add a nonzero delta
    if _INT.match(trimmed):
        delta = rng.choice([-9, -5, -3, -2, -1, 1, 2, 3, 5, 9])
        return str(int(trimmed) + delta)
    # 5. floating point — add a nonzero delta
    if _FLOAT.match(trimmed):
        delta = rng.choice([-1.5, -0.5, -0.25, 0.25, 0.5, 1.5])
        return str(round(float(trimmed) + delta, 4))
    # 6. ISO-8601 date — shift by a nonzero number of days
    if _ISO_DATE.match(trimmed):
        try:
            d = datetime.date.fromisoformat(trimmed)
            shift = rng.choice([-7, -3, -1, 1, 2, 5, 14])
            return (d + datetime.timedelta(days=shift)).isoformat()
        except ValueError:
            pass
    # 8. fall through — dither the original (untrimmed) string
    return _dither(value, rng)


def enumerate_mutations(ir):
    """All single-cell mutations of an IR. Returns a list of mutation dicts."""
    mutations = []
    counter = 0
    for si, scenario in enumerate(ir.get("scenarios", [])):
        for ei, example in enumerate(scenario.get("examples", [])):
            for key in sorted(example.keys()):
                original = example[key]
                path = "$.scenarios[%d].examples[%d].%s" % (si, ei, key)
                mutated = mutate_value(original, _rng_for(path, original))
                if mutated == original:
                    continue  # equivalent — skip
                counter += 1
                mutated_ir = copy.deepcopy(ir)
                mutated_ir["scenarios"][si]["examples"][ei][key] = mutated
                mutations.append({
                    "id": "m%d" % counter,
                    "path": path,
                    "description": "%s: %s -> %s" % (path, original, mutated),
                    "original": original,
                    "mutated": mutated,
                    "mutated_ir": mutated_ir,
                })
    return mutations


def main(argv):
    args = argv[1:]
    if not (1 <= len(args) <= 2):
        sys.stderr.write("usage: dae_gherkin_mutate.py SPEC_MD [WORK_DIR]\n")
        return 3
    spec_path = args[0]
    work_dir = args[1] if len(args) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(spec_path)), ".build", "mutation")

    try:
        with open(spec_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        sys.stderr.write("cannot read %s: %s\n" % (spec_path, exc))
        return 2
    try:
        ir = dae_gherkin.parse_spec(text)
    except dae_gherkin.GherkinError as exc:
        sys.stderr.write("spec error in %s: %s\n" % (spec_path, exc))
        return 1

    mutations = enumerate_mutations(ir)
    try:
        os.makedirs(work_dir, exist_ok=True)
        manifest = [{k: m[k] for k in ("id", "path", "description",
                                       "original", "mutated")}
                    for m in mutations]
        with open(os.path.join(work_dir, "mutations.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, sort_keys=True)
            fh.write("\n")
        for m in mutations:
            mdir = os.path.join(work_dir, m["id"])
            os.makedirs(mdir, exist_ok=True)
            with open(os.path.join(mdir, "spec.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(m["mutated_ir"], fh, indent=2, sort_keys=True)
                fh.write("\n")
    except OSError as exc:
        sys.stderr.write("cannot write under %s: %s\n" % (work_dir, exc))
        return 2

    sys.stderr.write("%d mutation(s) written to %s\n" % (len(mutations), work_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
