#!/usr/bin/env python3
"""Tests for dae_arch — the charter architecture fitness checker.

Run: python3 -m unittest test_dae_arch -v
"""
import os
import shutil
import tempfile
import unittest

import dae_arch as da


class TestGlob(unittest.TestCase):
    def test_star_within_segment(self):
        rx = da._glob_to_regex("src/*.py")
        self.assertTrue(rx.match("src/a.py"))
        self.assertFalse(rx.match("src/sub/a.py"))

    def test_double_star_spans_segments(self):
        rx = da._glob_to_regex("src/**/*.py")
        self.assertTrue(rx.match("src/a.py"))
        self.assertTrue(rx.match("src/x/y/a.py"))
        self.assertFalse(rx.match("lib/a.py"))

    def test_match_any(self):
        globs = da._compile_globs(["src/**", "lib/**"])
        self.assertTrue(da._match_any("src/x/y.py", globs))
        self.assertTrue(da._match_any("lib/z.py", globs))
        self.assertFalse(da._match_any("test/z.py", globs))


def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class TestGenericChecks(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def test_forbidden_pattern_hit(self):
        _write(self.root, "src/a.py", "x = 1\nconsole.log(x)\n")
        rules = [{"pattern": r"console\.log", "paths": ["src/**"],
                  "reason": "use the logger"}]
        v = da.check_forbidden(self.root, ["src/a.py"], rules)
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0][0], "src/a.py")
        self.assertEqual(v[0][1], 2)
        self.assertEqual(v[0][2], "forbidden_patterns")

    def test_forbidden_pattern_out_of_scope(self):
        _write(self.root, "lib/a.py", "console.log(1)\n")
        rules = [{"pattern": r"console\.log", "paths": ["src/**"]}]
        self.assertEqual(da.check_forbidden(self.root, ["lib/a.py"], rules), [])

    def test_naming_violation(self):
        rules = [{"paths": ["src/**"], "filename_must_match": r"^[a-z0-9_]+\.py$",
                  "reason": "snake_case"}]
        v = da.check_naming(["src/BadName.py"], rules)
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0][2], "naming")

    def test_naming_ok(self):
        rules = [{"paths": ["src/**"], "filename_must_match": r"^[a-z0-9_]+\.py$"}]
        self.assertEqual(da.check_naming(["src/good_name.py"], rules), [])

    def test_file_size_over_cap(self):
        _write(self.root, "src/big.py", "\n".join("x" for _ in range(50)) + "\n")
        cfg = {"max_lines": 10}
        v = da.check_file_size(self.root, ["src/big.py"], cfg)
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0][2], "file_size")

    def test_file_size_override(self):
        _write(self.root, "src/generated/g.py", "\n".join("x" for _ in range(50)) + "\n")
        cfg = {"max_lines": 10,
               "overrides": [{"paths": ["**/generated/**"], "max_lines": 1000}]}
        self.assertEqual(da.check_file_size(self.root, ["src/generated/g.py"], cfg), [])


class TestImports(unittest.TestCase):
    def test_python_imports(self):
        text = "import os\nfrom pkg.mod import thing\nfrom .relmod import other\n"
        specs = da.extract_imports("a/b.py", text)
        self.assertIn("os", specs)
        self.assertIn("pkg.mod", specs)
        self.assertIn(".relmod", specs)

    def test_js_imports(self):
        text = ('import x from "./local";\n'
                'const y = require("../up/dep");\n'
                'import "react";\n')
        specs = da.extract_imports("a/b.ts", text)
        self.assertIn("./local", specs)
        self.assertIn("../up/dep", specs)
        self.assertIn("react", specs)


class TestLayers(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def test_layering_violation_python(self):
        _write(self.root, "src/domain/order.py", "from src.infra.db import save\n")
        _write(self.root, "src/infra/db.py", "def save(): pass\n")
        layers = [
            {"name": "domain", "paths": ["src/domain/**"],
             "may_not_import": ["infra"]},
            {"name": "infra", "paths": ["src/infra/**"]},
        ]
        files = ["src/domain/order.py", "src/infra/db.py"]
        v = da.check_layers(self.root, files, layers, files)
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0][2], "layers")
        self.assertIn("domain", v[0][3])
        self.assertIn("infra", v[0][3])

    def test_layering_clean(self):
        _write(self.root, "src/domain/order.py", "from src.domain.money import M\n")
        _write(self.root, "src/domain/money.py", "M = 1\n")
        layers = [{"name": "domain", "paths": ["src/domain/**"],
                   "may_not_import": ["infra"]},
                  {"name": "infra", "paths": ["src/infra/**"]}]
        files = ["src/domain/order.py", "src/domain/money.py"]
        self.assertEqual(da.check_layers(self.root, files, layers, files), [])

    def test_layering_violation_js(self):
        _write(self.root, "src/web/page.ts", 'import {db} from "../infra/db";\n')
        _write(self.root, "src/infra/db.ts", "export const db = 1;\n")
        layers = [{"name": "web", "paths": ["src/web/**"],
                   "may_not_import": ["infra"]},
                  {"name": "infra", "paths": ["src/infra/**"]}]
        files = ["src/web/page.ts", "src/infra/db.ts"]
        v = da.check_layers(self.root, files, layers, files)
        self.assertEqual(len(v), 1)


class TestAudit(unittest.TestCase):
    def test_audit_collects_all_kinds(self):
        rules = {
            "forbidden_patterns": [{"pattern": "TODO", "paths": ["**"]}],
            "file_size": {"max_lines": 1},
        }
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        _write(root, "src/a.py", "TODO\nx\n")
        v = da.audit_rules(root, ["src/a.py"], rules)
        kinds = sorted(set(x[2] for x in v))
        self.assertEqual(kinds, ["file_size", "forbidden_patterns"])

    def test_audit_empty_rules(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        self.assertEqual(da.audit_rules(root, [], {}), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
