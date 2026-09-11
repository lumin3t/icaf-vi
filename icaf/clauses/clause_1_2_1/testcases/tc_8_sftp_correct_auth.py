"""
icaf/clauses/clause_1_2_1/testcases/tc_8_sftp_correct_auth.py

TC8: SFTP - Correct Authentication
Verify that SFTP accepts valid credentials and establishes subsystem.
"""

import socket
import paramiko
from icaf.core.result_recorder import record_result, save_evidence
from icaf.utils.logger import logger


def run(context):
    """Execute TC8: SFTP authentication with correct credentials."""
    tc_id = "TC8"
    tc_name = "SFTP - Correct Authentication"
    description = "Verify SFTP authenticates with correct credentials and enables file operations"
    
    dut_ip = context.ssh_ip
    test_user = context.ssh_user
    test_pass = context.ssh_password
    expected = "SFTP authenticates and subsystem is ready"
    
    all_output = []
    verdict = "FAIL"
    
    try:
        all_output.append(f"Target: {dut_ip}:22 (SFTP/SSH)")
        all_output.append(f"User: {test_user} (password masked)")
        all_output.append("Attempting SFTP with correct credentials...")
        
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
            
            # Initialize SFTP subsystem
            transport = client.get_transport()
            sftp_client = paramiko.SFTPClient.from_transport(transport)
            
            # Perform actual SFTP operation - list directory
            files = sftp_client.listdir(".")
            
            verdict = "PASS"
            actual = f"SFTP authenticated successfully, listed {len(files)} items in home directory"
            all_output.append(f"✓ PASS: SFTP authenticated, subsystem ready")
            all_output.append(f"        Listed {len(files)} items in home directory")
            
            sftp_client.close()
            client.close()
        
        except paramiko.AuthenticationException:
            verdict = "FAIL"
            actual = "SFTP SSH layer rejected correct credentials"
            all_output.append("❌ FAIL: SFTP rejected correct credentials")
        
        except paramiko.SSHException as e:
            error_msg = str(e).lower()
            if "subsystem" in error_msg or "sftp" in error_msg:
                verdict = "FAIL"
                actual = "SFTP subsystem negotiation failed"
                all_output.append("❌ FAIL: SFTP subsystem not available")
            else:
                verdict = "ERROR"
                actual = "SSH protocol error"
                all_output.append("❌ ERROR: SSH protocol error")
        
        except socket.timeout:
            verdict = "ERROR"
            actual = "Connection timeout"
            all_output.append("❌ ERROR: Connection timeout")
        
        except (socket.error, socket.gaierror, ConnectionRefusedError):
            verdict = "ERROR"
            actual = "Network error"
            all_output.append("❌ ERROR: Network error")
        
        except Exception as e:
            verdict = "ERROR"
            actual = f"Unexpected error: {type(e).__name__}"
            all_output.append(f"❌ ERROR: {type(e).__name__}")
    
    except Exception as e:
        verdict = "ERROR"
        actual = f"Test execution error: {str(e)[:100]}"
        all_output.append("❌ ERROR: Test execution failed")
    
    finally:
        evidence = save_evidence(tc_id, "sftp_correct_auth", "\n".join(all_output))
        record_result(
            tc_id=tc_id,
            tc_name=tc_name,
            description=description,
            input_cmd=f"sftp {test_user}@{dut_ip}",
            output="\n".join(all_output),
            expected=expected,
            actual_status=actual,
            verdict=verdict,
            evidence_files=[evidence]
        )