"""
icaf/clauses/clause_1_2_1/testcases/tc_9_sftp_incorrect_auth.py

TC9: SFTP - Incorrect Authentication
Verify that SFTP rejects connection with incorrect password.
"""

import socket
import paramiko
from icaf.core.result_recorder import record_result, save_evidence
from icaf.utils.logger import logger


def run(context):
    """Execute TC9: SFTP authentication with incorrect password."""
    tc_id = "TC9"
    tc_name = "SFTP - Incorrect Authentication"
    description = "Verify SFTP rejects incorrect password even with correct username"
    
    dut_ip = context.ssh_ip
    test_user = context.ssh_user
    wrong_pass = "WRONG_PASSWORD_12345"
    expected = "SFTP SSH layer rejects incorrect password"
    
    all_output = []
    verdict = "FAIL"
    
    try:
        all_output.append(f"Target: {dut_ip}:22 (SFTP/SSH)")
        all_output.append(f"User: {test_user} (wrong password)")
        all_output.append("Attempting SFTP with incorrect password...")
        
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
            actual = "SFTP SSH layer accepted incorrect password"
            all_output.append("❌ FAIL: SFTP accepted wrong password")
            client.close()
        
        except paramiko.AuthenticationException:
            verdict = "PASS"
            actual = "SFTP SSH layer correctly rejected incorrect password"
            all_output.append("✓ PASS: SFTP rejected incorrect password")
        
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
        evidence = save_evidence(tc_id, "sftp_incorrect_auth", "\n".join(all_output))
        record_result(
            tc_id=tc_id,
            tc_name=tc_name,
            description=description,
            input_cmd=f"sftp {test_user}@{dut_ip} (wrong password)",
            output="\n".join(all_output),
            expected=expected,
            actual_status=actual,
            verdict=verdict,
            evidence_files=[evidence]
        )