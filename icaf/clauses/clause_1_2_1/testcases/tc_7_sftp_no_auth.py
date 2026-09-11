"""
icaf/clauses/clause_1_2_1/testcases/tc_7_sftp_no_auth.py

TC7: SFTP - No Authentication
Verify that SFTP (over SSH) rejects connection attempts without credentials.
"""

import socket
import paramiko
from icaf.core.result_recorder import record_result, save_evidence
from icaf.utils.logger import logger


def run(context):
    """Execute TC7: SFTP connection without credentials must be rejected."""
    tc_id = "TC7"
    tc_name = "SFTP - No Authentication"
    description = "Verify DUT SFTP (SSH subsystem) rejects connection without credentials"
    
    dut_ip = context.ssh_ip
    expected = "SFTP SSH layer rejects unauthenticated connection"
    
    all_output = []
    verdict = "FAIL"
    
    try:
        all_output.append(f"Target: {dut_ip}:22 (SFTP/SSH)")
        all_output.append("Attempting SFTP without credentials...")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
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
            actual = "SFTP SSH layer accepted empty credentials"
            all_output.append("❌ FAIL: SFTP SSH accepted empty credentials")
            client.close()
        
        except paramiko.AuthenticationException:
            verdict = "PASS"
            actual = "SFTP SSH layer correctly rejected unauthenticated connection"
            all_output.append("✓ PASS: SFTP SSH rejected empty credentials")
        
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
            actual = "SSH/SFTP protocol error"
            all_output.append("❌ ERROR: SSH/SFTP protocol error")
        
        except Exception as e:
            verdict = "ERROR"
            actual = f"Unexpected error: {type(e).__name__}"
            all_output.append(f"❌ ERROR: {type(e).__name__}")
    
    except Exception as e:
        verdict = "ERROR"
        actual = f"Test execution error: {str(e)[:100]}"
        all_output.append("❌ ERROR: Test execution failed")
    
    finally:
        evidence = save_evidence(tc_id, "sftp_no_auth", "\n".join(all_output))
        record_result(
            tc_id=tc_id,
            tc_name=tc_name,
            description=description,
            input_cmd="sftp (no credentials)",
            output="\n".join(all_output),
            expected=expected,
            actual_status=actual,
            verdict=verdict,
            evidence_files=[evidence]
        )