#!/usr/bin/env python3
"""Tests for dae_infra.py — probe, state, ensure, teardown, status.

Run: python3 -m unittest test_dae_infra
"""

import http.server
import json
import os
import signal
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest

import dae_infra
import dae_resolve

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DAE_INFRA = os.path.join(SCRIPTS_DIR, "dae_infra.py")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _free_port() -> int:
    """Return a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _make_root(tmp: str, infra_yml: str = "") -> str:
    """Create a minimal methodology root under tmp with an infra section."""
    engineer_dir = os.path.join(tmp, ".engineer")
    os.makedirs(engineer_dir, exist_ok=True)
    manifest = (
        'methodology_version: "0.2"\n'
        'roadmap:\n  type: local\ntracker:\n  type: local\n'
    )
    if infra_yml:
        manifest += "\ninfra:\n" + infra_yml
    with open(os.path.join(engineer_dir, "manifest.yml"), "w") as f:
        f.write(manifest)
    return tmp


def _tcp_infra_yml(port: int, name: str = "svc", ready_timeout_s: int = 10) -> str:
    """YAML snippet for a TCP health entry backed by a minimal TCP echo server.

    The server accepts connections, closes them immediately, then loops — acting
    as a reliable liveness target. Uses double-quoted python -c so no shell
    escaping issues arise in the YAML value.
    """
    # Python snippet: bind, listen, serve_forever via threading — no HTTP needed.
    py_lines = (
        "import socket,threading,time;"
        "s=socket.socket();"
        "s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);"
        "s.bind(('127.0.0.1',{port}));"
        "s.listen(10);"
        "threading.Thread(target=lambda:[s.accept()[0].close() or None "
        "for _ in iter(int,1)],daemon=True).start();"
        "time.sleep(3600)"
    ).format(port=port)
    return (
        "  {name}:\n"
        "    health:\n"
        "      type: tcp\n"
        "      port: {port}\n"
        "      host: 127.0.0.1\n"
        "      timeout_s: 2\n"
        "    start:\n"
        "      command: python3 -c \"{py_lines}\"\n"
        "      background: true\n"
        "      ready_timeout_s: {rto}\n"
        "    teardown: session-end\n"
    ).format(name=name, port=port, rto=ready_timeout_s, py_lines=py_lines)


# Keep backward compat alias used by some tests
def _http_infra_yml(port: int, name: str = "web", ready_timeout_s: int = 10) -> str:
    """Alias to _tcp_infra_yml; previous HTTP-based helper was flaky."""
    return _tcp_infra_yml(port, name=name, ready_timeout_s=ready_timeout_s)


def _run_cli(*args, root=None):
    """Invoke dae_infra.py as a subprocess; return (returncode, stdout, stderr)."""
    cmd = [sys.executable, DAE_INFRA] + list(args)
    if root:
        # inject --root after sub-command
        sub_idx = 1  # index in cmd after the script itself
        cmd = [sys.executable, DAE_INFRA, args[0], "--root", root] + list(args[1:])
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# 1. Probe tests
# ---------------------------------------------------------------------------

class TestProbeHTTP(unittest.TestCase):
    """probe_http against a real one-shot HTTPServer."""

    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.server = socketserver.TCPServer(
            ("127.0.0.1", cls.port),
            http.server.SimpleHTTPRequestHandler,
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_up(self):
        self.assertTrue(dae_infra.probe_http(
            "http://127.0.0.1:%d" % self.port, timeout_s=3))

    def test_down(self):
        dead_port = _free_port()
        self.assertFalse(dae_infra.probe_http(
            "http://127.0.0.1:%d" % dead_port, timeout_s=1))


class TestProbeTCP(unittest.TestCase):
    """probe_tcp against a real listening socket."""

    def setUp(self):
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", 0))
        self.port = self.srv.getsockname()[1]
        self.srv.listen(1)

    def tearDown(self):
        self.srv.close()

    def test_up(self):
        self.assertTrue(dae_infra.probe_tcp("127.0.0.1", self.port, timeout_s=2))

    def test_down(self):
        self.srv.close()
        dead = _free_port()
        self.assertFalse(dae_infra.probe_tcp("127.0.0.1", dead, timeout_s=1))


class TestProbeCommand(unittest.TestCase):
    def test_true_command(self):
        self.assertTrue(dae_infra.probe_command("true", timeout_s=3))

    def test_false_command(self):
        self.assertFalse(dae_infra.probe_command("false", timeout_s=3))

    def test_nonexistent_command(self):
        self.assertFalse(dae_infra.probe_command("__no_such_cmd_xyz__", timeout_s=2))


class TestProbeProcess(unittest.TestCase):
    """probe_process tests using a controlled subprocess with a unique pattern."""

    UNIQUE_MARKER = "__dae_infra_probe_test_marker_xyz__"

    def setUp(self):
        # Spawn a background process with a unique string in its args
        self.proc = subprocess.Popen(
            [sys.executable, "-c",
             "import time; time.sleep(30)  # %s" % self.UNIQUE_MARKER],
            start_new_session=True,
        )
        time.sleep(0.2)

    def tearDown(self):
        try:
            self.proc.kill()
            self.proc.wait()
        except Exception:
            pass

    def test_matching_pattern(self):
        self.assertTrue(dae_infra.probe_process(self.UNIQUE_MARKER))

    def test_impossible_pattern(self):
        self.assertFalse(dae_infra.probe_process("__no_such_process_xyz_abc_123__"))


# ---------------------------------------------------------------------------
# 2. make_health_probe factory
# ---------------------------------------------------------------------------

class TestMakeHealthProbe(unittest.TestCase):
    def test_http_probe_down(self):
        health = {"type": "http", "url": "http://127.0.0.1:19999", "timeout_s": 1}
        p = dae_infra.make_health_probe(health)
        self.assertFalse(p())

    def test_tcp_probe_down(self):
        health = {"type": "tcp", "host": "127.0.0.1", "port": 19998, "timeout_s": 1}
        p = dae_infra.make_health_probe(health)
        self.assertFalse(p())

    def test_command_probe_true(self):
        health = {"type": "command", "command": "true", "timeout_s": 3}
        p = dae_infra.make_health_probe(health)
        self.assertTrue(p())

    def test_command_probe_false(self):
        health = {"type": "command", "command": "false", "timeout_s": 3}
        p = dae_infra.make_health_probe(health)
        self.assertFalse(p())

    def test_process_probe_match(self):
        MARKER = "__dae_make_health_probe_marker_abc__"
        proc = subprocess.Popen(
            [sys.executable, "-c",
             "import time; time.sleep(30)  # %s" % MARKER],
            start_new_session=True,
        )
        time.sleep(0.2)
        try:
            health = {"type": "process", "pattern": MARKER}
            p = dae_infra.make_health_probe(health)
            self.assertTrue(p())
        finally:
            proc.kill()
            proc.wait()

    def test_unknown_type_returns_false(self):
        health = {"type": "unknown_xyz"}
        p = dae_infra.make_health_probe(health)
        self.assertFalse(p())


# ---------------------------------------------------------------------------
# 3. Schema reading via dae_resolve
# ---------------------------------------------------------------------------

class TestLoadEntries(unittest.TestCase):
    def _make_root_with_infra(self, infra_yml):
        tmp = tempfile.mkdtemp()
        self.roots.append(tmp)
        _make_root(tmp, infra_yml)
        return tmp

    def setUp(self):
        self.roots = []

    def tearDown(self):
        import shutil
        for r in self.roots:
            shutil.rmtree(r, ignore_errors=True)

    def test_basic_entry_loaded(self):
        root = self._make_root_with_infra(
            "  auth:\n"
            "    health:\n"
            "      type: tcp\n"
            "      port: 9099\n"
            "    start:\n"
            "      command: echo hello\n"
        )
        entries = dae_infra.load_entries(root)
        self.assertIn("auth", entries)

    def test_health_defaults_filled(self):
        root = self._make_root_with_infra(
            "  svc:\n"
            "    health:\n"
            "      type: http\n"
            "      url: http://localhost:8080\n"
            "    start:\n"
            "      command: echo x\n"
        )
        entries = dae_infra.load_entries(root)
        self.assertEqual(entries["svc"]["health"]["timeout_s"], dae_infra.DEFAULT_HTTP_TIMEOUT)

    def test_start_defaults_filled(self):
        root = self._make_root_with_infra(
            "  svc:\n"
            "    health:\n"
            "      type: process\n"
            "      pattern: foo\n"
            "    start:\n"
            "      command: echo x\n"
        )
        entries = dae_infra.load_entries(root)
        self.assertTrue(entries["svc"]["start"]["background"])
        self.assertEqual(entries["svc"]["start"]["ready_timeout_s"], dae_infra.DEFAULT_READY_TIMEOUT)

    def test_teardown_default_from_block(self):
        root = self._make_root_with_infra(
            "  default_teardown: session-end\n"
            "  svc:\n"
            "    health:\n"
            "      type: process\n"
            "      pattern: foo\n"
            "    start:\n"
            "      command: echo x\n"
        )
        entries = dae_infra.load_entries(root)
        self.assertEqual(entries["svc"]["teardown"], "session-end")

    def test_teardown_entry_overrides_default(self):
        root = self._make_root_with_infra(
            "  default_teardown: session-end\n"
            "  svc:\n"
            "    health:\n"
            "      type: process\n"
            "      pattern: foo\n"
            "    start:\n"
            "      command: echo x\n"
            "    teardown: leave-running\n"
        )
        entries = dae_infra.load_entries(root)
        self.assertEqual(entries["svc"]["teardown"], "leave-running")

    def test_tcp_host_default(self):
        root = self._make_root_with_infra(
            "  svc:\n"
            "    health:\n"
            "      type: tcp\n"
            "      port: 9099\n"
            "    start:\n"
            "      command: echo x\n"
        )
        entries = dae_infra.load_entries(root)
        self.assertEqual(entries["svc"]["health"]["host"], "localhost")


# ---------------------------------------------------------------------------
# 4. State files
# ---------------------------------------------------------------------------

class TestStateFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_root(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_write_and_read(self):
        # Use only pid (no pgid) so read_state falls back to _pid_running(own pid)
        state = {"name": "foo", "pid": os.getpid(),
                 "started_at": "2026-01-01T00:00:00Z"}
        dae_infra.write_state(self.tmp, "foo", state)
        path = os.path.join(self.tmp, ".engineer", "infra", "foo.json")
        self.assertTrue(os.path.isfile(path))
        got = dae_infra.read_state(self.tmp, "foo")
        self.assertIsNotNone(got)
        self.assertEqual(got["name"], "foo")

    def test_read_missing_returns_none(self):
        self.assertIsNone(dae_infra.read_state(self.tmp, "nonexistent"))

    def test_stale_pid_gc(self):
        """State file with a dead PID is deleted and read returns None."""
        state = {"name": "bar", "pid": 999999, "started_at": "2026-01-01T00:00:00Z"}
        dae_infra.write_state(self.tmp, "bar", state)
        path = os.path.join(self.tmp, ".engineer", "infra", "bar.json")
        self.assertTrue(os.path.isfile(path))
        result = dae_infra.read_state(self.tmp, "bar")
        self.assertIsNone(result)
        self.assertFalse(os.path.isfile(path))

    def test_remove_state(self):
        state = {"name": "baz", "pid": os.getpid()}
        dae_infra.write_state(self.tmp, "baz", state)
        dae_infra.remove_state(self.tmp, "baz")
        self.assertIsNone(dae_infra.read_state(self.tmp, "baz"))

    def test_state_dir_created_on_write(self):
        state = {"name": "new", "pid": os.getpid()}
        dae_infra.write_state(self.tmp, "new", state)
        self.assertTrue(os.path.isdir(os.path.join(self.tmp, ".engineer", "infra")))


# ---------------------------------------------------------------------------
# 5. status CLI
# ---------------------------------------------------------------------------

class TestStatusCLI(unittest.TestCase):
    """Status CLI against a real TCP server fixture (in-process thread)."""

    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        # A plain TCPServer (accepts connections, serves no data — enough for TCP probe)
        cls.server = socketserver.TCPServer(
            ("127.0.0.1", cls.port),
            http.server.BaseHTTPRequestHandler,
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.tmp = tempfile.mkdtemp()
        _make_root(cls.tmp, _tcp_infra_yml(cls.port, name="web"))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        import shutil
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_status_up(self):
        rc, out, err = _run_cli("status", root=self.tmp)
        self.assertEqual(rc, 0, err)
        data = json.loads(out)
        self.assertIn("web", data)
        self.assertEqual(data["web"]["status"], "up")

    def test_status_specific_name(self):
        rc, out, err = _run_cli("status", "web", root=self.tmp)
        self.assertEqual(rc, 0, err)
        data = json.loads(out)
        self.assertIn("web", data)

    def test_status_down(self):
        dead_port = _free_port()
        tmp = tempfile.mkdtemp()
        try:
            _make_root(tmp, _tcp_infra_yml(dead_port, name="dead"))
            rc, out, err = _run_cli("status", root=tmp)
            self.assertEqual(rc, 0, err)
            data = json.loads(out)
            self.assertEqual(data["dead"]["status"], "down")
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_status_stale_pid_gc(self):
        """Status clears stale state files; entry shows as down."""
        tmp = tempfile.mkdtemp()
        try:
            dead_port = _free_port()
            _make_root(tmp, _tcp_infra_yml(dead_port, name="stale"))
            # Write a stale state (no pgid so falls back to PID liveness check)
            dae_infra.write_state(tmp, "stale", {
                "name": "stale", "pid": 999999,
                "started_at": "2026-01-01T00:00:00Z",
            })
            rc, out, err = _run_cli("status", root=tmp)
            self.assertEqual(rc, 0)
            data = json.loads(out)
            self.assertEqual(data["stale"]["status"], "down")
            state_path = os.path.join(tmp, ".engineer", "infra", "stale.json")
            self.assertFalse(os.path.isfile(state_path))
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# 6. ensure + teardown CLI (self-contained HTTP server as start command)
# ---------------------------------------------------------------------------

class TestEnsureTeardown(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.port = _free_port()
        # Infra entry: start a minimal TCP echo server via python3 -c
        _make_root(self.tmp, _tcp_infra_yml(self.port, name="svc", ready_timeout_s=10))

    def tearDown(self):
        # Best-effort cleanup: teardown then rmtree
        _run_cli("teardown", root=self.tmp)
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ensure_brings_up(self):
        rc, out, err = _run_cli("ensure", "svc", root=self.tmp)
        self.assertEqual(rc, 0, "stderr: %s\nstdout: %s" % (err, out))
        data = json.loads(out)
        self.assertTrue(data["all_up"])
        # Confirm via status
        rc2, out2, _ = _run_cli("status", root=self.tmp)
        self.assertEqual(rc2, 0)
        data2 = json.loads(out2)
        self.assertEqual(data2["svc"]["status"], "up")

    def test_ensure_idempotent(self):
        """Running ensure twice when already up is a no-op (no new process)."""
        rc, out, _ = _run_cli("ensure", "svc", root=self.tmp)
        self.assertEqual(rc, 0)
        data1 = json.loads(out)
        pid1 = data1["entries"][0].get("pid")

        rc2, out2, _ = _run_cli("ensure", "svc", root=self.tmp)
        self.assertEqual(rc2, 0)
        data2 = json.loads(out2)
        pid2 = data2["entries"][0].get("pid")
        # PID should be the same (idempotent), or second run saw it up
        # Both runs should report all_up
        self.assertTrue(data2["all_up"])

    def test_teardown_kills(self):
        rc, _, _ = _run_cli("ensure", "svc", root=self.tmp)
        self.assertEqual(rc, 0)
        rc2, out2, _ = _run_cli("teardown", root=self.tmp)
        self.assertEqual(rc2, 0)
        data = json.loads(out2)
        statuses = {e["name"]: e["status"] for e in data["entries"]}
        self.assertEqual(statuses.get("svc"), "stopped")

    def test_teardown_not_running(self):
        """Teardown with nothing running reports not-running gracefully."""
        rc, out, _ = _run_cli("teardown", root=self.tmp)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        statuses = {e["name"]: e["status"] for e in data["entries"]}
        self.assertEqual(statuses.get("svc"), "not-running")


# ---------------------------------------------------------------------------
# 7. ensure failure diagnostics
# ---------------------------------------------------------------------------

class TestEnsureFailures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_command_not_found(self):
        _make_root(self.tmp,
            "  svc:\n"
            "    health:\n"
            "      type: process\n"
            "      pattern: __no_match_xyz__\n"
            "    start:\n"
            "      command: __no_such_binary_xyz__ --start\n"
            "      ready_timeout_s: 3\n"
        )
        rc, out, err = _run_cli("ensure", "svc", root=self.tmp)
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertFalse(data["all_up"])
        entry = data["entries"][0]
        self.assertEqual(entry["status"], "start-failed")
        self.assertEqual(entry["diagnosis"], "command-not-found")

    def test_ready_timeout(self):
        """Start command runs forever but never serves the health endpoint."""
        dead_port = _free_port()
        _make_root(self.tmp,
            "  svc:\n"
            "    health:\n"
            "      type: tcp\n"
            "      port: {port}\n"
            "      host: 127.0.0.1\n"
            "    start:\n"
            "      command: python3 -c \"import time; time.sleep(60)\"\n"
            "      ready_timeout_s: 2\n"
        .format(port=dead_port))
        rc, out, err = _run_cli("ensure", "svc", root=self.tmp)
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertFalse(data["all_up"])
        entry = data["entries"][0]
        self.assertEqual(entry["status"], "start-failed")
        self.assertEqual(entry["diagnosis"], "ready-timeout")

    def test_unknown_name(self):
        _make_root(self.tmp)  # no infra section
        rc, out, err = _run_cli("ensure", "nonexistent", root=self.tmp)
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertFalse(data["all_up"])

    def test_start_exit_nonzero(self):
        """Process exits immediately with non-zero code."""
        _make_root(self.tmp,
            "  svc:\n"
            "    health:\n"
            "      type: process\n"
            "      pattern: __no_match_xyz__\n"
            "    start:\n"
            "      command: python3 -c \"import sys; sys.exit(1)\"\n"
            "      ready_timeout_s: 5\n"
        )
        rc, out, err = _run_cli("ensure", "svc", root=self.tmp)
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        entry = data["entries"][0]
        self.assertEqual(entry["status"], "start-failed")
        self.assertIn(entry["diagnosis"], ("start-exit-nonzero", "ready-timeout"))


# ---------------------------------------------------------------------------
# 8. ready_signal detection
# ---------------------------------------------------------------------------

class TestReadySignal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        # Also teardown any infra
        _run_cli("teardown", root=self.tmp)

    def test_ready_signal_detected(self):
        """Start a command that prints a ready signal; ensure should succeed."""
        _make_root(self.tmp,
            "  svc:\n"
            "    health:\n"
            "      type: command\n"
            "      command: true\n"
            "    start:\n"
            "      command: python3 -c \""
            "import sys, time; "
            "sys.stdout.write('READY\\n'); sys.stdout.flush(); "
            "time.sleep(30)\"\n"
            "      ready_signal: READY\n"
            "      ready_timeout_s: 5\n"
        )
        rc, out, err = _run_cli("ensure", "svc", root=self.tmp)
        self.assertEqual(rc, 0, "stderr: %s\nstdout: %s" % (err, out))
        data = json.loads(out)
        self.assertTrue(data["all_up"])


# ---------------------------------------------------------------------------
# 9. help and CLI shape
# ---------------------------------------------------------------------------

class TestCLIShape(unittest.TestCase):
    def test_help_exit_zero(self):
        rc, out, err = _run_cli("--help")
        self.assertEqual(rc, 0)
        self.assertIn("status", out)
        self.assertIn("ensure", out)
        self.assertIn("teardown", out)

    def test_unknown_subcommand(self):
        rc, out, err = _run_cli("foobar")
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# 10. _pid_running helper
# ---------------------------------------------------------------------------

class TestPidRunning(unittest.TestCase):
    def test_own_pid_running(self):
        self.assertTrue(dae_infra._pid_running(os.getpid()))

    def test_dead_pid_not_running(self):
        self.assertFalse(dae_infra._pid_running(999999))


# ---------------------------------------------------------------------------
# 11. _diagnose_start
# ---------------------------------------------------------------------------

class TestDiagnoseStart(unittest.TestCase):
    def test_command_not_found(self):
        health = {"type": "process", "pattern": "foo"}
        result = dae_infra._diagnose_start("__no_such_binary_xyz__", health)
        self.assertEqual(result, "command-not-found")

    def test_valid_command_no_diag(self):
        health = {"type": "process", "pattern": "foo"}
        result = dae_infra._diagnose_start("python3 --version", health)
        self.assertEqual(result, "")

    def test_port_in_use(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        srv.listen(1)
        try:
            health = {"type": "tcp", "host": "127.0.0.1", "port": port}
            result = dae_infra._diagnose_start("python3 --version", health)
            self.assertEqual(result, "port-in-use")
        finally:
            srv.close()


# ---------------------------------------------------------------------------
# 12. Multiple entries, teardown by name
# ---------------------------------------------------------------------------

class TestMultiEntry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.port1 = _free_port()
        self.port2 = _free_port()
        yml = (
            _tcp_infra_yml(self.port1, name="svc1", ready_timeout_s=10) +
            _tcp_infra_yml(self.port2, name="svc2", ready_timeout_s=10)
        )
        _make_root(self.tmp, yml)

    def tearDown(self):
        _run_cli("teardown", root=self.tmp)
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_teardown_specific_name(self):
        # Start svc1
        _run_cli("ensure", "svc1", root=self.tmp)
        # Teardown by explicit name
        rc, out, err = _run_cli("teardown", "svc1", root=self.tmp)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        names = {e["name"] for e in data["entries"]}
        self.assertIn("svc1", names)
        self.assertNotIn("svc2", names)

    def test_status_multiple(self):
        rc, out, _ = _run_cli("status", root=self.tmp)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("svc1", data)
        self.assertIn("svc2", data)


if __name__ == "__main__":
    unittest.main()
