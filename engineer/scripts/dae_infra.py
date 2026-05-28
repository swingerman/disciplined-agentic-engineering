#!/usr/bin/env python3
"""dae_infra.py — probe, auto-start, and teardown of declared infrastructure.

Implements the runtime side of the `infra:` manifest section, letting DAE
workflows auto-start services (firebase emulators, chromedriver, etc.) instead
of stopping to ask the human.

Usage:
    dae_infra.py status  [--root DIR] [NAME ...]
    dae_infra.py ensure  [--root DIR] NAME [NAME ...]
    dae_infra.py teardown [--root DIR] [NAME ...]

Exit codes:
    0  success (status always 0; ensure 0 if all up; teardown always 0)
    1  ensure: at least one entry failed to start
    3  usage error
"""

import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time

import dae_resolve

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_HTTP_TIMEOUT = 5
DEFAULT_TCP_TIMEOUT = 2
DEFAULT_CMD_TIMEOUT = 5
DEFAULT_READY_TIMEOUT = 60
POLL_INTERVAL = 0.5
MAX_OUTPUT_LINES = 20


# ---------------------------------------------------------------------------
# Probe implementations
# ---------------------------------------------------------------------------

def probe_http(url: str, timeout_s: int = DEFAULT_HTTP_TIMEOUT) -> bool:
    """GET url; return True if 2xx or 3xx."""
    try:
        import urllib.request
        import urllib.error
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return 200 <= resp.status < 400
    except Exception:
        return False


def probe_tcp(host: str, port: int, timeout_s: int = DEFAULT_TCP_TIMEOUT) -> bool:
    """Try to open a TCP connection; True if connects."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(timeout_s)
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def probe_process(pattern: str) -> bool:
    """pgrep -f <pattern>; True if any process matches."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def probe_command(command: str, timeout_s: int = DEFAULT_CMD_TIMEOUT) -> bool:
    """Run shell command; True if exit 0 within timeout."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=timeout_s,
        )
        return result.returncode == 0
    except Exception:
        return False


def make_health_probe(health: dict):
    """Return a zero-arg callable that probes according to the health dict."""
    htype = health.get("type")
    if htype == "http":
        url = health["url"]
        timeout_s = health.get("timeout_s", DEFAULT_HTTP_TIMEOUT)
        return lambda: probe_http(url, timeout_s)
    elif htype == "tcp":
        host = health.get("host", "localhost")
        port = health["port"]
        timeout_s = health.get("timeout_s", DEFAULT_TCP_TIMEOUT)
        return lambda: probe_tcp(host, port, timeout_s)
    elif htype == "process":
        pattern = health["pattern"]
        return lambda: probe_process(pattern)
    elif htype == "command":
        command = health["command"]
        timeout_s = health.get("timeout_s", DEFAULT_CMD_TIMEOUT)
        return lambda: probe_command(command, timeout_s)
    else:
        return lambda: False


# ---------------------------------------------------------------------------
# State files
# ---------------------------------------------------------------------------

def _state_dir(methodology_root: str) -> str:
    return os.path.join(methodology_root, ".engineer", "infra")


def write_state(methodology_root: str, name: str, state: dict) -> None:
    """Write state JSON for a named entry."""
    d = _state_dir(methodology_root)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def read_state(methodology_root: str, name: str):
    """Read state for a named entry; GC stale files; return None if absent/stale."""
    path = os.path.join(_state_dir(methodology_root), name + ".json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        try:
            os.remove(path)
        except OSError:
            pass
        return None
    # Use PGID for liveness if available (shell=True spawns a shell that exits,
    # leaving children in the same process group), else fall back to PID.
    pgid = state.get("pgid")
    pid = state.get("pid")
    alive = False
    if pgid is not None:
        alive = _pgid_running(pgid)
    elif pid is not None:
        alive = _pid_running(pid)
    if not alive:
        try:
            os.remove(path)
        except OSError:
            pass
        return None
    return state


def remove_state(methodology_root: str, name: str) -> None:
    path = os.path.join(_state_dir(methodology_root), name + ".json")
    try:
        os.remove(path)
    except OSError:
        pass


def _pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _pgid_running(pgid: int) -> bool:
    """Return True if any process in the process group is running."""
    try:
        result = subprocess.run(
            ["pgrep", "-g", str(pgid)],
            capture_output=True,
            timeout=3,
        )
        return result.returncode == 0
    except Exception:
        return _pid_running(pgid)


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

def load_entries(methodology_root: str) -> dict:
    """Load and return the infra entries from the manifest with defaults filled in.

    Returns {name: entry_dict} where each entry has health and start filled with
    defaults and a resolved teardown.
    """
    manifest_path = os.path.join(methodology_root, ".engineer", "manifest.yml")
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        raise InfraError(
            "no manifest found at %s — not a DAE-onboarded project, or wrong --root"
            % manifest_path)
    manifest = dae_resolve.read_manifest(text)
    infra_block = manifest.get("infra") or {}
    default_teardown = infra_block.get("default_teardown", "leave-running")

    entries = {}
    for name, entry in infra_block.items():
        if name == "default_teardown":
            continue
        if not isinstance(entry, dict):
            continue
        health = dict(entry.get("health") or {})
        # Fill in health defaults
        if health.get("type") == "http":
            health.setdefault("timeout_s", DEFAULT_HTTP_TIMEOUT)
        elif health.get("type") == "tcp":
            health.setdefault("host", "localhost")
            health.setdefault("timeout_s", DEFAULT_TCP_TIMEOUT)
        elif health.get("type") == "command":
            health.setdefault("timeout_s", DEFAULT_CMD_TIMEOUT)

        start = dict(entry.get("start") or {})
        start.setdefault("background", True)
        start.setdefault("ready_timeout_s", DEFAULT_READY_TIMEOUT)

        teardown = entry.get("teardown") or default_teardown
        entries[name] = {
            "health": health,
            "start": start,
            "teardown": teardown,
        }
    return entries


class InfraError(Exception):
    """Raised when the manifest can't be found or the infra block is malformed."""


# ---------------------------------------------------------------------------
# Background start
# ---------------------------------------------------------------------------

class StartFailure(Exception):
    def __init__(self, diagnosis: str, detail: str, last_output: list,
                 elapsed_s: float, suggested_fix: str = ""):
        self.diagnosis = diagnosis
        self.detail = detail
        self.last_output = last_output
        self.elapsed_s = elapsed_s
        self.suggested_fix = suggested_fix
        super().__init__(detail)


def _diagnose_start(command: str, health: dict) -> str:
    """Pre-start diagnosis: detect command-not-found or port-in-use."""
    first_word = command.split()[0] if command.strip() else ""
    if first_word and shutil.which(first_word) is None:
        return "command-not-found"
    # Check port-in-use before start
    htype = health.get("type")
    if htype in ("tcp", "http"):
        port = health.get("port")
        if not port and htype == "http":
            # Try to extract port from URL
            url = health.get("url", "")
            m = re.search(r":(\d+)", url.split("//")[-1])
            if m:
                port = int(m.group(1))
        host = health.get("host", "localhost")
        if port and probe_tcp(host, int(port), timeout_s=1):
            return "port-in-use"
    return ""


def _suggested_fix(diagnosis: str, command: str) -> str:
    if diagnosis == "command-not-found":
        first_word = command.split()[0] if command.strip() else command
        return "Install '%s' or ensure it is on PATH" % first_word
    elif diagnosis == "port-in-use":
        return "Stop the existing process using this port before starting"
    elif diagnosis == "ready-timeout":
        return "Check the start command and health probe config; increase ready_timeout_s if needed"
    elif diagnosis == "start-exit-nonzero":
        return "Check the start command for errors; review last_output for details"
    return "Check logs for details"


def start_background(command: str, ready_signal, ready_timeout_s: int,
                     health_probe, methodology_root: str) -> dict:
    """Spawn command; wait for ready; return state dict on success.

    Raises StartFailure on timeout or immediate non-zero exit.
    """
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    t0 = time.monotonic()
    output_lines = []

    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        cwd=methodology_root,
    )
    # Make stdout non-blocking so we don't deadlock
    try:
        os.set_blocking(proc.stdout.fileno(), False)
    except (AttributeError, OSError):
        pass  # not available on all platforms; proceed anyway

    ready_re = re.compile(ready_signal) if ready_signal else None
    found_ready = False

    while True:
        elapsed = time.monotonic() - t0

        # Read available stdout
        try:
            chunk = proc.stdout.read(4096)
            if chunk:
                for line in chunk.decode("utf-8", errors="replace").splitlines():
                    output_lines.append(line)
                    if len(output_lines) > MAX_OUTPUT_LINES * 2:
                        output_lines = output_lines[-MAX_OUTPUT_LINES:]
                    if ready_re and ready_re.search(line):
                        found_ready = True
        except (BlockingIOError, OSError):
            pass

        if found_ready:
            break

        # Check if process died
        ret = proc.poll()
        if ret is not None and ret != 0:
            last = output_lines[-MAX_OUTPUT_LINES:]
            raise StartFailure(
                diagnosis="start-exit-nonzero",
                detail="Process exited with code %d after %.1fs" % (ret, elapsed),
                last_output=last,
                elapsed_s=elapsed,
                suggested_fix=_suggested_fix("start-exit-nonzero", command),
            )

        # If no ready_signal, poll health
        if not ready_re:
            try:
                if health_probe():
                    found_ready = True
                    break
            except Exception:
                pass

        if elapsed >= ready_timeout_s:
            # Timeout — kill process group
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGTERM)
            except OSError:
                try:
                    proc.kill()
                except OSError:
                    pass
            last = output_lines[-MAX_OUTPUT_LINES:]
            raise StartFailure(
                diagnosis="ready-timeout",
                detail="Not ready after %.1fs (timeout=%ds)" % (elapsed, ready_timeout_s),
                last_output=last,
                elapsed_s=elapsed,
                suggested_fix=_suggested_fix("ready-timeout", command),
            )

        time.sleep(POLL_INTERVAL)

    # Success
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        pgid = proc.pid

    return {
        "pid": proc.pid,
        "pgid": pgid,
        "started_at": started_at,
        "last_output": output_lines[-MAX_OUTPUT_LINES:],
    }


# ---------------------------------------------------------------------------
# Methodology root resolution
# ---------------------------------------------------------------------------

def _find_root(root_arg=None) -> str:
    if root_arg:
        return os.path.abspath(root_arg)
    start = os.getcwd()
    root, _ = dae_resolve.find_methodology_root(start)
    if root is None:
        sys.stderr.write(
            "error: no .engineer/manifest.yml found walking up from %s\n" % start)
        sys.exit(3)
    return root


# ---------------------------------------------------------------------------
# Status probe
# ---------------------------------------------------------------------------

def _probe_entry(methodology_root: str, name: str, health: dict):
    """Return {status: up|down|unknown, pid: int|None, started_at: str|None}."""
    state = read_state(methodology_root, name)
    probe = make_health_probe(health)
    try:
        up = probe()
    except Exception:
        up = False
    pid = state.get("pid") if state else None
    started_at = state.get("started_at") if state else None
    return {
        "status": "up" if up else "down",
        "pid": pid,
        "started_at": started_at,
    }


# ---------------------------------------------------------------------------
# CLI sub-commands
# ---------------------------------------------------------------------------

def cmd_status(argv):
    """status [--root DIR] [NAME ...]"""
    root_arg, names, _ = _parse_common(argv)
    root = _find_root(root_arg)
    entries = load_entries(root)
    if names:
        selected = {n: entries[n] for n in names if n in entries}
    else:
        selected = entries
    result = {}
    for name, entry in selected.items():
        result[name] = _probe_entry(root, name, entry["health"])
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_ensure(argv):
    """ensure [--root DIR] NAME [NAME ...]"""
    root_arg, names, quiet = _parse_common(argv)
    root = _find_root(root_arg)
    entries = load_entries(root)
    report = []
    all_up = True

    for name in names:
        if name not in entries:
            err = {
                "name": name,
                "status": "start-failed",
                "diagnosis": "unknown",
                "detail": "No infra entry named %r in manifest" % name,
                "last_output": [],
                "elapsed_s": 0.0,
                "suggested_fix": "Add an infra.%s entry to the manifest" % name,
            }
            report.append(err)
            all_up = False
            break

        entry = entries[name]
        health = entry["health"]
        start_cfg = entry["start"]
        probe = make_health_probe(health)

        # Probe current health
        try:
            already_up = probe()
        except Exception:
            already_up = False

        if already_up:
            state = read_state(root, name)
            report.append({
                "name": name,
                "status": "up",
                "pid": state.get("pid") if state else None,
                "started_at": state.get("started_at") if state else None,
            })
            continue

        # Need to start
        command = start_cfg["command"]
        pre_diag = _diagnose_start(command, health)
        if pre_diag in ("command-not-found", "port-in-use"):
            err = {
                "name": name,
                "status": "start-failed",
                "diagnosis": pre_diag,
                "detail": "Pre-start check failed: %s for command %r" % (pre_diag, command),
                "last_output": [],
                "elapsed_s": 0.0,
                "suggested_fix": _suggested_fix(pre_diag, command),
            }
            report.append(err)
            all_up = False
            break

        try:
            state_data = start_background(
                command=command,
                ready_signal=start_cfg.get("ready_signal"),
                ready_timeout_s=start_cfg.get("ready_timeout_s", DEFAULT_READY_TIMEOUT),
                health_probe=probe,
                methodology_root=root,
            )
        except StartFailure as sf:
            err = {
                "name": name,
                "status": "start-failed",
                "diagnosis": sf.diagnosis,
                "detail": sf.detail,
                "last_output": sf.last_output,
                "elapsed_s": sf.elapsed_s,
                "suggested_fix": sf.suggested_fix,
            }
            report.append(err)
            all_up = False
            break

        state = {
            "name": name,
            "pid": state_data["pid"],
            "pgid": state_data["pgid"],
            "command": command,
            "started_at": state_data["started_at"],
            "health": health,
        }
        write_state(root, name, state)
        report.append({
            "name": name,
            "status": "up",
            "pid": state_data["pid"],
            "started_at": state_data["started_at"],
        })

    output = {"entries": report, "all_up": all_up}
    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if all_up else 1


def cmd_teardown(argv):
    """teardown [--root DIR] [NAME ...]"""
    root_arg, names, quiet = _parse_common(argv)
    root = _find_root(root_arg)
    entries = load_entries(root)

    if names:
        to_teardown = names
    else:
        # All entries whose effective teardown is session-end or always
        to_teardown = [
            n for n, e in entries.items()
            if e.get("teardown") in ("session-end", "always")
        ]

    report = []
    for name in to_teardown:
        state = read_state(root, name)
        if state is None:
            report.append({"name": name, "status": "not-running", "error": None})
            continue
        pgid = state.get("pgid")
        pid = state.get("pid")
        error = None
        try:
            if pgid:
                os.killpg(pgid, signal.SIGTERM)
            elif pid:
                os.kill(pid, signal.SIGTERM)
        except OSError as e:
            error = str(e)
        remove_state(root, name)
        report.append({"name": name, "status": "stopped", "error": error})

    json.dump({"entries": report}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


# ---------------------------------------------------------------------------
# Argument parsing helpers
# ---------------------------------------------------------------------------

def _parse_common(argv):
    """Parse [--root DIR] [--quiet] [NAME ...] from argv (already stripped of sub-command).

    Returns (root_arg, names_list, quiet_bool).
    """
    args = list(argv)
    root_arg = None
    quiet = False
    if "--quiet" in args:
        quiet = True
        args.remove("--quiet")
    if "--root" in args:
        idx = args.index("--root")
        if idx + 1 >= len(args):
            sys.stderr.write("error: --root requires a directory argument\n")
            sys.exit(3)
        root_arg = args[idx + 1]
        del args[idx:idx + 2]
    names = args
    return root_arg, names, quiet


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

USAGE = """\
usage:
  dae_infra.py status   [--root DIR] [NAME ...]
  dae_infra.py ensure   [--root DIR] NAME [NAME ...]
  dae_infra.py teardown [--root DIR] [NAME ...]
"""

COMMANDS = {
    "status": cmd_status,
    "ensure": cmd_ensure,
    "teardown": cmd_teardown,
}


def main(argv):
    args = argv[1:]
    if not args or args[0] in ("-h", "--help"):
        sys.stdout.write(USAGE)
        return 0
    sub = args[0]
    if sub not in COMMANDS:
        sys.stderr.write("error: unknown sub-command %r\n%s" % (sub, USAGE))
        return 3
    try:
        return COMMANDS[sub](args[1:])
    except InfraError as e:
        sys.stderr.write("error: %s\n" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
