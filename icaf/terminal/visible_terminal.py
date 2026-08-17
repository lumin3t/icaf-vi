"""
icaf/terminal/visible_terminal.py
Commands now EXECUTE in the visible terminal AND mirror to the renderer.
"""

import subprocess
import time
from icaf.utils.logger import logger
from icaf.terminal.base_terminal import BaseTerminal
from icaf.terminal.terminal_renderer import terminal_renderer   # ← import singleton


class VisibleTerminal(BaseTerminal):
    # Alpine prompt shown in renderer
    PROMPT = "root@alpine:~#"

    def __init__(self, name):
        super().__init__(name)
        self.session = f"TCAF-{name}"
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

    def _auto_login(self):
        logger.info("Logging into Alpine...")
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
            "Root@Alpine1", "Enter"        # ← CHANGE password here
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)

        terminal_renderer.add_raw_line("(login)", color="dim")

    def run(self, command, screenshot_path=None):
        """Execute in visible terminal AND mirror to renderer."""
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