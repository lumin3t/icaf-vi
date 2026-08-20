"""
icaf/reporting/clause_reports/clause_1_9_3_report.py
─────────────────────────────────────────────────────────────────────────────
Report generator for ITSAR 1.9.3 — Vulnerability Scanning Compliance.

Report FORMAT and APPEARANCE  → icaf's helpers / build_doc_with_header_footer
Report CONTENT (test data)    → vulnerability scan test results (raw dicts)

The raw_results list comes from  context.scan_results["vulnerability_scanning"]
which is populated by Clause_1_9_3.run().
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import datetime
import subprocess

from icaf.reporting.helpers import (
    PURPLE, LIGHT_PURPLE, DARK_GREY, MID_GREY,
    TABLE_HEADER_BG, TABLE_ALT_BG, PASS_GREEN, FAIL_RED, WHITE,
    NOT_RUN_COLOR, NOT_RUN_BG,
    HEX_PURPLE, HEX_PASS_GREEN, HEX_FAIL_RED,
    ERROR_ORANGE,
    _style_cell, _para_in_cell, _set_table_width, _set_col_widths,
    section_heading, sub_heading, tc_heading,
    body_para, label_value_para, bullet_item,
    spacer, terminal_block, add_screenshot, status_result_table,
    two_col_info_table, four_col_table,
    build_doc_with_header_footer,
)
from icaf.config.settings import settings


class Clause193Report:
    """
    Generates a .docx (then PDF) compliance report for ITSAR clause 1.9.3.

    Receives:
        context  — icaf RuntimeContext  (has .ssh_ip, .dut_name, etc.)
        tc_objects  — list of icaf TestCase objects  (each has .raw_result dict)
    """

    def __init__(self, context, tc_objects: list):
        self.context    = context
        self.tc_objects = tc_objects
        # Unwrap flat result dicts produced by the clause test cases
        self.results: list[dict] = [
            getattr(tc, "raw_result", {}) for tc in tc_objects
        ]

    # ── Public entry point ────────────────────────────────────────────────────

    def generate(self) -> str:
        results = self.results
        ctx     = self.context
        now     = datetime.datetime.now()

        passed  = sum(1 for r in results if r.get("verdict") == "PASS")
        failed  = sum(1 for r in results if r.get("verdict") == "FAIL")
        errors  = sum(1 for r in results if r.get("verdict") == "ERROR")
        total   = len(results)
        overall = "PASS" if total > 0 and failed == 0 and errors == 0 else "FAIL"

        dut_name    = getattr(ctx, "dut_name",    None) or ctx.ssh_ip or "DUT"
        dut_version = getattr(ctx, "dut_version", None) or "Alpine Linux / Router OS"
        start_time  = ctx.start_time.strftime("%Y-%m-%d %H:%M:%S") \
                      if hasattr(ctx, "start_time") else now.strftime("%Y-%m-%d %H:%M:%S")

        # ── Build doc with icaf header/footer ─────────────────────────────
        doc = build_doc_with_header_footer(dut_name, dut_version)
        self._set_clause_header(doc)

        # ── Front page ────────────────────────────────────────────────────
        self._add_front_page(doc, dut_name, dut_version, start_time,
                             now.strftime("%Y-%m-%d %H:%M:%S"), overall)

        # ── Section 1: Requirement Description ───────────────────────────
        section_heading(doc, "1. Requirement Description")
        bullet_item(doc,
            "(i) The purpose of vulnerability scanning is to ensure that there are no "
            "known vulnerabilities (or that relevant vulnerabilities are identified and remediation "
            "plans are in place to mitigate them) on the Network Product, both in the OS and in the installed applications.")
        bullet_item(doc,
            "(ii) Automated vulnerability assessment scanning tools must be executed via the "
            "Internet Protocol (IP) enabled network interfaces of the DUT.")
        bullet_item(doc,
            "(iii) The scan must be conducted with appropriate credentials/privilege elevation "
            "to perform an in-depth authenticated security evaluation across all exposed services and software packages.")
        spacer(doc, small=True)

        # ── Section 2: DUT Configuration ─────────────────────────────────
        section_heading(doc, "2. DUT Configuration")
        sub_heading(doc, "2.1 Network Services & Interface Configuration")
        body_para(doc,
            "The network interfaces and listening services on the DUT were identified and inspected. "
            "The configuration baseline of the DUT under assessment includes:")
        for b in [
            f"Target IP Interface configured and reachable at: {ctx.ssh_ip}",
            "Administrative remote management protocol enabled: SSH (TCP Port 22)",
            "System inspection interfaces: Active network sockets, transport layer listeners (TCP/UDP), and daemon services",
            "Authentication profile: Automated assessment executed using provisioned target credentials with administrative privilege",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        sub_heading(doc, "2.2 Vulnerability Scanner Integration")
        body_para(doc,
            "The tester system established authenticated scanning communication targeting the DUT's IP interface. "
            "The vulnerability scanning suite utilized recent vulnerability databases and CVE feeds "
            "to probe for known service exposures, weak crypto suites, and obsolete software baselines.")
        spacer(doc, small=True)

        # ── Section 3: Preconditions ──────────────────────────────────────
        section_heading(doc, "3. Preconditions")
        for b in [
            f"DUT is operational and network reachable at {ctx.ssh_ip}.",
            "All IP-based network interfaces and exposed transport protocols are documented.",
            "Valid administrative/audit credentials are provisioned for credential-based scanning.",
            "Vulnerability scanning tool database is up-to-date with recent vulnerability intelligence.",
            "ICAF test harness has established network connectivity and capture capabilities.",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        # ── Section 4: Test Objective ─────────────────────────────────────
        section_heading(doc, "4. Test Objective")
        body_para(doc,
            "To verify that the Device Under Test (DUT) does not contain known, unmitigated "
            "vulnerabilities across its operating system components and network services. The test specifically validates:")
        for b in [
            "Execution of credential-based vulnerability audit against active IP interfaces.",
            "Identification and reporting of any Critical, Severe, or Moderate vulnerability findings.",
            "Verification of cryptographic security, network service configurations (e.g., SSH, NTP), and OS package integrity.",
            "Verification that any identified vulnerability has an effective remediation or mitigation plan.",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        # ── Section 5: Test Scenario ──────────────────────────────────────
        section_heading(doc, "5. Test Scenario")
        sub_heading(doc, "5.1 Number of Test Scenarios")
        body_para(doc, f"Total of {total} test scenario(s) executed under Clause 1.9.3.")
        spacer(doc, small=True)

        two_col_info_table(doc,
            headers    =["Component", "Details"],
            col_widths =[3500, 5860],
            data_rows  =[
                ("Tester System",  f"Ubuntu Linux / ICAF Engine — {getattr(ctx, 'tester_ip', '127.0.0.1')}"),
                ("DUT",            f"{dut_name} ({dut_version}) — {ctx.ssh_ip}"),
                ("Audit Type",     "Full Authenticated / Credential-based Vulnerability Audit"),
                ("Framework",      "ICAF — ITSAR Compliance Automation Framework"),
            ]
        )
        spacer(doc, small=True)

        sub_heading(doc, "5.2 Tools Required")
        for b in [
            "Vulnerability Scanning Engine (Nexpose / Nessus / OpenVAS / Nmap Vuln Engine)",
            "Python 3 + Paramiko — SSH command execution and DUT telemetry capture",
            "python-docx — ITSAR compliant DOCX / PDF report compilation",
            "tmux + gnome-terminal — Real-time visual terminal execution tracking",
            "Network Packet Capture (Pcap) engine for traffic validation",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        sub_heading(doc, "5.3 Test Execution Steps")
        for b in [
            "Discover and validate DUT IP interfaces and active listening transport ports.",
            "Initiate an authenticated vulnerability scan targeting all open network interfaces.",
            "Perform in-depth package inspection, OS version matching, and cryptographic protocol auditing.",
            "Generate and capture the structured vulnerability scan report.",
            "Parse findings and evaluate each observation based on severity (Critical, Severe, Moderate).",
            "Collate evidence, logs, and screenshots into the final compliance report.",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        # ── Section 6: Expected Results ───────────────────────────────────
        section_heading(doc, "6. Expected Results for Pass")
        body_para(doc,
            "The credential-based vulnerability scan report generated against the DUT shall show NO "
            "known vulnerabilities (Critical, Severe, or Moderate) across the operating system and running services. "
            "In case any findings are reported, documented remediation and mitigation plans must be active. "
            "The report must be accessible, valid, and successfully verified by the framework.")
        spacer(doc, small=True)

        doc.add_page_break()

        # ── Section 7: Test Execution ─────────────────────────────────────
        section_heading(doc, "7. Test Execution")

        for r in results:
            tc_id   = r.get("tc_id", "TC-1-9-3-001")
            tc_name = r.get("tc_name", "Conduct Credential-based Vulnerability Scan")
            verdict = r.get("verdict", "FAIL")
            vc = (PASS_GREEN if verdict == "PASS"
                  else FAIL_RED if verdict == "FAIL"
                  else ERROR_ORANGE)

            tc_heading(doc, f"Test Case: {tc_id}")
            label_value_para(doc, "a) Test Case Name",        tc_id)
            label_value_para(doc, "b) Test Case Description", r.get("description", tc_name))
            spacer(doc, small=True)

            body_para(doc, "c) Input Command / Audit Trigger:", bold=True)
            terminal_block(doc, [r.get("input_cmd", "(none)")])
            spacer(doc, small=True)

            label_value_para(doc, "d) Expected Result", r.get("expected", "0 known vulnerabilities detected"))
            label_value_para(doc, "e) Actual Result",
                             r.get("actual_status", verdict), value_color=vc)
            spacer(doc, small=True)

            body_para(doc, "f) Scan Output & Audit Findings:", bold=True)
            output_lines = str(r.get("output", "")).split("\n")[:40]
            terminal_block(doc, output_lines)
            spacer(doc, small=True)

            status_result_table(doc, verdict,
                                label=f"{tc_id} — {tc_name[:60]}")
            spacer(doc, small=True)

            # Screenshots & Evidence Files
            for ef in (r.get("evidence_files") or []):
                if ef and ef.lower().endswith(".png") and os.path.exists(ef):
                    body_para(doc, "Terminal Screenshot (Evidence):", bold=True)
                    add_screenshot(doc, ef, width_inches=5.5)

            spacer(doc)

        doc.add_page_break()

        # ── Section 8: Test Observation ───────────────────────────────────
        section_heading(doc, "8. Test Observation for Vulnerability Scanning")
        if overall == "PASS":
            body_para(doc,
                "It was observed that the Device Under Test (DUT) complies with ITSAR Clause 1.9.3 requirements. "
                "The authenticated vulnerability scan completed successfully and identified no unmitigated "
                "vulnerabilities across the operating system or active application services.")
        else:
            failed_ids = [r.get("tc_id", "TC") for r in results if r.get("verdict") != "PASS"]
            body_para(doc,
                f"It was observed that the Device Under Test (DUT) does not fully comply with the vulnerability scanning "
                f"requirements. Findings/Failures were recorded under: {', '.join(failed_ids)}. "
                f"Known vulnerabilities were identified on the DUT IP interface without confirmed remediation plans, "
                f"posing potential operational and security risks.")
        spacer(doc, small=True)

        # ── Section 9: Test Case Results Table ───────────────────────────
        section_heading(doc, "9. Test Case Result for Vulnerability Scanning")
        four_col_table(doc,
            headers    =["SL. No", "TEST CASE NAME", "PASS/FAIL", "Remarks"],
            col_widths =[700, 4500, 1500, 2660],
            data_rows  =[
                (str(i + 1),
                 f"{r.get('tc_id','')} — {r.get('tc_name','')[:45]}",
                 r.get("verdict", "FAIL"),
                 r.get("actual_status", "")[:60])
                for i, r in enumerate(results)
            ]
        )
        spacer(doc)

        status_result_table(doc, overall,
                            label=f"Overall Result — {passed}/{total} passed")
        spacer(doc)

        # ── Section 10: Compliance Analysis ──────────────────────────────
        section_heading(doc, "10. Compliance Analysis")
        two_col_info_table(doc,
            headers    =["Clause Requirement", "Result"],
            col_widths =[7200, 2160],
            data_rows  =[
                ("Vulnerability assessment tool operational against DUT IP",
                 "PASS" if total > 0 else "FAIL"),
                ("Credential-based authenticated scan successfully executed",
                 self._first_verdict()),
                ("No Critical / High OS vulnerabilities detected (e.g. obsolete OS)",
                 self._first_verdict()),
                ("No Severe service vulnerabilities detected (e.g. NTP amplification, weak SSH MACs)",
                 self._first_verdict()),
                ("No Moderate information disclosure vulnerabilities detected",
                 self._first_verdict()),
                ("Remediation plans verified for reported findings",
                 self._first_verdict()),
            ]
        )
        spacer(doc)

        # ── Section 11: Conclusion ────────────────────────────────────────
        section_heading(doc, "11. Conclusion")
        if overall == "PASS":
            body_para(doc,
                f"All {total} test case(s) passed. The DUT successfully satisfied ITSAR clause 1.9.3. "
                "The credential-based audit confirmed that all exposed services and underlying OS components "
                "are hardened and free of known unmitigated vulnerabilities.")
        else:
            body_para(doc,
                f"The test execution identified {failed} failing test case(s) and {errors} error(s). "
                "The DUT does NOT comply with Clause 1.9.3 vulnerability scanning requirements. "
                "Remediation is required before the product can achieve certification.")
        spacer(doc, small=True)

        body_para(doc, "Recommendations:", bold=True)
        for b in [
            "Upgrade obsolete operating system packages and base distributions to maintained Long-Term Support (LTS) releases.",
            "Disable or reconfigure vulnerable service features (e.g., restrict ntpd monlist / request nonce queries).",
            "Deprecate weak Message Authentication Codes (MACs) and weak ciphers in SSH daemon configuration.",
            "Apply vendor security patches and ensure continuous automated vulnerability scanning is integrated.",
            "Re-run the Clause 1.9.3 automated scan suite after remediation to verify compliance closure.",
        ]:
            bullet_item(doc, b)

        # ── Save docx → PDF ───────────────────────────────────────────────
        ts         = now.strftime("%Y%m%d_%H%M%S")
        report_dir = str(settings.REPORT_DIR)
        os.makedirs(report_dir, exist_ok=True)
        docx_path  = os.path.join(report_dir, f"clause_1_9_3_report_{ts}.docx")
        doc.save(docx_path)

        subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf",
             docx_path, "--outdir", report_dir],
            capture_output=True, text=True
        )
        pdf_path = docx_path.replace(".docx", ".pdf")
        if os.path.exists(pdf_path):
            os.remove(docx_path)
            return pdf_path
        return docx_path

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _first_verdict(self) -> str:
        if not self.results:
            return "N/A"
        return self.results[0].get("verdict", "N/A")

    @staticmethod
    def _set_clause_header(doc) -> None:
        try:
            for paragraph in doc.sections[0].header.paragraphs:
                for run in paragraph.runs:
                    if "1.1.1" in run.text or "1.2.4" in run.text:
                        run.text = run.text.replace("1.1.1", "1.9.3").replace("1.2.4", "1.9.3")
        except Exception:
            pass

    def _add_front_page(self, doc, dut_name, dut_version,
                        start_time, end_time, overall):
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from icaf.reporting.helpers import (
            PURPLE, MID_GREY, HEX_PURPLE,
            spacer, four_col_table, two_col_info_table,
            _add_para_border_bottom,
        )

        spacer(doc, large=True)
        spacer(doc, large=True)

        def _centered(text, size_pt, color, bold=False):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(text)
            run.bold = bold
            run.font.size = Pt(size_pt)
            run.font.name = "Arial"
            run.font.color.rgb = color
            return p

        p = _centered("Vulnerability Scanning Test Report", 22, PURPLE, bold=True)
        _add_para_border_bottom(p, HEX_PURPLE, size=12)
        _centered("ITSAR Clause 1.9.3 — Vulnerability Assessment", 13, MID_GREY)
        spacer(doc, large=True)

        four_col_table(doc,
            headers   =["Document No.", "Created By", "Reviewed By", "Approved By"],
            data_rows =[("1", "ICAF Framework", "Reviewer", "Approver")],
            col_widths=[2340, 2340, 2340, 2340],
        )
        spacer(doc, small=True)
        spacer(doc)

        two_col_info_table(doc,
            headers    =["Field", "Value"],
            col_widths =[3500, 5860],
            data_rows  =[
                ("DUT Details",             dut_name),
                ("DUT Host / Target IP",    getattr(self.context, "ssh_ip", "N/A")),
                ("DUT Software Version",    dut_version),
                ("Type",                    "Auto Generated Validation Report"),
                ("Test Start",              start_time),
                ("Test End",                end_time),
                ("Requirement Test Result", overall),
            ]
        )
        doc.add_page_break()