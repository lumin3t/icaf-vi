"""
icaf/clauses/clause_1_2_1/testcases/tc_4_ssh_no_auth.py

TC4: SSH - No Authentication
Verify that DUT SSH server rejects connection attempts without credentials.
"""

import socket
import paramiko
from icaf.core.result_recorder import record_result, save_evidence
from icaf.utils.logger import logger


def run(context):
    """Execute TC4: SSH connection without credentials must be rejected."""
    tc_id = "TC4"
    tc_name = "SSH - No Authentication"
    description = "Verify DUT SSH rejects connection attempts without credentials"
    
    dut_ip = context.ssh_ip
    expected = "SSH server rejects unauthenticated connection"
    
    all_output = []
    verdict = "FAIL"
    
    try:
        all_output.append(f"Target: {dut_ip}:22")
        all_output.append("Attempting SSH without credentials...")
        
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
            actual = "SSH accepted connection without credentials (SECURITY FAILURE)"
            all_output.append("❌ FAIL: SSH accepted empty credentials")
            client.close()
        
        except paramiko.AuthenticationException:
            verdict = "PASS"
            actual = "SSH correctly rejected unauthenticated connection"
            all_output.append("✓ PASS: SSH rejected empty credentials")
        
        except socket.timeout:
            verdict = "ERROR"
            actual = "Connection timeout"
            all_output.append("❌ ERROR: SSH connection timeout")
        
        except (socket.error, socket.gaierror, ConnectionRefusedError) as e:
            verdict = "ERROR"
            actual = f"Network error: {type(e).__name__}"
            all_output.append(f"❌ ERROR: {type(e).__name__}")
        
        except paramiko.SSHException as e:
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
        all_output.append(f"❌ ERROR: Test execution failed")
    
    finally:
        evidence = save_evidence(tc_id, "ssh_no_auth", "\n".join(all_output))
        record_result(
            tc_id=tc_id,
            tc_name=tc_name,
            description=description,
            input_cmd="ssh (no credentials)",
            output="\n".join(all_output),
            expected=expected,
            actual_status=actual,
            verdict=verdict,
            evidence_files=[evidence]
        )