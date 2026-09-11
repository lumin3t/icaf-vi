"""
icaf/clauses/clause_1_2_1/testcases/tc_6_ssh_incorrect_auth.py

TC6: SSH - Incorrect Authentication
Verify that DUT SSH server rejects connection attempts with wrong password.
"""

import socket
import paramiko
from icaf.core.result_recorder import record_result, save_evidence
from icaf.utils.logger import logger


def run(context):
    """Execute TC6: SSH authentication with incorrect password."""
    tc_id = "TC6"
    tc_name = "SSH - Incorrect Authentication"
    description = "Verify DUT SSH rejects incorrect password even with correct username"
    
    dut_ip = context.ssh_ip
    test_user = context.ssh_user
    wrong_pass = "WRONG_PASSWORD_12345"
    expected = "SSH rejects connection with incorrect password"
    
    all_output = []
    verdict = "FAIL"
    
    try:
        all_output.append(f"Target: {dut_ip}:22")
        all_output.append(f"User: {test_user} (wrong password)")
        all_output.append("Attempting SSH with incorrect password...")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            client.connect(
                hostname=dut_ip,
                port=22,
                username=test_user,
                password=wrong_pass,
                timeout=10,
                allow_agent=False,
                look_for_keys=False,
            )
            
            verdict = "FAIL"
            actual = "SSH accepted incorrect password (SECURITY FAILURE)"
            all_output.append("❌ FAIL: SSH accepted wrong password")
            client.close()
        
        except paramiko.AuthenticationException:
            verdict = "PASS"
            actual = "SSH correctly rejected incorrect password"
            all_output.append("✓ PASS: SSH rejected incorrect password")
        
        except socket.timeout:
            verdict = "ERROR"
            actual = "Connection timeout"
            all_output.append("❌ ERROR: SSH connection timeout")
        
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
        evidence = save_evidence(tc_id, "ssh_incorrect_auth", "\n".join(all_output))
        record_result(
            tc_id=tc_id,
            tc_name=tc_name,
            description=description,
            input_cmd=f"ssh {test_user}@{dut_ip} (wrong password)",
            output="\n".join(all_output),
            expected=expected,
            actual_status=actual,
            verdict=verdict,
            evidence_files=[evidence]
        )