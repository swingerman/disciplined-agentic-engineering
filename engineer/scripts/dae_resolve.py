#!/usr/bin/env python3
"""dae-resolve — resolve the DAE methodology root and parse/validate the manifest.

The first step of every DAE skill. Walks up from a start directory to find
`.engineer/manifest.yml`, parses it, validates it against the Foundation
Design Section 2 schema, and prints JSON.

Parsing is stdlib-only: a *scoped reader* for the locked manifest schema —
NOT a general YAML parser. It handles exactly what the manifest uses:
`key: value`, nested maps by indentation, `-` lists of scalars or maps,
inline `[...]` lists, `#` comments, and quoted/typed scalars.

Usage:
    dae_resolve.py [--validate-only] [START_DIR]

Output (JSON on stdout):
    {
      "methodology_root": "/abs/path",                  # dir containing .engineer/
      "manifest_path": "/abs/path/.engineer/manifest.yml",
      "manifest": { ... },                              # parsed manifest
      "valid": true,
      "errors": [],                                     # hard — block
      "warnings": []                                    # soft — review
    }

Exit codes:
    0  manifest found and valid
    1  manifest found but invalid (errors present)
    2  no manifest found walking up from START_DIR
    3  usage error
"""

import json
import os
import sys

KNOWN_METHODOLOGY_VERSIONS = {"0.1", "0.2"}
TRACKER_TYPES = {"notion", "github-projects", "linear", "jira", "local"}
AUTONOMY_LEVELS = {"low", "medium", "high"}
MUTATION_SCOPES = {"changed_files", "changed_module", "full"}
MUTATION_CADENCES = {"per_pr", "per_merge", "per_release", "on_demand"}
MUTATION_DEFAULTS = {"required", "opt_in"}
AGENTIC_SUMMARY_FORMATS = {"markdown"}
IMPACT_ANALYSIS_VALUES = {"on", "off"}
GIT_MANUAL_VALUES = {True, False}
DUPLICATION_TOOLS = {"jscpd", "pmd-cpd", "flay", "dupl"}
DUPLICATION_SKIP_VALUES = {True, False}


class ManifestError(Exception):
    """Raised when the manifest text cannot be parsed at all."""


# --------------------------------------------------------------------------
# Scoped manifest reader
# --------------------------------------------------------------------------

def _strip_comment(line):
    """Remove a trailing/whole-line `#` comment, ignoring `#` inside quotes."""
    out = []
    in_quote = None
    for i, c in enumerate(line):
        if in_quote:
            out.append(c)
            if c == in_quote:
                in_quote = None
        elif c in ('"', "'"):
            in_quote = c
            out.append(c)
        elif c == '#' and (i == 0 or line[i - 1] in ' \t'):
            break
        else:
            out.append(c)
    return ''.join(out)


def _tokenize(text):
    """Text -> [(indent, content), ...] with comments and blank lines removed."""
    lines = []
    for raw in text.splitlines():
        body = _strip_comment(raw)
        if not body.strip():
            continue
        indent = len(body) - len(body.lstrip(' '))
        lines.append((indent, body.strip()))
    return lines


def _parse_scalar(s):
    """A scalar token -> Python value (str/int/float/bool/None/list)."""
    s = s.strip()
    if s.startswith('[') and s.endswith(']'):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(x) for x in inner.split(',')]
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    low = s.lower()
    if low in ('true', 'yes'):
        return True
    if low in ('false', 'no'):
        return False
    if low in ('null', '~', ''):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _parse_block(lines, i, indent):
    if lines[i][1].startswith('- '):
        return _parse_list(lines, i, indent)
    return _parse_map(lines, i, indent)


def _parse_map(lines, i, indent):
    result = {}
    while i < len(lines):
        line_indent, content = lines[i]
        if line_indent != indent or content.startswith('- '):
            break
        key, sep, val = content.partition(':')
        if not sep:
            raise ManifestError("expected 'key: value', got: %r" % content)
        key, val = key.strip(), val.strip()
        if val:
            result[key] = _parse_scalar(val)
            i += 1
        else:
            i += 1
            if i < len(lines) and lines[i][0] > indent:
                child, i = _parse_block(lines, i, lines[i][0])
                result[key] = child
            else:
                result[key] = None
    return result, i


def _parse_list(lines, i, indent):
    result = []
    while i < len(lines):
        line_indent, content = lines[i]
        if line_indent != indent or not content.startswith('- '):
            break
        item = content[2:].strip()
        key, sep, val = item.partition(':')
        if sep:  # list item is a map; first key sits on the `-` line
            item_indent = indent + 2
            entry = {key.strip(): _parse_scalar(val.strip()) if val.strip() else None}
            i += 1
            if i < len(lines) and lines[i][0] == item_indent \
                    and not lines[i][1].startswith('- '):
                cont, i = _parse_map(lines, i, item_indent)
                entry.update(cont)
            result.append(entry)
        else:  # scalar list item
            result.append(_parse_scalar(item))
            i += 1
    return result, i


def read_manifest(text):
    """Parse manifest YAML-subset text into a dict."""
    lines = _tokenize(text)
    if not lines:
        return {}
    if lines[0][0] != 0:
        raise ManifestError("manifest must start at indent 0")
    value, consumed = _parse_block(lines, 0, 0)
    if consumed != len(lines):
        raise ManifestError("unparsed content at line %d: %r"
                            % (consumed, lines[consumed][1]))
    if not isinstance(value, dict):
        raise ManifestError("manifest top level must be a map")
    return value


def extract_frontmatter(text):
    """Return the YAML frontmatter block of a markdown file — the text between
    the first pair of `---` fences — or None if there is none or it is
    unterminated. Companion to read_manifest, which parses the returned block.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    return None


# --------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------

def find_methodology_root(start_dir):
    """Walk up from start_dir for a directory containing .engineer/manifest.yml.

    Returns (methodology_root, manifest_path) or (None, None).
    """
    d = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(d, '.engineer', 'manifest.yml')
        if os.path.isfile(candidate):
            return d, candidate
        parent = os.path.dirname(d)
        if parent == d:
            return None, None
        d = parent


# --------------------------------------------------------------------------
# Validation (Foundation Design, Section 2)
# --------------------------------------------------------------------------

def _check_range(errors, manifest, section, key, lo, hi):
    block = manifest.get(section)
    if not isinstance(block, dict) or key not in block:
        return
    v = block[key]
    if not isinstance(v, (int, float)) or not (lo <= v <= hi):
        errors.append("%s.%s must be a number in [%d, %d]" % (section, key, lo, hi))


def _check_enum(errors, manifest, section, key, allowed):
    block = manifest.get(section)
    if not isinstance(block, dict) or key not in block or block[key] is None:
        return
    if block[key] not in allowed:
        errors.append("%s.%s = %r — must be one of %s"
                      % (section, key, block[key], sorted(allowed)))


def _validate_architecture(errors, manifest):
    """Light structural validation of the optional `architecture:` section."""
    arch = manifest.get("architecture")
    if not isinstance(arch, dict):
        return
    for i, layer in enumerate(arch.get("layers") or []):
        if not isinstance(layer, dict) or not layer.get("name") \
                or not layer.get("paths"):
            errors.append("architecture.layers[%d] must have 'name' and 'paths'" % i)
    fs = arch.get("file_size")
    if isinstance(fs, dict) and "max_lines" in fs:
        ml = fs["max_lines"]
        if not isinstance(ml, int) or ml <= 0:
            errors.append("architecture.file_size.max_lines must be a positive int")


def validate_manifest(manifest):
    """Validate against the locked schema. Returns (errors, warnings)."""
    errors, warnings = [], []

    # Required fields
    if not manifest.get("methodology_version"):
        errors.append("missing required field: methodology_version")
    elif str(manifest["methodology_version"]) not in KNOWN_METHODOLOGY_VERSIONS:
        warnings.append("methodology_version %r is not a known version %s"
                        % (manifest["methodology_version"],
                           sorted(KNOWN_METHODOLOGY_VERSIONS)))

    for section in ("roadmap", "tracker"):
        block = manifest.get(section)
        if not isinstance(block, dict) or not block.get("type"):
            errors.append("missing required field: %s.type" % section)

    # Enums
    _check_enum(errors, manifest, "roadmap", "type", TRACKER_TYPES)
    _check_enum(errors, manifest, "tracker", "type", TRACKER_TYPES)
    _check_enum(errors, manifest, "mutation", "scope", MUTATION_SCOPES)
    _check_enum(errors, manifest, "mutation", "cadence", MUTATION_CADENCES)
    _check_enum(errors, manifest, "mutation", "default_per_feature", MUTATION_DEFAULTS)
    _check_enum(errors, manifest, "autonomy", "default_level", AUTONOMY_LEVELS)
    _check_enum(errors, manifest, "agentic_summary", "format", AGENTIC_SUMMARY_FORMATS)
    _check_enum(errors, manifest, "acceptance", "impact_analysis",
                IMPACT_ANALYSIS_VALUES)
    _check_enum(errors, manifest, "git", "manual", GIT_MANUAL_VALUES)
    _check_enum(errors, manifest, "duplication", "tool", DUPLICATION_TOOLS)
    _check_enum(errors, manifest, "duplication", "skip", DUPLICATION_SKIP_VALUES)

    autonomy = manifest.get("autonomy")
    if isinstance(autonomy, dict):
        allowed = autonomy.get("allowed_levels")
        if allowed is not None:
            if not isinstance(allowed, list) or any(x not in AUTONOMY_LEVELS for x in allowed):
                errors.append("autonomy.allowed_levels must be a subset of %s"
                              % sorted(AUTONOMY_LEVELS))
        for ov in autonomy.get("path_overrides") or []:
            if isinstance(ov, dict) and ov.get("max_level") not in AUTONOMY_LEVELS:
                errors.append("autonomy.path_overrides[].max_level = %r — must be one of %s"
                              % (ov.get("max_level"), sorted(AUTONOMY_LEVELS)))

    # Quality thresholds in range
    for key in ("crap_max", "coverage_min", "mutation_score_min"):
        _check_range(errors, manifest, "quality_thresholds", key, 0, 100)

    # Verification independence implies the verifier role
    verification = manifest.get("verification")
    if isinstance(verification, dict) and verification.get("enforce_independence"):
        team = manifest.get("team")
        roles = team.get("default_roles") if isinstance(team, dict) else None
        if not isinstance(roles, list) or "verifier" not in roles:
            errors.append("verification.enforce_independence is true — "
                          "team.default_roles must include 'verifier'")

    _validate_architecture(errors, manifest)

    return errors, warnings


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def resolve(start_dir):
    """Full resolve: returns a result dict (see module docstring)."""
    root, manifest_path = find_methodology_root(start_dir)
    if root is None:
        return None
    with open(manifest_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    try:
        manifest = read_manifest(text)
        parse_error = None
    except ManifestError as exc:
        manifest, parse_error = {}, str(exc)
    if parse_error:
        errors, warnings = ["manifest parse error: " + parse_error], []
    else:
        errors, warnings = validate_manifest(manifest)
    return {
        "methodology_root": root,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def main(argv):
    args = [a for a in argv[1:]]
    validate_only = False
    if "--validate-only" in args:
        validate_only = True
        args.remove("--validate-only")
    if len(args) > 1:
        sys.stderr.write("usage: dae_resolve.py [--validate-only] [START_DIR]\n")
        return 3
    start_dir = args[0] if args else os.getcwd()

    result = resolve(start_dir)
    if result is None:
        sys.stderr.write(
            "no .engineer/manifest.yml found walking up from %s — "
            "run /engineer.onboard first\n" % os.path.abspath(start_dir))
        return 2

    if validate_only:
        for e in result["errors"]:
            sys.stderr.write("ERROR: " + e + "\n")
        for w in result["warnings"]:
            sys.stderr.write("WARNING: " + w + "\n")
        if result["valid"]:
            sys.stderr.write("manifest valid: %s\n" % result["manifest_path"])
    else:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")

    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
