"""
icaf/clauses/clause_1_2_1/clause.py

Clause 1.2.1: User Authentication

Orchestrator for authentication testing across multiple protocols:
- SSH (TC4-TC6)
- SFTP (TC7-TC9)
- SCP (TC10-TC12)
- Console (TC1-TC3) - deferred, marked NOT_APPLICABLE

Architecture:
1. Setup: Create test user on DUT via authenticated SSH
2. Execute individual test cases (TC4-TC12)
3. Capture results and evidence
4. Cleanup: Remove test user from DUT
"""

import subprocess
import time
import os
import datetime
import importlib

from icaf.core.clause import BaseClause
from icaf.core.testcase import TestCase
from icaf.core.result_recorder import clear_results, get_results, set_terminal_manager
from icaf.core.step_runner import StepRunner
from icaf.steps.screenshot_step import ScreenshotStep
from icaf.steps.clear_terminal_step import ClearTerminalStep
from icaf.utils.logger import logger
from icaf.clauses.clause_1_2_1.testcases.tc_console_not_applicable import (
    run_not_applicable,
)

try:
    from icaf.core.terminal_renderer import terminal_renderer
    HAS_TERMINAL_RENDERER = True
except ImportError:
    HAS_TERMINAL_RENDERER = False
    terminal_renderer = None


# Test case discovery - SSH, SFTP, SCP tests
TEST_CASES = [
    "tc_4_ssh_no_auth",
    "tc_5_ssh_correct_auth",
    "tc_6_ssh_incorrect_auth",
    "tc_7_sftp_no_auth",
    "tc_8_sftp_correct_auth",
    "tc_9_sftp_incorrect_auth",
    "tc_10_scp_no_auth",
    "tc_11_scp_correct_auth",
    "tc_12_scp_incorrect_auth",
    # Console tests deferred - not yet implemented
]

CONSOLE_TESTS = [
    ("TC1", "Console - No Authentication"),
    ("TC2", "Console - Correct Authentication"),
    ("TC3", "Console - Incorrect Authentication"),
]

TEST_USER = "testuser"
TEST_PASSWORD = "TestPass123"


class Clause_1_2_1(BaseClause):
    """
    Clause 1.2.1: User Authentication
    
    Validates authentication enforcement across SSH, SFTP, and SCP protocols.
    Each test case makes fresh connection attempts to verify authentication behavior.
    """

    name = "1.2.1 User Authentication"

    def __init__(self, context):
        super().__init__(context)
        self.ssh_session = None
        self.test_user_created = False

    def run(self) -> list[TestCase]:
        """
        Execute user authentication test suite.
        
        Returns:
            list: TestCase objects with results
        """
        clear_results()

        tm = getattr(self.context, "terminal_manager", None)
        if tm is not None:
            set_terminal_manager(tm)

        logger.info("[1.2.1] Starting User Authentication Test Suite")

        try:
            # Step 1: Establish baseline SSH session for setup
            self._setup_ssh_session()

            # Step 2: Create test user
            if not self._create_test_user():
                logger.error("[1.2.1] Test user creation failed - cannot proceed")
                # Record setup failure and return
                return self._build_failed_result("Test user creation failed")

            self.test_user_created = True

            # Step 3: Record the deferred console test cases, then execute
            # the implemented SSH, SFTP, and SCP cases.
            self._record_console_tests()
            self._execute_test_cases()

            # Step 4: Cleanup test user
            self._cleanup_test_user()

        except Exception as e:
            logger.error(f"[1.2.1] Clause execution error: {e}")
            if self.test_user_created:
                self._cleanup_test_user()

        finally:
            # Close baseline SSH session
            if self.ssh_session:
                try:
                    self.ssh_session.close()
                except:
                    pass

        # Collect and return results
        raw_results = get_results()
        self.context.scan_results = {"user_authentication": raw_results}
        return self._build_testcase_objects(raw_results)

    def _setup_ssh_session(self):
        """Establish baseline SSH connection for setup/cleanup."""
        try:
            import paramiko
            self.ssh_session = paramiko.SSHClient()
            self.ssh_session.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_session.connect(
                hostname=self.context.ssh_ip,
                port=22,
                username=self.context.ssh_user,
                password=self.context.ssh_password,
                timeout=30,
            )
            logger.info(f"[1.2.1] Baseline SSH session established to {self.context.ssh_ip}")
        except Exception as e:
            logger.error(f"[1.2.1] Failed to establish baseline SSH: {e}")
            raise

    def _create_test_user(self) -> bool:
        """
        Create temporary test user on DUT.
        
        Returns:
            bool: True if successful, False if creation failed
        """
        if not self.ssh_session:
            logger.error("[1.2.1] No SSH session available for test user creation")
            return False

        try:
            logger.info(f"[1.2.1] Creating test user: {TEST_USER}")

            # Check if user already exists
            stdin, stdout, stderr = self.ssh_session.exec_command(f"id {TEST_USER} 2>/dev/null")
            exit_code = stdout.channel.recv_exit_status()

            if exit_code == 0:
                logger.info(f"[1.2.1] Test user {TEST_USER} already exists")
                return True

            # Create new user
            stdin, stdout, stderr = self.ssh_session.exec_command(
                f"adduser -D {TEST_USER} 2>&1"
            )
            exit_code = stdout.channel.recv_exit_status()

            if exit_code != 0:
                error_output = stderr.read().decode('utf-8', errors='replace').strip()
                logger.error(f"[1.2.1] adduser failed: {error_output}")
                return False

            logger.info(f"[1.2.1] Test user {TEST_USER} created")

            # Set password
            stdin, stdout, stderr = self.ssh_session.exec_command(
                f"echo '{TEST_USER}:{TEST_PASSWORD}' | chpasswd 2>&1"
            )
            exit_code = stdout.channel.recv_exit_status()

            if exit_code != 0:
                error_output = stderr.read().decode('utf-8', errors='replace').strip()
                logger.error(f"[1.2.1] chpasswd failed: {error_output}")
                return False

            logger.info(f"[1.2.1] Password set for {TEST_USER}")
            return True

        except Exception as e:
            logger.error(f"[1.2.1] Test user creation exception: {e}")
            return False

    def _execute_test_cases(self):
        """Discover and execute individual test case modules."""
        testcases_dir = os.path.dirname(__file__)
        testcases_path = os.path.join(testcases_dir, "testcases")

        for tc_module_name in TEST_CASES:
            try:
                logger.info(f"[1.2.1] Executing {tc_module_name}")

                # Dynamically import test case module
                spec = importlib.util.spec_from_file_location(
                    tc_module_name,
                    os.path.join(testcases_path, f"{tc_module_name}.py")
                )
                module = importlib.util.module_from_spec(spec)

                # Update context with test credentials for this test
                test_context = self.context
                test_context.test_user = TEST_USER
                test_context.test_password = TEST_PASSWORD

                spec.loader.exec_module(module)

                # Execute test case
                module.run(test_context)

                time.sleep(0.5)

            except Exception as e:
                logger.error(f"[1.2.1] Error executing {tc_module_name}: {e}")

    def _record_console_tests(self):
        """Record deferred console cases as NOT_APPLICABLE results."""
        for tc_id, tc_name in CONSOLE_TESTS:
            run_not_applicable(self.context, tc_id, tc_name)

    def _cleanup_test_user(self):
        """Remove test user from DUT."""
        if not self.ssh_session:
            logger.warning("[1.2.1] No SSH session for cleanup")
            return

        try:
            logger.info(f"[1.2.1] Cleaning up test user: {TEST_USER}")

            stdin, stdout, stderr = self.ssh_session.exec_command(
                f"deluser {TEST_USER} 2>&1"
            )
            exit_code = stdout.channel.recv_exit_status()

            if exit_code != 0:
                error_output = stderr.read().decode('utf-8', errors='replace').strip()
                logger.warning(f"[1.2.1] deluser exit code {exit_code}: {error_output}")
            else:
                logger.info(f"[1.2.1] Test user {TEST_USER} removed")

        except Exception as e:
            logger.error(f"[1.2.1] Cleanup exception: {e}")

    def _build_failed_result(self, error_message: str) -> list:
        """Build a failed result when setup fails."""
        from icaf.core.result_recorder import record_result, save_evidence

        evidence = save_evidence("SETUP", "setup_failure", error_message)
        record_result(
            tc_id="SETUP",
            tc_name="Test Setup",
            description="Test environment setup",
            input_cmd="setup",
            output=error_message,
            expected="Test user created successfully",
            actual=error_message,
            verdict="ERROR",
            evidence_files=[evidence]
        )

        raw_results = get_results()
        return self._build_testcase_objects(raw_results)

    @staticmethod
    def _build_testcase_objects(raw_results):
        """Build TestCase objects from raw result data."""
        tc_objects = []
        for r in raw_results:
            tc = TestCase(name=r.get("tc_id", ""), description=r.get("tc_name", ""))
            screenshot = next(
                (f for f in r.get("evidence_files", []) if f.endswith(".png")),
                None,
            )
            tc.add_evidence(
                command=r.get("input_cmd"),
                output=r.get("output"),
                screenshot=screenshot
            )
            tc.status = {
                "PASS": "PASS",
                "FAIL": "FAIL",
                "ERROR": "ERROR",
                "NOT_APPLICABLE": "NOT_RUN"
            }.get(r.get("verdict", "FAIL"), "FAIL")
            tc.raw_result = r
            tc_objects.append(tc)
        return tc_objects
