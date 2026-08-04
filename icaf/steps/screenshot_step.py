"""
icaf/steps/screenshot_step.py

Real-time screenshot step.
Calls terminal.capture() which now uses the VM-safe multi-fallback chain
defined in VisibleTerminal.capture().

No Pillow rendering — every screenshot is a genuine live capture of the
gnome-terminal window at the moment this step runs.
"""

import os
from datetime import datetime

from icaf.core.step import Step
from icaf.utils.logger import logger


class ScreenshotStep(Step):

    def __init__(self, terminal: str):
        super().__init__("Capture real-time terminal screenshot")
        self.terminal = terminal

    # ── Filename ───────────────────────────────────────────────────────────

    def _generate_filename(self, context) -> str:
        testcase  = context.current_testcase
        tc_name   = getattr(testcase, "name", "unknown_tc")
        timestamp = datetime.now().strftime("%H%M%S_%f")
        return f"{tc_name}_{self.terminal}_{timestamp}.png"

    # ── Execute ────────────────────────────────────────────────────────────

    def execute(self, context):
        """
        1. Resolve the output directory from context.evidence
        2. Build full file path
        3. Call terminal.capture(full_path)  — real gnome-terminal screenshot
        4. Attach the saved path to context.current_testcase
        """
        testcase = context.current_testcase
        if testcase is None:
            logger.warning("[ScreenshotStep] No current testcase — skipping")
            return None

        clause   = context.clause
        path_dir = context.evidence.screenshot_path(clause, testcase)
        os.makedirs(path_dir, exist_ok=True)

        filename  = self._generate_filename(context)
        full_path = os.path.join(path_dir, filename)

        terminal = context.terminal_manager.get_terminal(self.terminal)
        if not terminal:
            logger.error(f"[ScreenshotStep] Terminal '{self.terminal}' not found")
            return None

        logger.info(f"[ScreenshotStep] Capturing → {full_path}")

        # Real capture — VisibleTerminal.capture() handles all VM fallbacks
        saved_path = terminal.capture(full_path)

        if saved_path and os.path.exists(saved_path):
            logger.info(f"[ScreenshotStep] ✓ Saved: {saved_path}")
            testcase.add_evidence(screenshot=saved_path)
        else:
            logger.warning("[ScreenshotStep] capture() returned no valid file")

        return saved_path
