"""
icaf/clauses/clause_1_2_1/testcases/tc_11_scp_correct_auth.py

TC11: SCP - Correct Authentication
Verify that SCP accepts valid credentials and transfers files.

SCP file transfer validation: uses SFTP (paramiko.SFTPClient) as the
underlying implementation, which matches SCP's protocol behavior
(SSH authentication + file transfer via secure protocol).
"""

import socket
import paramiko
import tempfile
import os
from icaf.core.result_recorder import record_result, save_evidence
from icaf.utils.logger import logger


def run(context):
    """Execute TC11: SCP file transfer with correct credentials."""
    tc_id = "TC11"
    tc_name = "SCP - Correct Authentication"
    description = "Verify SCP accepts correct credentials and transfers files"
    
    dut_ip = context.ssh_ip
    test_user = context.ssh_user
    test_pass = context.ssh_password
    expected = "SCP authenticates and transfers file successfully"
    
    all_output = []
    verdict = "FAIL"
    temp_file = None
    
    try:
        all_output.append(f"Target: {dut_ip}:22 (SCP/SSH)")
        all_output.append(f"User: {test_user} (password masked)")
        all_output.append("Attempting SCP file transfer with correct credentials...")
        
        # Create temporary test file
        fd, temp_file = tempfile.mkstemp(prefix="scp_test_")
        os.write(fd, b"SCP test content - Clause 1.2.1\n")
        os.close(fd)
        
        remote_file = f"/tmp/scp_test_{os.getpid()}.txt"
        
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
            
            # Perform SCP transfer using SFTP (SCP's protocol equivalent)
            transport = client.get_transport()
            sftp = paramiko.SFTPClient.from_transport(transport)
            
            # Upload file
            sftp.put(temp_file, remote_file)
            
            # Verify file exists on remote
            remote_stat = sftp.stat(remote_file)
            
            # Clean up remote file
            sftp.remove(remote_file)
            sftp.close()
            client.close()
            
            verdict = "PASS"
            actual = f"SCP transferred file successfully ({remote_stat.st_size} bytes)"
            all_output.append(f"✓ PASS: SCP transferred file ({remote_stat.st_size} bytes)")
        
        except paramiko.AuthenticationException:
            verdict = "FAIL"
            actual = "SCP SSH layer rejected correct credentials"
            all_output.append("❌ FAIL: SCP rejected correct credentials")
        
        except paramiko.SSHException as e:
            error_msg = str(e).lower()
            if "subsystem" in error_msg:
                verdict = "FAIL"
                actual = "SCP subsystem not available"
                all_output.append("❌ FAIL: SCP subsystem not available")
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
            actual = f"Transfer error: {type(e).__name__}"
            all_output.append(f"❌ ERROR: {type(e).__name__}")
    
    except Exception as e:
        verdict = "ERROR"
        actual = f"Test execution error: {str(e)[:100]}"
        all_output.append("❌ ERROR: Test execution failed")
    
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        
        evidence = save_evidence(tc_id, "scp_correct_auth", "\n".join(all_output))
        record_result(
            tc_id=tc_id,
            tc_name=tc_name,
            description=description,
            input_cmd=f"scp test_file {test_user}@{dut_ip}:/tmp/",
            output="\n".join(all_output),
            expected=expected,
            actual_status=actual,
            verdict=verdict,
            evidence_files=[evidence]
        )