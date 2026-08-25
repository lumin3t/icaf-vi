"""
steps/session_reset_step.py
──────────────────────────────────────────────────────────────────────────────
Cleanly tears down the active session on a terminal at the end of a test case,
then pauses for a configurable inter-test-case cooldown.

Improvements over original
───────────────────────────
• Sends "exit" and then waits to confirm the SSH prompt is actually gone
  (looks for shell prompt characters that would indicate a live session is
  still open) before declaring the session closed.
• Sends "exit" up to max_exit_attempts times to handle nested sessions
  (e.g., DUT shell → system shell → bare terminal).
• Calls `clear` after disconnect so the next TC starts with a clean terminal.
• Accepts a post_reset_delay parameter (default 3 s) used as a between-TC
  breathing gap.  The caller (TC code) can override this per-TC.
• Logs the final terminal state so failures are easy to diagnose.
• Empty/unreadable pane capture is treated as "unknown state" and retried —
  NOT as evidence of disconnection. A transient capture failure (pane not
  yet settled) must never be mistaken for a real disconnect, since that
  leaves the next test case typing commands into a still-live session.
"""

import time

from icaf.core.step import Step
from icaf.core.step_runner import StepRunner
from icaf.steps.clear_terminal_step import ClearTerminalStep
from icaf.steps.ensure_ssh_disconnected_step import EnsureSSHDisconnectedStep
from icaf.utils.logger import logger


# Prompts that indicate a live SSH/shell session is still active
_LIVE_SESSION_INDICATORS = ["#", "$", ">", "rkscli", "apollo", "watchdog"]

# Prompts that confirm we're back at the bare terminal (not in a session)
_DISCONNECTED_INDICATORS = [
    "connection closed",
    "disconnected",
    "logout",
    "not connected",
]

# How many times to retry a capture that came back empty before giving up
# and falling through to the Ctrl+C escape hatch anyway.
_MAX_EMPTY_CAPTURE_RETRIES = 3


class SessionResetStep(Step):
    """
    Disconnect any active SSH/shell session on the given terminal and
    perform a post-test-case cooldown.

    Parameters
    ----------
    terminal : str
        Terminal name as registered with the TerminalManager.
    post_reset_delay : float
        Seconds to wait after cleanup completes (inter-TC gap).  Default 3 s.
    max_exit_attempts : int
        How many times to send "exit" to unwind nested sessions.  Default 3.
    """

    def __init__(
        self,
        terminal: str,
        post_reset_delay: float = 3.0,
        max_exit_attempts: int = 1,
    ):
        super().__init__("Reset session")
        self.terminal         = terminal
        self.post_reset_delay = post_reset_delay
        self.max_exit_attempts = max_exit_attempts

    def execute(self, context) -> None:
        tm = context.terminal_manager

        logger.info(
            "SessionReset: tearing down session on terminal '%s'",
            self.terminal,
        )

        # ── Brief settle so the current command finishes output ───────────
        time.sleep(1.5)

        # ── Send "exit" up to max_exit_attempts times ─────────────────────
        # Each exit unwinds one shell layer (DUT CLI → bash → bare terminal).
        for attempt in range(1, self.max_exit_attempts + 1):
            tm.run(self.terminal, "exit")
            time.sleep(2.0)

            # Give a genuinely empty pane capture a couple of extra chances
            # before treating it as meaningful — it usually just means the
            # tmux pane hadn't settled yet, not that the session is gone.
            output = ""
            for capture_try in range(_MAX_EMPTY_CAPTURE_RETRIES):
                output = tm.capture_output(self.terminal)
                if output.strip():
                    break
                logger.debug(
                    "SessionReset: empty capture on attempt %d (try %d/%d) — "
                    "retrying capture before drawing any conclusion",
                    attempt, capture_try + 1, _MAX_EMPTY_CAPTURE_RETRIES,
                )
                time.sleep(1.0)

            if not output.strip():
                # We genuinely could not read the pane after several tries.
                # Do NOT assume disconnected — that's an unverified guess
                # that leaves the next TC talking to an unknown session
                # state. Just move on to the next exit attempt.
                logger.warning(
                    "SessionReset: could not capture any output after %d exit(s) "
                    "— terminal state unknown, retrying exit instead of "
                    "assuming disconnected",
                    attempt,
                )
                continue

            output = output.lower()

            # If we see a disconnection indicator, we're done
            if any(ind in output for ind in _DISCONNECTED_INDICATORS):
                logger.info(
                    "SessionReset: disconnection confirmed after %d exit(s)",
                    attempt,
                )
                break

            # If no live-session prompt is visible, also consider us done —
            # this branch is now only reached with REAL (non-empty) output.
            if not any(ind in output for ind in _LIVE_SESSION_INDICATORS):
                logger.info(
                    "SessionReset: no live-session prompt detected after "
                    "%d exit(s) — assuming disconnected",
                    attempt,
                )
                break

            logger.debug(
                "SessionReset: still connected after %d exit(s) — retrying",
                attempt,
            )
        else:
            # Exhausted attempts — force Ctrl+C then exit as a last resort
            logger.warning(
                "SessionReset: could not cleanly disconnect after %d attempts — "
                "sending Ctrl+C + exit",
                self.max_exit_attempts,
            )
            tm.run(self.terminal, "\x03")   # Ctrl+C
            time.sleep(0.5)
            tm.run(self.terminal, "exit")
            time.sleep(1.0)

        # ── Clear the terminal buffer ─────────────────────────────────────
        try:
            StepRunner([ClearTerminalStep(self.terminal)]).run(context)
        except Exception as exc:
            logger.warning(
                "SessionReset: ClearTerminalStep failed (%s) — continuing",
                exc,
            )

        # ── Inter-test-case cooldown ──────────────────────────────────────
        logger.info(
            "SessionReset: post-reset cooldown %.1f s", self.post_reset_delay
        )
        time.sleep(self.post_reset_delay)

        logger.info(
            "SessionReset: terminal '%s' is ready for the next test case",
            self.terminal,
        )