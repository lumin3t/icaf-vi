from icaf.core.step import Step
from icaf.utils.logger import logger


class ClearTerminalStep(Step):

    def __init__(self, terminal):

        super().__init__("Clear terminal")

        self.terminal = terminal

    def execute(self, context):

        tm = context.terminal_manager

        logger.info(f"Clearing terminal {self.terminal}")

        tm.run(self.terminal, "clear")