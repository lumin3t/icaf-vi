"""
icaf/clauses/clause_1_2_1/testcases/tc_1_console_no_auth.py
icaf/clauses/clause_1_2_1/testcases/tc_2_console_correct_auth.py
icaf/clauses/clause_1_2_1/testcases/tc_3_console_incorrect_auth.py

Console Authentication Tests - NOT_APPLICABLE

These tests are deferred pending definition of actual console access mechanism.

The ICAF framework currently provides:
- VisibleTerminal for tmux/SSH sessions
- TerminalManager for SSH connections
- No real physical/serial console interface

To implement real console authentication testing, the following is required:
1. Definition of DUT console interface (serial, USB, telnet service, etc.)
2. Implementation of console adapter within vendor adapter framework
3. Console access mechanism in TerminalManager or VisibleTerminal

Until these are available, console authentication testing cannot be performed.
"""

from icaf.core.result_recorder import record_result, save_evidence
from icaf.utils.logger import logger


def run_not_applicable(context, tc_id, tc_name):
    """
    Mark console test as NOT_APPLICABLE due to missing console interface.
    
    Args:
        context: RuntimeContext
        tc_id: Test case ID (TC1, TC2, or TC3)
        tc_name: Test case name
    """
    description = "Console authentication test - deferred pending console interface definition"
    expected = "Console interface available in ICAF framework"
    actual = "Console interface not available"
    verdict = "NOT_APPLICABLE"
    
    output = [
        "Console authentication testing requires:",
        "1. Physical/serial console interface definition",
        "2. Console adapter implementation in vendor adapters",
        "3. Console access mechanism in TerminalManager",
        "",
        "Currently available:",
        "- SSH/SFTP/SCP via VisibleTerminal (implemented)",
        "- Serial/physical console (NOT implemented)",
        "",
        "This test is deferred until console support is added.",
    ]
    
    evidence = save_evidence(tc_id, "console_not_applicable", "\n".join(output))
    record_result(
        tc_id=tc_id,
        tc_name=tc_name,
        description=description,
        input_cmd="console login (not applicable)",
        output="\n".join(output),
        expected=expected,
        actual_status=actual,
        verdict=verdict,
        evidence_files=[evidence]
    )
    
    logger.info(f"[1.2.1] {tc_id}: NOT_APPLICABLE - console interface not available")


def run(context):
    """This function should not be called directly for console tests."""
    # Console tests are deferred
    pass