import paramiko

host = "192.168.56.101"
user = "root"
password = "PUT_YOUR_REAL_PASSWORD_HERE"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

client.connect(
    hostname=host,
    port=22,
    username=user,
    password=password,
    timeout=30,
    banner_timeout=30,
    auth_timeout=30,
    look_for_keys=False,
    allow_agent=False,
)

stdin, stdout, stderr = client.exec_command("whoami")
print("STDOUT:")
print(stdout.read().decode())
print("STDERR:")
print(stderr.read().decode())

client.close()
