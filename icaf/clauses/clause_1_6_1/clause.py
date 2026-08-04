from icaf.core.clause import BaseClause
from icaf.core.testcase import TestCase

from icaf.tools.scanners.nmap_scan import run_nmap_scan
from icaf.tools.scanners.cipher_support import run_cipher_detection
from icaf.tools.scanners.ssh_verify import run_ssh_verification
from icaf.tools.scanners.force_weak import run_ssh_weak_cipher_test
from icaf.tools.scanners.TLS_cipher_support import run_httpsCipher_detection
from icaf.tools.scanners.TLS_verify import run_tls_verification
from icaf.utils.dut_info import get_dut_info


class Clause_1_6_1(BaseClause):

    name = "1.6.1 Cryptographic Based Secure Communication"

    def __init__(self, context):

        super().__init__(context)

    def run(self):

        nmap_result = run_nmap_scan(self.context)
        cipher_result = run_cipher_detection(self.context)
        ssh_result = run_ssh_verification(self.context)

        weak_cipher_result = run_ssh_weak_cipher_test(self.context, cipher_result)

        https_cipher_data = run_httpsCipher_detection(self.context)
        https_data = run_tls_verification(self.context)

        dut_info = get_dut_info(self.context.ssh_user, self.context.ssh_ip, self.context.ssh_password)

        self.context.scan_results = {
            "nmap": nmap_result,
            "cipher": cipher_result,
            "ssh": ssh_result,
            "weak_cipher": weak_cipher_result,
            "https_cipher": https_cipher_data,
            "https": https_data,
            "dut_info": dut_info
        }

        results = []

        results.append(
            TestCase(
                name="SSH Cipher Detection",
                description="Check SSH supported encryption algorithms",
            )
        )

        results.append(
            TestCase(
                name="SSH Weak Cipher Negotiation",
                description="Ensure weak SSH ciphers cannot be negotiated",
            )
        )

        results.append(
            TestCase(
                name="SSH Secure Communication",
                description="Verify SSH secure communication",
            )
        )

        results.append(
            TestCase(
                name="HTTPS Cipher Hardening",
                description="Verify TLS cipher security",
            )
        )

        results.append(
            TestCase(
                name="HTTPS Secure Communication",
                description="Verify TLS secure communication",
            )
        )

        return results
