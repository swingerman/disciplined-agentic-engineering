#!/usr/bin/env python3
"""
Compute CRAP (Change Risk Anti-Patterns) scores for functions touched by a diff.

CRAP(m) = comp(m)^2 * (1 - cov(m))^3 + comp(m)

Zero external dependencies. Heuristic complexity via token counting, coverage
via multi-format parsing. Accurate enough to rank findings; not a replacement
for a proper static analyzer.

Supported source languages (by extension):
  JS/TS: .ts .tsx .js .jsx .mjs .cjs
  Python: .py
  Java/Kotlin: .java .kt .kts
  Go: .go
  Ruby: .rb
  C#: .cs
  Rust: .rs
  PHP: .php

Supported coverage formats (auto-detected):
  lcov.info, Cobertura XML, JaCoCo XML, Clover XML, Go coverage.out,
  coverage.py JSON.

Usage:
  compute_crap.py --diff <path|-> [--repo-root DIR] [--lcov PATH]
                  [--threshold N] [--format json|md|both]

If --diff is '-' the diff is read from stdin. --lcov (misnomer; accepts any
supported format) overrides auto-discovery.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from pathlib import Path

# ---------- language registry ----------

LANG_BY_EXT = {
    ".ts": "ts", ".tsx": "ts", ".js": "js", ".jsx": "js",
    ".mjs": "js", ".cjs": "js",
    ".py": "python",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".go": "go",
    ".rb": "ruby",
    ".cs": "csharp",
    ".rs": "rust",
    ".php": "php",
}

# Test files we skip — don't analyze test code itself.
TEST_PATTERNS = [
    re.compile(r"\.(spec|test)\.[jt]sx?$"),
    re.compile(r"\.(spec|test)\.(mjs|cjs)$"),
    re.compile(r"(^|/)test_[^/]+\.py$"),
    re.compile(r"(^|/)[^/]+_test\.py$"),
    re.compile(r"_test\.go$"),
    re.compile(r"Test\.(java|kt|kts)$"),
    re.compile(r"Tests\.(java|kt|kts|cs)$"),
    re.compile(r"Spec\.(java|kt|kts)$"),
    re.compile(r"_spec\.rb$"),
    re.compile(r"(^|/)tests?/"),
    re.compile(r"\.d\.ts$"),
]


def language_of(rel_path: str) -> str | None:
    """Return language id for a repo-relative path, or None if unsupported/test."""
    if any(p.search(rel_path) for p in TEST_PATTERNS):
        return None
    ext = os.path.splitext(rel_path)[1].lower()
    return LANG_BY_EXT.get(ext)


# ---------- diff parsing ----------

DIFF_FILE_RE = re.compile(r"^\+\+\+ b/(.+)$")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def parse_diff(diff_text: str) -> dict[str, set[int]]:
    """Return {file_path: set_of_added_line_numbers} (new-side line numbers)."""
    touched: dict[str, set[int]] = {}
    current_file: str | None = None
    new_line = 0
    in_hunk = False
    for raw in diff_text.splitlines():
        m = DIFF_FILE_RE.match(raw)
        if m:
            current_file = m.group(1)
            if current_file == "/dev/null":
                current_file = None
            if current_file:
                touched.setdefault(current_file, set())
            in_hunk = False
            continue
        hm = HUNK_RE.match(raw)
        if hm and current_file:
            new_line = int(hm.group(1))
            in_hunk = True
            continue
        if not in_hunk or not current_file:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            touched[current_file].add(new_line)
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            pass  # removed from old, no new line advance
        else:
            new_line += 1
    return {f: lines for f, lines in touched.items() if lines}


# ---------- token stripping ----------

def _blank_preserving_newlines(s: str) -> str:
    return "".join(" " if ch != "\n" else "\n" for ch in s)


def strip_brace_language(src: str) -> str:
    """Blank out strings and comments for brace-style languages (JS/TS/Java/Kotlin/Go/C#/Rust/PHP).
    Preserves newlines and column offsets.

    Handles // line comments, /* block comments */, ' ", ` (template) strings,
    and `#` line comments (for shells, though we don't strictly need it here).
    Blanks template-literal interpolation bodies to keep brace counter balanced."""
    out: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            j = src.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
            continue
        if c == "/" and nxt == "*":
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append(_blank_preserving_newlines(src[i:j]))
            i = j
            continue
        if c in ("'", '"', "`"):
            quote = c
            j = i + 1
            while j < n:
                if src[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if src[j] == quote:
                    j += 1
                    break
                if quote != "`" and src[j] == "\n":
                    break
                j += 1
            out.append(_blank_preserving_newlines(src[i:j]))
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def strip_python(src: str) -> str:
    """Blank out strings (including triple-quoted / f-strings) and comments in Python."""
    out: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c == "#":
            j = src.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
            continue
        # triple-quoted strings
        if (c in ("'", '"')) and src[i:i + 3] in ("'''", '"""'):
            quote = src[i:i + 3]
            j = src.find(quote, i + 3)
            j = n if j == -1 else j + 3
            out.append(_blank_preserving_newlines(src[i:j]))
            i = j
            continue
        # single-quoted (possibly prefixed: r, b, f, rb, fr, etc.)
        if c in ("'", '"'):
            quote = c
            j = i + 1
            while j < n:
                if src[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if src[j] == quote or src[j] == "\n":
                    if src[j] == quote:
                        j += 1
                    break
                j += 1
            out.append(_blank_preserving_newlines(src[i:j]))
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def strip_ruby(src: str) -> str:
    """Ruby strings and # comments. Good-enough heuristic; ignores heredocs
    (they'll just leak into the source but rarely confuse decision counting)."""
    out: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c == "#":
            j = src.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
            continue
        if c in ("'", '"'):
            quote = c
            j = i + 1
            while j < n:
                if src[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if src[j] == quote:
                    j += 1
                    break
                j += 1
            out.append(_blank_preserving_newlines(src[i:j]))
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def strip_source(lang: str, src: str) -> str:
    if lang == "python":
        return strip_python(src)
    if lang == "ruby":
        return strip_ruby(src)
    return strip_brace_language(src)


# ---------- function discovery ----------

@dataclass
class FuncSpan:
    name: str
    kind: str
    start_line: int
    body_start_line: int
    body_end_line: int


def line_of(src: str, pos: int) -> int:
    return src.count("\n", 0, pos) + 1


def find_matching_brace(src: str, open_pos: int) -> int:
    depth = 0
    i = open_pos
    n = len(src)
    while i < n:
        c = src[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def find_body_brace_after_signature(src: str, after: int) -> int:
    """For C-family signatures, find the next '{' that begins a body,
    skipping return-type annotations etc. Returns -1 if it's only a declaration."""
    n = len(src)
    i = after
    depth_paren = 0
    depth_angle = 0
    while i < n:
        c = src[i]
        if c == "(":
            depth_paren += 1
        elif c == ")":
            depth_paren -= 1
        elif c == "<":
            depth_angle += 1
        elif c == ">" and depth_angle > 0:
            depth_angle -= 1
        elif c == "{" and depth_paren == 0 and depth_angle == 0:
            return i
        elif c == ";" and depth_paren == 0 and depth_angle == 0:
            return -1
        i += 1
    return -1


def _walk_to_matching_paren(src: str, open_idx: int) -> int:
    depth = 0
    i = open_idx
    n = len(src)
    while i < n:
        if src[i] == "(":
            depth += 1
        elif src[i] == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


# --- JS/TS function discovery -------------------------------------------------

_JSTS_RESERVED = {
    "if", "else", "for", "while", "do", "switch", "case", "return", "throw",
    "try", "catch", "finally", "new", "typeof", "instanceof", "in", "of",
    "void", "delete", "await", "yield", "function", "class", "interface",
    "type", "enum", "const", "let", "var", "import", "export", "from", "as",
    "default", "true", "false", "null", "undefined", "this", "super",
    "extends", "implements", "public", "private", "protected", "readonly",
    "static", "abstract", "async", "get", "set", "constructor",
}

_JSTS_FUNC_DECL = re.compile(r"\bfunction\s*\*?\s*([A-Za-z_$][\w$]*)\s*(?:<[^>]*>)?\s*\(")
_JSTS_METHOD = re.compile(
    r"^(?P<indent>[ \t]*)"
    r"(?:(?:public|private|protected|readonly|static|abstract|async|override)\s+)*"
    r"(?P<kind>get\s+|set\s+|)"
    r"(?P<name>[A-Za-z_$][\w$]*|constructor)"
    r"\s*(?:<[^>]*>)?\s*\(",
    re.MULTILINE,
)
_JSTS_ARROW = re.compile(
    r"^(?P<indent>[ \t]*)"
    r"(?:(?:public|private|protected|readonly|static|async|override)\s+)*"
    r"(?P<name>[A-Za-z_$][\w$]*)\s*"
    r"(?::\s*[^=;{]+)?\s*"
    r"=\s*(?:async\s+)?"
    r"(?:<[^>]*>)?\s*"
    r"\([^)]*\)\s*"
    r"(?::\s*[^=>{]+)?\s*=>\s*\{",
    re.MULTILINE,
)


def discover_jstsfuncs(src: str, stripped: str) -> list[FuncSpan]:
    found: list[FuncSpan] = []
    seen: set[int] = set()

    def add(name: str, kind: str, sig_pos: int, body_open: int) -> None:
        if body_open in seen:
            return
        close = find_matching_brace(stripped, body_open)
        if close == -1:
            return
        seen.add(body_open)
        found.append(FuncSpan(
            name=name, kind=kind,
            start_line=line_of(src, sig_pos),
            body_start_line=line_of(src, body_open),
            body_end_line=line_of(src, close),
        ))

    for m in _JSTS_FUNC_DECL.finditer(stripped):
        paren_open = stripped.find("(", m.end() - 1)
        paren_close = _walk_to_matching_paren(stripped, paren_open)
        if paren_close == -1:
            continue
        body_open = find_body_brace_after_signature(stripped, paren_close + 1)
        if body_open != -1:
            add(m.group(1), "function", m.start(), body_open)

    for m in _JSTS_ARROW.finditer(stripped):
        name = m.group("name")
        if name in _JSTS_RESERVED:
            continue
        body_open = stripped.find("{", m.end() - 1)
        if body_open != -1:
            add(name, "arrow", m.start(), body_open)

    for m in _JSTS_METHOD.finditer(stripped):
        name = m.group("name")
        prefix = m.group("kind").strip()
        if name in _JSTS_RESERVED and name != "constructor":
            continue
        if name in ("if", "for", "while", "switch", "catch", "return"):
            continue
        paren_open = stripped.find("(", m.end() - 1)
        paren_close = _walk_to_matching_paren(stripped, paren_open)
        if paren_close == -1:
            continue
        body_open = find_body_brace_after_signature(stripped, paren_close + 1)
        if body_open == -1:
            continue
        kind = ("ctor" if name == "constructor"
                else "getter" if prefix == "get"
                else "setter" if prefix == "set"
                else "method")
        add(name, kind, m.start(), body_open)

    return found


# --- Python function discovery -----------------------------------------------

_PY_DEF = re.compile(
    r"^(?P<indent>[ \t]*)(?:async\s+)?def\s+(?P<name>[A-Za-z_][\w]*)\s*\(",
    re.MULTILINE,
)


def discover_py_funcs(src: str, stripped: str) -> list[FuncSpan]:
    """Use indentation to bound each def's body."""
    found: list[FuncSpan] = []
    lines = src.splitlines()
    n_lines = len(lines)
    matches = list(_PY_DEF.finditer(stripped))
    for m in matches:
        name = m.group("name")
        indent = m.group("indent") or ""
        sig_line = line_of(src, m.start())
        # Find the colon that ends the signature (may span several lines due to type hints).
        body_start_line = sig_line
        i = m.start()
        depth_paren = 0
        depth_bracket = 0
        while i < len(stripped):
            c = stripped[i]
            if c == "(":
                depth_paren += 1
            elif c == ")":
                depth_paren -= 1
            elif c == "[":
                depth_bracket += 1
            elif c == "]":
                depth_bracket -= 1
            elif c == ":" and depth_paren == 0 and depth_bracket == 0:
                body_start_line = line_of(src, i) + 1
                break
            i += 1
        # End: next line (starting from body_start_line) whose indent <= signature indent and is non-empty.
        end_line = n_lines
        sig_indent_len = len(indent)
        for ln_idx in range(body_start_line - 1, n_lines):
            line = lines[ln_idx]
            stripped_line = line.lstrip()
            if not stripped_line or stripped_line.startswith("#"):
                continue
            cur_indent = len(line) - len(stripped_line)
            if cur_indent <= sig_indent_len and ln_idx + 1 > body_start_line:
                end_line = ln_idx  # exclusive; previous line was last body line
                break
        found.append(FuncSpan(
            name=name,
            kind="method" if indent else "function",
            start_line=sig_line,
            body_start_line=body_start_line,
            body_end_line=end_line,
        ))
    return found


# --- Java / Kotlin / C# function discovery -----------------------------------

_JVM_METHOD = re.compile(
    # modifiers + return-type + name(
    r"^(?P<indent>[ \t]*)"
    r"(?:(?:public|private|protected|internal|static|final|abstract|override|open|sealed|suspend|default|native|synchronized|async|virtual|new|partial|extern)\s+)*"
    r"(?:@[A-Za-z_$][\w$.]*(?:\([^)]*\))?\s+)*"  # annotations
    r"(?:[A-Za-z_$][\w$<>.,?\[\] ]*\s+)?"  # return type (optional for ctors)
    r"(?P<name>[A-Za-z_$][\w$]*)"
    r"\s*(?:<[^>]*>)?\s*\(",
    re.MULTILINE,
)

_KOTLIN_FUN = re.compile(
    r"^(?P<indent>[ \t]*)"
    r"(?:(?:public|private|protected|internal|inline|suspend|operator|override|open|final|abstract|tailrec|infix|external|actual|expect)\s+)*"
    r"fun\s+(?:<[^>]*>\s+)?"
    r"(?:[A-Za-z_$][\w$.<>,?\[\] ]*\.)?"  # receiver type
    r"(?P<name>[A-Za-z_$][\w$]*)"
    r"\s*(?:<[^>]*>)?\s*\(",
    re.MULTILINE,
)

_CSHARP_CONTROL_KW = {"if", "for", "foreach", "while", "switch", "catch", "lock", "using", "fixed", "unsafe", "return", "throw"}


def discover_jvm_funcs(src: str, stripped: str, lang: str) -> list[FuncSpan]:
    found: list[FuncSpan] = []
    seen: set[int] = set()

    def add(name: str, kind: str, sig_pos: int, body_open: int):
        if body_open in seen:
            return
        close = find_matching_brace(stripped, body_open)
        if close == -1:
            return
        seen.add(body_open)
        found.append(FuncSpan(
            name=name, kind=kind,
            start_line=line_of(src, sig_pos),
            body_start_line=line_of(src, body_open),
            body_end_line=line_of(src, close),
        ))

    patterns: list[tuple[re.Pattern, str]] = []
    if lang == "kotlin":
        patterns.append((_KOTLIN_FUN, "function"))
    # Both kotlin secondary constructors and java/cs methods match _JVM_METHOD
    patterns.append((_JVM_METHOD, "method"))

    for pat, default_kind in patterns:
        for m in pat.finditer(stripped):
            name = m.group("name")
            if name in _CSHARP_CONTROL_KW:
                continue
            paren_open = stripped.find("(", m.end() - 1)
            paren_close = _walk_to_matching_paren(stripped, paren_open)
            if paren_close == -1:
                continue
            body_open = find_body_brace_after_signature(stripped, paren_close + 1)
            if body_open == -1:
                continue  # abstract/interface/declaration only
            kind = "ctor" if default_kind == "method" and name[:1].isupper() and _looks_like_ctor(stripped, m) else default_kind
            add(name, kind, m.start(), body_open)

    return found


def _looks_like_ctor(stripped: str, m: re.Match) -> bool:
    # Rough heuristic: return-type slot is empty (name directly after modifiers).
    before = stripped[max(0, m.start()):m.end()].rstrip("(").rstrip()
    tokens = before.split()
    if not tokens:
        return False
    return tokens[-1] == m.group("name")


# --- Go function discovery ---------------------------------------------------

_GO_FUNC = re.compile(
    r"^func\s+(?:\([^)]*\)\s+)?(?P<name>[A-Za-z_][\w]*)\s*(?:\[[^\]]*\])?\s*\(",
    re.MULTILINE,
)


def discover_go_funcs(src: str, stripped: str) -> list[FuncSpan]:
    found: list[FuncSpan] = []
    for m in _GO_FUNC.finditer(stripped):
        paren_open = stripped.find("(", m.end() - 1)
        paren_close = _walk_to_matching_paren(stripped, paren_open)
        if paren_close == -1:
            continue
        body_open = find_body_brace_after_signature(stripped, paren_close + 1)
        if body_open == -1:
            continue
        close = find_matching_brace(stripped, body_open)
        if close == -1:
            continue
        found.append(FuncSpan(
            name=m.group("name"), kind="function",
            start_line=line_of(src, m.start()),
            body_start_line=line_of(src, body_open),
            body_end_line=line_of(src, close),
        ))
    return found


# --- Ruby function discovery -------------------------------------------------

_RUBY_DEF = re.compile(
    r"^(?P<indent>[ \t]*)def\s+(?:self\.)?(?P<name>[A-Za-z_][\w]*[!?=]?)",
    re.MULTILINE,
)


def discover_ruby_funcs(src: str, stripped: str) -> list[FuncSpan]:
    """Match def...end blocks by scanning stripped source for `end` at same indent."""
    found: list[FuncSpan] = []
    lines = stripped.splitlines()
    for m in _RUBY_DEF.finditer(stripped):
        name = m.group("name")
        indent = m.group("indent") or ""
        sig_line = line_of(src, m.start())
        # Walk forward until we find `end` at matching indent
        end_line = len(lines)
        for ln_idx in range(sig_line, len(lines)):
            raw = lines[ln_idx]
            if raw.strip() == "end" and raw.startswith(indent + "end") or raw == indent + "end":
                end_line = ln_idx + 1  # 1-based
                break
        found.append(FuncSpan(
            name=name, kind="method",
            start_line=sig_line,
            body_start_line=sig_line + 1,
            body_end_line=end_line,
        ))
    return found


# --- Rust function discovery -------------------------------------------------

_RUST_FN = re.compile(
    r"^(?P<indent>[ \t]*)"
    r"(?:(?:pub(?:\([^)]*\))?|const|async|unsafe|extern(?:\s+\"[^\"]*\")?)\s+)*"
    r"fn\s+(?P<name>[A-Za-z_][\w]*)",
    re.MULTILINE,
)


def discover_rust_funcs(src: str, stripped: str) -> list[FuncSpan]:
    found: list[FuncSpan] = []
    for m in _RUST_FN.finditer(stripped):
        body_open = find_body_brace_after_signature(stripped, m.end())
        if body_open == -1:
            continue
        close = find_matching_brace(stripped, body_open)
        if close == -1:
            continue
        found.append(FuncSpan(
            name=m.group("name"), kind="function",
            start_line=line_of(src, m.start()),
            body_start_line=line_of(src, body_open),
            body_end_line=line_of(src, close),
        ))
    return found


# --- PHP function discovery --------------------------------------------------

_PHP_FN = re.compile(
    r"^(?P<indent>[ \t]*)"
    r"(?:(?:public|private|protected|static|final|abstract)\s+)*"
    r"function\s+(?:&\s*)?(?P<name>[A-Za-z_][\w]*)",
    re.MULTILINE,
)


def discover_php_funcs(src: str, stripped: str) -> list[FuncSpan]:
    found: list[FuncSpan] = []
    for m in _PHP_FN.finditer(stripped):
        paren_open = stripped.find("(", m.end())
        if paren_open == -1:
            continue
        paren_close = _walk_to_matching_paren(stripped, paren_open)
        if paren_close == -1:
            continue
        body_open = find_body_brace_after_signature(stripped, paren_close + 1)
        if body_open == -1:
            continue
        close = find_matching_brace(stripped, body_open)
        if close == -1:
            continue
        found.append(FuncSpan(
            name=m.group("name"), kind="function",
            start_line=line_of(src, m.start()),
            body_start_line=line_of(src, body_open),
            body_end_line=line_of(src, close),
        ))
    return found


# --- dispatcher --------------------------------------------------------------

def discover_functions(lang: str, src: str, stripped: str) -> list[FuncSpan]:
    if lang in ("ts", "js"):
        return discover_jstsfuncs(src, stripped)
    if lang == "python":
        return discover_py_funcs(src, stripped)
    if lang in ("java", "kotlin", "csharp"):
        return discover_jvm_funcs(src, stripped, lang)
    if lang == "go":
        return discover_go_funcs(src, stripped)
    if lang == "ruby":
        return discover_ruby_funcs(src, stripped)
    if lang == "rust":
        return discover_rust_funcs(src, stripped)
    if lang == "php":
        return discover_php_funcs(src, stripped)
    return []


# ---------- complexity ----------

# Shared C-family decision keywords
_CFAMILY_KW = re.compile(r"\b(?:if|for|while|case|catch)\b")
_GO_KW = re.compile(r"\b(?:if|for|case|select)\b")  # Go has no while; select's cases
_PY_KW = re.compile(r"\b(?:if|elif|for|while|except|case)\b")
_RUBY_KW = re.compile(r"\b(?:if|elsif|unless|for|while|until|when|rescue)\b")
_KOTLIN_KW = re.compile(r"\b(?:if|for|while|catch|when)\b")
_CSHARP_KW = re.compile(r"\b(?:if|for|foreach|while|case|catch)\b")

# Logical / ternary
_LOGICAL_OPS = re.compile(r"&&|\|\||\?\?")
_PY_LOGICAL = re.compile(r"\b(?:and|or)\b")
_RUBY_LOGICAL = re.compile(r"&&|\|\||\b(?:and|or)\b")
_TERNARY = re.compile(r"(?<![?!])\?(?![.?:)\]])")


def compute_complexity(lang: str, body: str) -> int:
    c = 1
    if lang in ("ts", "js"):
        c += len(_CFAMILY_KW.findall(body))
        c += len(_LOGICAL_OPS.findall(body))
        c += len(_TERNARY.findall(body))
    elif lang == "python":
        c += len(_PY_KW.findall(body))
        c += len(_PY_LOGICAL.findall(body))
        # Python's ternary `x if c else y` — count each `if` inside expression. Already in _PY_KW.
    elif lang == "java":
        c += len(_CFAMILY_KW.findall(body))
        c += len(_LOGICAL_OPS.findall(body))
        c += len(_TERNARY.findall(body))
    elif lang == "kotlin":
        c += len(_KOTLIN_KW.findall(body))
        c += len(_LOGICAL_OPS.findall(body))
        c += len(_TERNARY.findall(body))
    elif lang == "csharp":
        c += len(_CSHARP_KW.findall(body))
        c += len(_LOGICAL_OPS.findall(body))
        c += len(_TERNARY.findall(body))
    elif lang == "go":
        c += len(_GO_KW.findall(body))
        c += len(_LOGICAL_OPS.findall(body))
        # Go has no ternary
    elif lang == "ruby":
        c += len(_RUBY_KW.findall(body))
        c += len(_RUBY_LOGICAL.findall(body))
        c += len(_TERNARY.findall(body))
    elif lang == "rust":
        c += len(_CFAMILY_KW.findall(body))
        c += len(re.findall(r"\bmatch\b", body))
        c += len(_LOGICAL_OPS.findall(body))
        # Rust has no ternary
    elif lang == "php":
        c += len(_CFAMILY_KW.findall(body))
        c += len(re.findall(r"\belseif\b", body))
        c += len(_LOGICAL_OPS.findall(body))
        c += len(_TERNARY.findall(body))
    return c


# ---------- coverage parsing ----------

@dataclass
class CovFile:
    line_hits: dict[int, int] = field(default_factory=dict)


def parse_lcov(text: str, repo_root: Path) -> dict[str, CovFile]:
    by_file: dict[str, CovFile] = {}
    current: CovFile | None = None
    current_path: str | None = None
    for line in text.splitlines():
        if line.startswith("SF:"):
            raw = line[3:].strip()
            p = Path(raw)
            if not p.is_absolute():
                p = (repo_root / p).resolve()
            try:
                rel = p.relative_to(repo_root.resolve())
                current_path = str(rel).replace(os.sep, "/")
            except ValueError:
                current_path = str(p)
            current = CovFile()
            by_file[current_path] = current
        elif line.startswith("DA:") and current is not None:
            try:
                ln_s, hit_s = line[3:].split(",", 1)
                ln = int(ln_s)
                hits = int(hit_s.split(",")[0])
                current.line_hits[ln] = hits
            except (ValueError, IndexError):
                continue
        elif line.startswith("end_of_record"):
            current = None
            current_path = None
    return by_file


def parse_cobertura(text: str, repo_root: Path) -> dict[str, CovFile]:
    by_file: dict[str, CovFile] = {}
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return by_file
    # Source roots declared at top of report
    source_roots: list[Path] = []
    for s in root.findall(".//sources/source"):
        if s.text:
            sp = Path(s.text.strip())
            source_roots.append(sp if sp.is_absolute() else (repo_root / sp).resolve())
    if not source_roots:
        source_roots = [repo_root.resolve()]

    for cls in root.findall(".//class"):
        filename = cls.get("filename")
        if not filename:
            continue
        # Resolve via source roots
        chosen: str | None = None
        abs_candidate = Path(filename)
        if abs_candidate.is_absolute() and abs_candidate.exists():
            try:
                chosen = str(abs_candidate.relative_to(repo_root.resolve())).replace(os.sep, "/")
            except ValueError:
                chosen = str(abs_candidate)
        else:
            for root_dir in source_roots:
                cand = (root_dir / filename).resolve()
                if cand.exists():
                    try:
                        chosen = str(cand.relative_to(repo_root.resolve())).replace(os.sep, "/")
                    except ValueError:
                        chosen = str(cand)
                    break
            if chosen is None:
                # fall back to the raw relative path
                chosen = filename.replace(os.sep, "/")
        cov = by_file.setdefault(chosen, CovFile())
        for line_el in cls.findall(".//line"):
            try:
                ln = int(line_el.get("number", "0"))
                hits = int(line_el.get("hits", "0"))
                if ln > 0:
                    cov.line_hits[ln] = hits
            except ValueError:
                continue
    return by_file


def parse_jacoco(text: str, repo_root: Path) -> dict[str, CovFile]:
    by_file: dict[str, CovFile] = {}
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return by_file
    # JaCoCo XML: <report><package name="com/acme"><sourcefile name="Foo.java"><line nr="N" mi="0" ci="1" ...></line>...
    for pkg in root.findall(".//package"):
        pkg_name = pkg.get("name", "").replace(".", "/")
        for sf in pkg.findall("sourcefile"):
            fname = sf.get("name")
            if not fname:
                continue
            rel = f"{pkg_name}/{fname}" if pkg_name else fname
            # Try to resolve against common source roots
            candidates = [
                repo_root / rel,
                repo_root / "src" / "main" / "java" / rel,
                repo_root / "src" / "main" / "kotlin" / rel,
            ]
            chosen = rel
            for c in candidates:
                if c.exists():
                    try:
                        chosen = str(c.resolve().relative_to(repo_root.resolve())).replace(os.sep, "/")
                    except ValueError:
                        chosen = str(c)
                    break
            cov = by_file.setdefault(chosen, CovFile())
            for ln in sf.findall("line"):
                try:
                    nr = int(ln.get("nr", "0"))
                    mi = int(ln.get("mi", "0"))  # missed instructions
                    ci = int(ln.get("ci", "0"))  # covered instructions
                    if nr > 0 and (mi + ci) > 0:
                        cov.line_hits[nr] = 1 if ci > 0 else 0
                except ValueError:
                    continue
    return by_file


def parse_clover(text: str, repo_root: Path) -> dict[str, CovFile]:
    by_file: dict[str, CovFile] = {}
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return by_file
    for f in root.findall(".//file"):
        path = f.get("path") or f.get("name")
        if not path:
            continue
        p = Path(path)
        rel = path
        if p.is_absolute():
            try:
                rel = str(p.resolve().relative_to(repo_root.resolve())).replace(os.sep, "/")
            except ValueError:
                rel = str(p)
        cov = by_file.setdefault(rel, CovFile())
        for line_el in f.findall("line"):
            if line_el.get("type") != "stmt" and line_el.get("type") is not None:
                continue
            try:
                ln = int(line_el.get("num", "0"))
                count = int(line_el.get("count", "0"))
                if ln > 0:
                    cov.line_hits[ln] = count
            except ValueError:
                continue
    return by_file


def parse_go_coverage(text: str, repo_root: Path) -> dict[str, CovFile]:
    """Go's native `coverage.out` format:
        mode: set|count|atomic
        <file>:<startLine>.<startCol>,<endLine>.<endCol> <numStmts> <count>
    Lines are block ranges; we expand to per-line hit info."""
    by_file: dict[str, CovFile] = {}
    lines = text.splitlines()
    if not lines or not lines[0].startswith("mode:"):
        return by_file
    block_re = re.compile(r"^(.+):(\d+)\.\d+,(\d+)\.\d+\s+(\d+)\s+(\d+)$")
    for raw in lines[1:]:
        m = block_re.match(raw)
        if not m:
            continue
        import_path = m.group(1)  # e.g. github.com/foo/bar/pkg/file.go
        start_line = int(m.group(2))
        end_line = int(m.group(3))
        count = int(m.group(5))
        # Reduce the import path to a repo-relative path. Strategy: try the
        # last path segment, then trim module prefix heuristically.
        rel_candidates: list[str] = []
        parts = import_path.split("/")
        for i in range(len(parts)):
            rel_candidates.append("/".join(parts[i:]))
        chosen: str | None = None
        for cand in rel_candidates:
            if (repo_root / cand).exists():
                chosen = cand
                break
        if chosen is None:
            chosen = parts[-1]
        cov = by_file.setdefault(chosen, CovFile())
        for ln in range(start_line, end_line + 1):
            prev = cov.line_hits.get(ln, 0)
            cov.line_hits[ln] = max(prev, count)
    return by_file


def parse_coveragepy_json(text: str, repo_root: Path) -> dict[str, CovFile]:
    """coverage.py `coverage json` output."""
    by_file: dict[str, CovFile] = {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return by_file
    files = data.get("files") or {}
    for fname, finfo in files.items():
        p = Path(fname)
        rel = fname
        if p.is_absolute():
            try:
                rel = str(p.resolve().relative_to(repo_root.resolve())).replace(os.sep, "/")
            except ValueError:
                rel = str(p)
        cov = by_file.setdefault(rel, CovFile())
        executed = set(finfo.get("executed_lines", []))
        missing = set(finfo.get("missing_lines", []))
        for ln in executed:
            cov.line_hits[ln] = 1
        for ln in missing:
            cov.line_hits.setdefault(ln, 0)
    return by_file


# ---------- coverage auto-discovery ----------

COVERAGE_CANDIDATES: list[tuple[str, str]] = [
    ("coverage/lcov.info", "lcov"),
    ("coverage/lcov/lcov.info", "lcov"),
    ("coverage/lcov-report/lcov.info", "lcov"),
    ("coverage.xml", "cobertura_or_clover"),
    ("coverage/cobertura-coverage.xml", "cobertura"),
    ("coverage/coverage.xml", "cobertura_or_clover"),
    ("target/site/jacoco/jacoco.xml", "jacoco"),
    ("build/reports/jacoco/test/jacocoTestReport.xml", "jacoco"),
    ("build/reports/jacoco/jacocoTestReport.xml", "jacoco"),
    ("coverage.out", "go"),
    ("coverage.json", "coveragepy"),
    ("coverage/coverage-final.json", "coveragepy"),  # istanbul-compatible JSON shape differs; we skip
    ("clover.xml", "clover"),
]


def _sniff_xml(text: str) -> str:
    """Disambiguate cobertura vs clover vs jacoco by content."""
    snippet = text[:4096]
    if "<coverage" in snippet and "clover" in snippet.lower():
        return "clover"
    if "<coverage" in snippet and ("lines-covered" in snippet or "line-rate" in snippet or "<packages" in snippet):
        return "cobertura"
    if "<report" in snippet and "jacoco" in snippet.lower():
        return "jacoco"
    if "<clover" in snippet:
        return "clover"
    return "cobertura"  # default guess — cobertura is most common


def auto_find_coverage(repo_root: Path) -> tuple[Path, str] | None:
    """Return (path, format_hint) or None."""
    # Try explicit candidate paths first.
    for rel, hint in COVERAGE_CANDIDATES:
        p = repo_root / rel
        if p.exists():
            fmt = hint
            if fmt == "cobertura_or_clover":
                try:
                    fmt = _sniff_xml(p.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    fmt = "cobertura"
            return p, fmt

    # Recursive fallback under coverage/ — pick newest.
    cov_dir = repo_root / "coverage"
    if cov_dir.is_dir():
        lcovs = sorted(cov_dir.rglob("lcov.info"), key=lambda p: p.stat().st_mtime, reverse=True)
        if lcovs:
            return lcovs[0], "lcov"
        coburas = sorted(cov_dir.rglob("*.xml"), key=lambda p: p.stat().st_mtime, reverse=True)
        for p in coburas:
            try:
                fmt = _sniff_xml(p.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
            return p, fmt

    # Nx-style: coverage/<project>/lcov.info already caught above; also look at jacoco.
    for target_dir in ("target", "build"):
        d = repo_root / target_dir
        if d.is_dir():
            for p in d.rglob("jacoco*.xml"):
                return p, "jacoco"

    return None


def parse_coverage(path: Path, fmt: str, repo_root: Path) -> dict[str, CovFile]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if fmt == "lcov":
        return parse_lcov(text, repo_root)
    if fmt == "cobertura":
        return parse_cobertura(text, repo_root)
    if fmt == "clover":
        return parse_clover(text, repo_root)
    if fmt == "jacoco":
        return parse_jacoco(text, repo_root)
    if fmt == "go":
        return parse_go_coverage(text, repo_root)
    if fmt == "coveragepy":
        return parse_coveragepy_json(text, repo_root)
    # Unknown — best effort: try each parser and keep the one with content.
    for fn in (parse_lcov, parse_cobertura, parse_jacoco, parse_clover, parse_go_coverage, parse_coveragepy_json):
        try:
            result = fn(text, repo_root)
        except Exception:
            continue
        if result:
            return result
    return {}


def detect_format_from_content(path: Path) -> str:
    """Sniff file content to pick a parser when the user passes --lcov to something else."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(4096)
    except OSError:
        return "lcov"
    if head.lstrip().startswith("<?xml") or head.lstrip().startswith("<"):
        return _sniff_xml(head)
    if head.startswith("mode:"):
        return "go"
    if head.lstrip().startswith("{"):
        return "coveragepy"
    if "SF:" in head or "DA:" in head:
        return "lcov"
    return "lcov"


# ---------- CRAP score ----------

def crap_score(complexity: int, coverage: float) -> float:
    return complexity * complexity * ((1 - coverage) ** 3) + complexity


def coverage_for(func: FuncSpan, cov: CovFile | None) -> tuple[int, int, float]:
    if cov is None:
        return 0, 0, 0.0
    executable = 0
    covered = 0
    for ln in range(func.body_start_line, func.body_end_line + 1):
        if ln in cov.line_hits:
            executable += 1
            if cov.line_hits[ln] > 0:
                covered += 1
    if executable == 0:
        return 0, 0, 0.0
    return executable, covered, covered / executable


# ---------- analysis ----------

@dataclass
class Finding:
    file: str
    name: str
    kind: str
    language: str
    start_line: int
    end_line: int
    complexity: int
    coverage: float
    executable_lines: int
    covered_lines: int
    crap: float


def analyze(
    diff_text: str,
    repo_root: Path,
    cov_by_file: dict[str, CovFile],
    threshold: float,
) -> list[Finding]:
    touched = parse_diff(diff_text)
    findings: list[Finding] = []
    for rel_path, touched_lines in touched.items():
        lang = language_of(rel_path)
        if lang is None:
            continue
        abs_path = repo_root / rel_path
        if not abs_path.is_file():
            continue
        src = abs_path.read_text(encoding="utf-8", errors="replace")
        stripped = strip_source(lang, src)
        funcs = discover_functions(lang, src, stripped)
        cov = cov_by_file.get(rel_path) or cov_by_file.get(rel_path.replace(os.sep, "/"))
        if cov is None:
            # Try matching by basename (coverage parsers sometimes return absolute paths).
            basename = os.path.basename(rel_path)
            for k, v in cov_by_file.items():
                if k.endswith("/" + basename) or k == basename:
                    cov = v
                    break
        for fn in funcs:
            fn_range = set(range(fn.body_start_line, fn.body_end_line + 1))
            if not fn_range & touched_lines:
                continue
            body_lines = stripped.splitlines()[fn.body_start_line - 1:fn.body_end_line]
            body_stripped = "\n".join(body_lines)
            complexity = compute_complexity(lang, body_stripped)
            execu, cov_lines, cov_frac = coverage_for(fn, cov)
            score = crap_score(complexity, cov_frac)
            if score < threshold:
                continue
            findings.append(Finding(
                file=rel_path,
                name=fn.name,
                kind=fn.kind,
                language=lang,
                start_line=fn.start_line,
                end_line=fn.body_end_line,
                complexity=complexity,
                coverage=round(cov_frac, 3),
                executable_lines=execu,
                covered_lines=cov_lines,
                crap=round(score, 2),
            ))
    findings.sort(key=lambda f: f.crap, reverse=True)
    return findings


def render_markdown(findings: list[Finding], threshold: float, had_cov: bool, fmt_label: str | None) -> str:
    if not findings:
        return f"# CRAP report\n\nNo functions above threshold ({threshold}).\n"
    lines = [f"# CRAP report\n\nThreshold: **{threshold}** — {len(findings)} finding(s), ranked worst-first.\n"]
    if not had_cov:
        lines.append(
            "> No coverage file found — coverage treated as 0% for all functions. "
            "Run tests with coverage to refine.\n"
        )
    elif fmt_label:
        lines.append(f"> Coverage source: **{fmt_label}**.\n")
    lines.append("| # | File:Line | Function | Lang | Complexity | Coverage | CRAP |")
    lines.append("|---|-----------|----------|------|-----------:|---------:|-----:|")
    for i, f in enumerate(findings, 1):
        cov_pct = "n/a" if f.executable_lines == 0 else f"{int(f.coverage * 100)}% ({f.covered_lines}/{f.executable_lines})"
        lines.append(
            f"| {i} | `{f.file}:{f.start_line}` | `{f.name}` ({f.kind}) "
            f"| {f.language} | {f.complexity} | {cov_pct} | **{f.crap}** |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Compute CRAP scores for diff-touched functions.")
    p.add_argument("--diff", required=True, help="Path to unified diff, or '-' for stdin.")
    p.add_argument("--repo-root", default=".", help="Repository root (default: cwd).")
    p.add_argument("--lcov", default=None,
                   help="Path to coverage file (any supported format — flag name is historical).")
    p.add_argument("--threshold", type=float, default=20.0,
                   help="Minimum CRAP score to report (default: 20).")
    p.add_argument("--format", choices=("json", "md", "both"), default="both")
    args = p.parse_args(argv)

    if args.diff == "-":
        diff_text = sys.stdin.read()
    else:
        diff_text = Path(args.diff).read_text(encoding="utf-8", errors="replace")

    repo_root = Path(args.repo_root).resolve()

    cov_path: Path | None = None
    cov_fmt: str | None = None
    if args.lcov:
        cov_path = Path(args.lcov)
        cov_fmt = detect_format_from_content(cov_path)
    else:
        discovered = auto_find_coverage(repo_root)
        if discovered:
            cov_path, cov_fmt = discovered

    cov_by_file: dict[str, CovFile] = {}
    if cov_path and cov_path.exists() and cov_fmt:
        cov_by_file = parse_coverage(cov_path, cov_fmt, repo_root)

    findings = analyze(diff_text, repo_root, cov_by_file, args.threshold)

    if args.format in ("json", "both"):
        payload = {
            "threshold": args.threshold,
            "coverage_file": str(cov_path) if cov_path else None,
            "coverage_format": cov_fmt,
            "findings": [asdict(f) for f in findings],
        }
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")

    if args.format in ("md", "both"):
        out = render_markdown(
            findings, args.threshold,
            had_cov=bool(cov_path and cov_path.exists()),
            fmt_label=cov_fmt,
        )
        stream = sys.stderr if args.format == "both" else sys.stdout
        stream.write(out)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
