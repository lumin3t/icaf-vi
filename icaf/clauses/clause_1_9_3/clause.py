"""
icaf/clauses/clause_1_9_3/clause.py

Clause 1.9.3: Vulnerability Scanning

ONE SSH connection via paramiko (opened first).
The tmux terminal types commands visually but does NOT open its own SSH —
it just echoes what paramiko sends so the tester can see activity.
scrot takes a real screenshot of that tmux window for the report.

Test Case:
TC-1-9-3-001: Conduct credential-based vulnerability scan using
vulnerability assessment/scanning tool against an IP interface of the DUT.
"""

import subprocess
import time

from icaf.core.clause import BaseClause
from icaf.core.testcase import TestCase
from icaf.core.result_recorder import clear_results, get_results, set_terminal_manager
from icaf.core.step_runner import StepRunner
from icaf.steps.screenshot_step import ScreenshotStep
from icaf.steps.clear_terminal_step import ClearTerminalStep
from icaf.utils.logger import logger

from icaf.clauses.clause_1_9_3.testcases.tc_193_001 import run as run_tc001

_TC_MANIFEST = [
    (run_tc001, "TC1", "Conduct Credential-based Vulnerability Scan",
     "Verify DUT generates a credential-based vulnerability scan report using "
     "vulnerability assessment/scanning tool against an IP interface of the DUT"),
]

TMUX_NAME = "ICAF-DUT"
TERMINAL  = "dut"


def _tmux(keys, enter=True):
    """Send keys to tmux terminal."""
    cmd = ["tmux", "send-keys", "-t", TMUX_NAME, keys]
    if enter:
        cmd.append("Enter")
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Clause_1_9_3(BaseClause):
    """
    Clause 1.9.3: Vulnerability Scanning
    
    Ensures the DUT can be scanned for vulnerabilities using
    credential-based scanning tools and generates accessible reports.
    """

    name = "1.9.3 Vulnerability Scanning"

    def __init__(self, context):
        super().__init__(context)
        self._ssh = None

    def run(self) -> list[TestCase]:
        """Execute vulnerability scanning compliance tests."""
        clear_results()

        tm = getattr(self.context, "terminal_manager", None)
        if tm is not None:
            set_terminal_manager(tm)

        # ── Step 1: open ONE paramiko SSH session ─────────────────────────
        self._ssh = self._make_ssh_session()

        # ── Step 2: open gnome-terminal showing a local prompt ────────────
        # The terminal does NOT ssh into the DUT itself — it just shows
        # the commands we type into it via tmux send-keys
        self._open_terminal()

        # ── Step 3: patch ssh.run to also type visually ───────────────────
        self._patch_visual()

        # ── Run each test case ────────────────────────────────────────────
        for runner_fn, tc_id, tc_name, _desc in _TC_MANIFEST:
            logger.info(f"[1.9.3] Running {tc_id}")
            _tmux(f"echo '=== {tc_id}: {tc_name} ==='")
            time.sleep(0.3)

            tc_obj = TestCase(name=tc_id, description=tc_name)
            self.context.current_testcase = tc_obj

            try:
                runner_fn(self._ssh)
            except Exception as exc:
                logger.error(f"[1.9.3] {tc_id} exception: {exc}")
                from icaf.core.result_recorder import record_result, save_evidence
                ev = save_evidence(tc_id, "N/A", str(exc))
                record_result(tc_id, tc_name, _desc,
                              "N/A", str(exc), "No exception",
                              str(exc), "ERROR", [ev])

            self.context.current_testcase = None
            StepRunner([ClearTerminalStep(TERMINAL)]).run(self.context)
            time.sleep(0.4)

        # ── Teardown ──────────────────────────────────────────────────────
        try:
            self._ssh.close()
        except Exception:
            pass

        raw_results = get_results()
        self.context.scan_results = {"vulnerability_scanning": raw_results}
        return self._build_testcase_objects(raw_results)

    # ── Open terminal (local shell — no second SSH) ───────────────────────

    def _open_terminal(self):
        """
        Open a gnome-terminal with a tmux session showing a local shell.
        Commands are typed into it via _patch_visual so the tester sees
        activity — but there is no second SSH connection.
        We show the DUT IP in the prompt so it's clear what's being tested.
        """
        subprocess.run(["tmux", "kill-session", "-t", TMUX_NAME],
                       stderr=subprocess.DEVNULL)
        subprocess.run(["tmux", "new-session", "-d", "-s", TMUX_NAME])

        subprocess.Popen([
            "gnome-terminal",
            f"--title=ICAF — Alpine DUT ({self.context.ssh_ip})",
            "--", "tmux", "attach", "-t", TMUX_NAME,
        ])
        time.sleep(2.0)

        # Show a clear header so it's obvious what this terminal is for
        _tmux(f"echo '=== ICAF Clause 1.9.3 — DUT: {self.context.ssh_ip} ==='")
        _tmux("echo '=== Vulnerability Scanning via SSH (paramiko) ==='")
        _tmux("echo ''")
        time.sleep(0.5)
        logger.info("[1.9.3] Terminal window opened")

    # ── Patch: type every ssh.run command visually into tmux ──────────────

    def _patch_visual(self):
        """Patch SSH run method to display commands and output in tmux."""
        orig = self._ssh.run

        def visual_run(command, sudo=False, input_text=None, timeout=30):
            # Show command being run
            _tmux(f"echo '$ {command}'")
            time.sleep(0.2)
            # Execute via paramiko and show output
            result = orig(command, sudo=sudo, input_text=input_text, timeout=timeout)
            out, err, code = result
            combined = (out + err).strip()
            if combined:
                for line in combined.splitlines()[:20]:
                    _tmux(f"echo '  {line}'")
            _tmux(f"echo '  [exit: {code}]'")
            time.sleep(0.3)
            return result

        self._ssh.run = visual_run

    # ── Paramiko SSH ──────────────────────────────────────────────────────

    def _make_ssh_session(self):
        """Create and establish paramiko SSH session."""
        import paramiko as _pm
        client = _pm.SSHClient()
        client.set_missing_host_key_policy(_pm.AutoAddPolicy())
        client.connect(
            hostname=self.context.ssh_ip, port=22,
            username=self.context.ssh_user,
            password=self.context.ssh_password, timeout=30,
        )
        logger.info(f"[1.9.3] SSH connected to {self.context.ssh_ip}")
        return _SSHWrapper(client)

    @staticmethod
    def _build_testcase_objects(raw_results):
        """Build TestCase objects from raw result data."""
        tc_objects = []
        for r in raw_results:
            tc = TestCase(name=r["tc_id"], description=r.get("tc_name", ""))
            screenshot = next(
                (f for f in r.get("evidence_files", []) if f.endswith(".png")),
                None,
            )
            tc.add_evidence(command=r.get("input_cmd"),
                            output=r.get("output"),
                            screenshot=screenshot)
            tc.status = {"PASS": "PASS", "FAIL": "FAIL", "ERROR": "FAIL"}.get(
                r.get("verdict", "FAIL"), "FAIL"
            )
            tc.raw_result = r
            tc_objects.append(tc)
        return tc_objects


class _SSHWrapper:
    """Wrapper around paramiko SSH client for command execution."""

    def __init__(self, client):
        self._client = client

    def run(self, command, sudo=False, input_text=None, timeout=30):
        """
        Execute command via SSH and return output.
        
        Args:
            command: Shell command to execute
            sudo: Whether to use sudo (not typically needed for vulnerability scanning)
            input_text: Text to send to stdin if needed
            timeout: Command execution timeout in seconds
            
        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        use_pty = (
            "passwd" in command
            and "cat" not in command
            and "grep" not in command
        )
        stdin, stdout, stderr = self._client.exec_command(
            command, timeout=timeout, get_pty=use_pty
        )
        if input_text:
            try:
                stdin.write(input_text)
                stdin.flush()
                stdin.channel.shutdown_write()
            except Exception:
                pass
        out  = stdout.read().decode("utf-8", errors="replace")
        err  = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        return out, err, code

    def close(self):
        """Close SSH connection."""
        try:
            self._client.close()
        except Exception:
            pass
