"""
icaf/clauses/clause_1_2_1/testcases/tc_10_scp_no_auth.py

TC10: SCP - No Authentication
Verify that SCP (secure copy) rejects connection attempts without credentials.

SCP uses SSH for authentication and transport. This test validates that
the SSH authentication layer (which SCP depends on) rejects unauthenticated access.
"""

import socket
import paramiko
from icaf.core.result_recorder import record_result, save_evidence
from icaf.utils.logger import logger


def run(context):
    """Execute TC10: SCP connection without credentials must be rejected."""
    tc_id = "TC10"
    tc_name = "SCP - No Authentication"
    description = "Verify SCP SSH transport rejects connection without credentials"
    
    dut_ip = context.ssh_ip
    expected = "SCP SSH transport rejects unauthenticated connection"
    
    all_output = []
    verdict = "FAIL"
    
    try:
        all_output.append(f"Target: {dut_ip}:22 (SCP/SSH)")
        all_output.append("Attempting SCP without credentials...")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # SCP uses SSH authentication layer
            client.connect(
                hostname=dut_ip,
                port=22,
                username="",
                password="",
                timeout=10,
                allow_agent=False,
                look_for_keys=False,
            )
            
            verdict = "FAIL"
            actual = "SCP SSH transport accepted empty credentials"
            all_output.append("❌ FAIL: SCP SSH accepted empty credentials")
            client.close()
        
        except paramiko.AuthenticationException:
            verdict = "PASS"
            actual = "SCP SSH transport correctly rejected unauthenticated connection"
            all_output.append("✓ PASS: SCP SSH rejected empty credentials")
        
        except socket.timeout:
            verdict = "ERROR"
            actual = "Connection timeout"
            all_output.append("❌ ERROR: Connection timeout")
        
        except (socket.error, socket.gaierror, ConnectionRefusedError):
            verdict = "ERROR"
            actual = "Network error"
            all_output.append("❌ ERROR: Network error")
        
        except paramiko.SSHException:
            verdict = "ERROR"
            actual = "SSH protocol error"
            all_output.append("❌ ERROR: SSH protocol error")
        
        except Exception as e:
            verdict = "ERROR"
            actual = f"Unexpected error: {type(e).__name__}"
            all_output.append(f"❌ ERROR: {type(e).__name__}")
    
    except Exception as e:
        verdict = "ERROR"
        actual = f"Test execution error: {str(e)[:100]}"
        all_output.append("❌ ERROR: Test execution failed")
    
    finally:
        evidence = save_evidence(tc_id, "scp_no_auth", "\n".join(all_output))
        record_result(
            tc_id=tc_id,
            tc_name=tc_name,
            description=description,
            input_cmd="scp (no credentials)",
            output="\n".join(all_output),
            expected=expected,
            actual_status=actual,
            verdict=verdict,
            evidence_files=[evidence]
        )