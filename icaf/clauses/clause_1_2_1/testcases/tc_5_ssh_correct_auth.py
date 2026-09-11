"""
icaf/clauses/clause_1_2_1/testcases/tc_5_ssh_correct_auth.py

TC5: SSH - Correct Authentication
Verify that DUT SSH server accepts valid credentials and grants shell access.
"""

import socket
import paramiko
from icaf.core.result_recorder import record_result, save_evidence
from icaf.utils.logger import logger


def run(context):
    """Execute TC5: SSH authentication with correct credentials."""
    tc_id = "TC5"
    tc_name = "SSH - Correct Authentication"
    description = "Verify DUT SSH accepts correct username and password credentials"
    
    dut_ip = context.ssh_ip
    test_user = context.ssh_user
    test_pass = context.ssh_password
    expected = f"SSH authenticates {test_user} and grants shell access"
    
    all_output = []
    verdict = "FAIL"
    
    try:
        all_output.append(f"Target: {dut_ip}:22")
        all_output.append(f"User: {test_user} (password masked)")
        all_output.append("Attempting SSH with correct credentials...")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            client.connect(
                hostname=dut_ip,
                port=22,
                username=test_user,
                password=test_pass,
                timeout=10,
                allow_agent=False,
                look_for_keys=False,
            )
            
            # Verify authentication by executing whoami
            stdin, stdout, stderr = client.exec_command("whoami", timeout=5)
            output = stdout.read().decode('utf-8', errors='replace').strip()
            
            if output == test_user:
                verdict = "PASS"
                actual = f"SSH authenticated successfully as {test_user}"
                all_output.append(f"✓ PASS: SSH authenticated as {test_user}")
            else:
                verdict = "FAIL"
                actual = f"SSH authenticated but unexpected user: {output}"
                all_output.append(f"❌ FAIL: Unexpected user: {output}")
            
            client.close()
        
        except paramiko.AuthenticationException:
            verdict = "FAIL"
            actual = "SSH rejected correct credentials"
            all_output.append("❌ FAIL: SSH rejected correct credentials")
        
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
        evidence = save_evidence(tc_id, "ssh_correct_auth", "\n".join(all_output))
        record_result(
            tc_id=tc_id,
            tc_name=tc_name,
            description=description,
            input_cmd=f"ssh {test_user}@{dut_ip}",
            output="\n".join(all_output),
            expected=expected,
            actual_status=actual,
            verdict=verdict,
            evidence_files=[evidence]
        )