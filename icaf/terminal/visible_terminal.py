"""
icaf/terminal/visible_terminal.py
Commands now EXECUTE in the visible terminal AND mirror to the renderer.
"""

import subprocess
import time
from icaf.utils.logger import logger
from icaf.terminal.base_terminal import BaseTerminal
from icaf.terminal.terminal_renderer import terminal_renderer   # import singleton


class VisibleTerminal(BaseTerminal):
    # Alpine prompt shown in renderer
    PROMPT = "root@alpine:~#"

    # Last-resort fallback values only - used if no credentials are passed in.
    # These exist so the terminal doesn't crash if something upstream forgets
    # to supply real values, but should not be relied on.
    _FALLBACK_IP = "192.168.56.101"
    _FALLBACK_USER = "root"
    _FALLBACK_PASSWORD = "Root@Alpine1"

    def __init__(self, name, ssh_ip=None, ssh_user=None, ssh_password=None):
        super().__init__(name)
        self.session = f"TCAF-{name}"

        self.ssh_ip = ssh_ip or self._FALLBACK_IP
        self.ssh_user = ssh_user or self._FALLBACK_USER
        self.ssh_password = ssh_password or self._FALLBACK_PASSWORD

        if not ssh_ip or not ssh_user or not ssh_password:
            logger.warning(
                "VisibleTerminal(%s): missing ssh_ip/ssh_user/ssh_password - "
                "falling back to hardcoded defaults (ip=%s, user=%s). "
                "Pass real credentials via TerminalManager.create_terminal().",
                name, self.ssh_ip, self.ssh_user,
            )

        self._open_session()

    def _open_session(self):
        """Create the tmux session + gnome-terminal window and log in."""
        logger.info("Opening visible Alpine terminal...")

        # Kill old session
        subprocess.run(
            ["tmux", "kill-session", "-t", self.session],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
        )
        # Create tmux session
        subprocess.run(["tmux", "new-session", "-d", "-s", self.session])
        # Open visible terminal
        subprocess.Popen([
            "gnome-terminal", "--title", "TCAF Live — Alpine DUT",
            "--geometry", "150x60",
            "--", "tmux", "attach-session", "-t", self.session
        ])
        time.sleep(3.5)
        self._auto_login()

    def _session_alive(self) -> bool:
        """Check whether the tmux session for this terminal still exists."""
        result = subprocess.run(
            ["tmux", "has-session", "-t", self.session],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return result.returncode == 0

    def _ensure_session_alive(self):
        """
        If the tmux session died (e.g. its shell process exited), recreate
        it and log back in, instead of silently sending commands into a
        session that no longer exists.
        """
        if not self._session_alive():
            logger.warning(
                "[VisibleTerminal] Session '%s' is dead — recreating and "
                "logging back in.",
                self.session,
            )
            self._open_session()

    def _auto_login(self):
        logger.info("Logging into Alpine...")

        ssh_cmd = f"ssh -o StrictHostKeyChecking=no {self.ssh_user}@{self.ssh_ip}"

        subprocess.run([
            "tmux", "send-keys", "-t", self.session,
            "ssh -o StrictHostKeyChecking=no root@192.168.56.102", "Enter"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(4)

        terminal_renderer.add_raw_line(
            "ssh -o StrictHostKeyChecking=no root@192.168.56.102", color="dim"
        )

        subprocess.run([
            "tmux", "send-keys", "-t", self.session,
            self.ssh_password, "Enter"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)

        terminal_renderer.add_raw_line("(login)", color="dim")

    def run(self, command, screenshot_path=None):
        """Execute in visible terminal AND mirror to renderer."""
        # Self-heal: if the tmux session died since the last command
        # (e.g. an over-eager "exit" killed the underlying shell), recreate
        # it and log back in before trying to send anything else.
        self._ensure_session_alive()

        logger.info(f"[VisibleTerminal] Executing: {command}")

        # 1. Mirror the command to the renderer immediately
        terminal_renderer.add_command_with_prompt(self.PROMPT, command)

        # 2. Send to tmux
        try:
            subprocess.run([
                "tmux", "send-keys", "-t", self.session, command, "Enter"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"[VisibleTerminal] send-keys failed: {e}")
            return

        # 3. Wait for output
        time.sleep(3.0)

        # 4. Capture pane output and push to renderer
        output = self._capture_pane_output()
        if output:
            terminal_renderer.add_output(output)
            logger.info(f"[VisibleTerminal] Captured {len(output.splitlines())} output lines")
        else:
            logger.warning("[VisibleTerminal] No output captured from pane")

        # 5. Re-render the PNG
        if screenshot_path:
            terminal_renderer.render(screenshot_path)

    def _capture_pane_output(self) -> str:
        """
        Capture recent lines from the tmux pane.
        Returns only the *new* lines since last prompt (heuristic: last 20 lines,
        strip the prompt line itself and any blank trailing lines).
        """
        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", self.session, "-p", "-S", "-20"],
                capture_output=True, text=True, timeout=5
            )
            raw = result.stdout

            # Split into lines, strip trailing blank lines
            lines = raw.splitlines()
            while lines and not lines[-1].strip():
                lines.pop()

            # Drop the last line if it's just the prompt (waiting for input)
            if lines and lines[-1].strip().startswith(self.PROMPT.split(":")[0]):
                lines.pop()

            # Drop the command line itself (renderer already added it)
            if lines and lines[-1].strip() == lines[-1].strip():
                # crude: skip lines that look like prompts
                lines = [
                    l for l in lines
                    if not l.strip().startswith("root@") or "#" not in l
                ]

            return "\n".join(lines[-15:])   # keep last 15 output lines
        except Exception as e:
            logger.error(f"[VisibleTerminal] pane capture failed: {e}")
            return ""

    def capture_output(self) -> str:
        """
        Return the current tmux pane content as a string.

        Used by TerminalManager.capture_output() to poll the terminal until
        the output stabilises (stops changing between successive reads) -
        this is how CommandStep knows a command has finished producing output.
        """
        if not self._session_alive():
            logger.warning(
                "[VisibleTerminal] capture_output: session '%s' is dead",
                self.session,
            )
            return ""

        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", self.session, "-p", "-S", "-50"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout
        except Exception as e:
            logger.error(f"[VisibleTerminal] capture_output failed: {e}")
            return ""

    def capture(self, screenshot_path):
        """Capture the visible window via scrot AND render the Pillow terminal."""
        # Always re-render the Pillow screenshot
        terminal_renderer.render(screenshot_path)
        # Optionally also grab the real screen
        try:
            subprocess.run(["scrot", "-u", "-o", screenshot_path + ".real.png"], timeout=5)
        except Exception:
            pass
        return screenshot_path