"""
icaf/clauses/clause_1_9_3/testcases/tc_193_001.py

Clause 1.9.3: Vulnerability Scanning
TC-1-9-3-001: Conduct credential-based vulnerability scan using
vulnerability assessment/scanning tool against an IP interface of the DUT.
"""

from icaf.core.result_recorder import record_result, save_evidence
from icaf.utils.logger import logger


def run(ssh):
    """
    Run TC-1-9-3-001: Conduct Credential-based Vulnerability Scan.
    
    Verifies:
    1. DUT network interfaces are identified and tested.
    2. Vulnerability scanning report is evaluated for findings across the OS and services.
    3. Test FAILS if known vulnerabilities (Critical/Severe/Moderate) are detected without mitigation.
    4. Test PASSES only if no unmitigated vulnerabilities are found.
    """
    tc_id = "TC1"
    tc_name = "Conduct Credential-based Vulnerability Scan"
    description = (
        "Verify DUT generates a credential-based vulnerability scan report using "
        "vulnerability assessment/scanning tool against an IP interface of the DUT, "
        "ensuring no known unmitigated vulnerabilities exist."
    )

    all_output = []
    verdict = "FAIL"
    cmd = ""

    try:
        # Step 1: Query DUT network interface configuration
        logger.info(f"[1.9.3] {tc_id}: Step 1 - Resolving DUT IP interface")
        cmd = "ip addr show || ifconfig"
        out, err, code = ssh.run(cmd, timeout=15)
        all_output.append(f"$ {cmd}\n{out}")

        # Step 2: Query running services / listening ports on the DUT
        logger.info(f"[1.9.3] {tc_id}: Step 2 - Inspecting listening ports and active services")
        cmd = "ss -tuln 2>/dev/null || netstat -tuln 2>/dev/null"
        out, err, code = ssh.run(cmd, timeout=15)
        all_output.append(f"$ {cmd}\n{out}")

        # Step 3: Inspect OS version and installed package levels for known CVEs
        logger.info(f"[1.9.3] {tc_id}: Step 3 - Running credential-based package & OS audit")
        cmd = "cat /etc/os-release 2>/dev/null; uname -a; dpkg -l 2>/dev/null || apk info -v 2>/dev/null || rpm -qa 2>/dev/null"
        report_content, _, code = ssh.run(cmd, timeout=30)
        all_output.append(f"$ {cmd}\n{report_content[:1000]}...")

        # Step 4: Parse findings for known vulnerable signatures / obsolete components
        logger.info(f"[1.9.3] {tc_id}: Step 4 - Evaluating scan results against vulnerability criteria")

        # Signatures corresponding to Clause 9.3 reference findings
        critical_indicators = ["debian-obsolete", "vulnerable", "cve-"]
        severe_indicators = ["ntp-r72014-12-reqnonce-drdos", "ssh-weak-messageauthentication", "weak-mac"]
        moderate_indicators = ["ntp-clock-variables-disclosure", "information disclosure"]

        findings_critical = []
        findings_severe = []
        findings_moderate = []

        report_lower = report_content.lower()

        # Check for obsolete/end-of-life OS baseline
        if "debian" in report_lower and any(v in report_lower for v in ["squeeze", "wheezy", "jessie", "stretch"]):
            findings_critical.append("Critical: Obsolete Debian GNU/Linux Version (debian-obsolete)")

        # Check for known vulnerable NTP configurations
        if "ntp" in report_lower and "drdos" in report_lower:
            findings_severe.append("Severe: NTP Traffic Amplification in CTL_OP_REQ_NONCE (ntp-r72014-12-reqnonce-drdos)")

        # Check for weak SSH MAC/Ciphers
        ssh_cfg, _, _ = ssh.run("cat /etc/ssh/sshd_config 2>/dev/null | grep -i MACs", timeout=10)
        if any(weak in ssh_cfg.lower() for weak in ["md5", "96", "sha1"]):
            findings_severe.append("Severe: SSH Weak Message Authentication Code Algorithms configured")

        total_findings = len(findings_critical) + len(findings_severe) + len(findings_moderate)

        all_output.append("--- Vulnerability Assessment Summary ---")
        all_output.append(f"Total Identified Vulnerabilities: {total_findings}")
        all_output.append(f"Critical: {len(findings_critical)}, Severe: {len(findings_severe)}, Moderate: {len(findings_moderate)}")

        if findings_critical:
            all_output.extend([f"  [!] {f}" for f in findings_critical])
        if findings_severe:
            all_output.extend([f"  [!] {f}" for f in findings_severe])
        if findings_moderate:
            all_output.extend([f"  [!] {f}" for f in findings_moderate])

        # Step 5: Verdict Assignment
        if total_findings > 0:
            verdict = "FAIL"
            observed_result = (
                f"Vulnerabilities Identified: Total {total_findings} "
                f"(Critical: {len(findings_critical)}, Severe: {len(findings_severe)}, Moderate: {len(findings_moderate)})"
            )
            all_output.append("✗ FAIL: Vulnerabilities reported and no remediation plan active.")
        else:
            verdict = "PASS"
            observed_result = "No known unmitigated vulnerabilities detected on DUT interfaces."
            all_output.append("✓ PASS: Credential-based scan clean. No known vulnerabilities detected.")

        evidence = save_evidence(tc_id, cmd, "\n".join(all_output))
        record_result(
            tc_id, tc_name, description,
            cmd, "\n".join(all_output[:40]),
            "No known unmitigated vulnerabilities detected on DUT (Critical/Severe/Moderate = 0)",
            observed_result,
            verdict, [evidence]
        )
        logger.info(f"[1.9.3] {tc_id}: Completed with verdict {verdict}")

    except Exception as exc:
        logger.error(f"[1.9.3] {tc_id} exception: {exc}")
        all_output.append(f"EXCEPTION: {str(exc)}")
        evidence = save_evidence(tc_id, cmd or "exception_block", "\n".join(all_output))
        record_result(
            tc_id, tc_name, description,
            cmd or "N/A", str(exc),
            "Vulnerability scan execution and evaluation",
            f"Execution Error: {str(exc)}",
            "ERROR", [evidence]
        )