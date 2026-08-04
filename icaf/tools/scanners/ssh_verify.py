import subprocess
import time
# pyautogui imported lazily inside functions (avoids X display error at import time)
import os
import re
from datetime import datetime


SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# ---------------- TERMINAL CONTROL ----------------

def launch_terminal(title=None):

    cmd = ["gnome-terminal"]

    if title:
        cmd += ["--title", title]

    subprocess.Popen(cmd)

    time.sleep(3)


def focus_window(title):

    subprocess.run(["wmctrl", "-a", title])
    time.sleep(1)


def maximize_terminal():

    import pyautogui
    pyautogui.hotkey("alt", "f10")
    time.sleep(1)


def close_terminal():

    import pyautogui
    pyautogui.hotkey("ctrl", "c")
    time.sleep(1)

    pyautogui.typewrite("exit\n", interval=0.05)
    time.sleep(0.5)


# ---------------- SCREENSHOT ----------------

def take_screenshot(label):

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    path = f"{SCREENSHOT_DIR}/{ts}_{label}.png"

    import pyautogui
    pyautogui.screenshot(path)

    return path


# ---------------- SSH OUTPUT CAPTURE ----------------

def capture_ssh_terminal_output(user, ip):

    result = subprocess.run(
        ["ssh", f"{user}@{ip}", "exit"],
        capture_output=True,
        text=True
    )

    return result.stdout.strip()


# ---------------- WIRESHARK ----------------

def launch_wireshark(interface):

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    pcap_file = f"full_capture_{ts}.pcap"

    subprocess.Popen([
        "wireshark",
        "-i", interface,
        "-k",
        "-w", pcap_file
    ])

    time.sleep(8)

    return pcap_file


def apply_ssh_filter():

    import pyautogui
    pyautogui.hotkey("ctrl", "/")
    time.sleep(1)

    pyautogui.typewrite("ssh", interval=0.05)

    pyautogui.press("enter")

    time.sleep(2)


# ---------------- PACKET NAVIGATION ----------------

def select_packet1():

    import pyautogui
    pyautogui.press("tab")
    pyautogui.hotkey("ctrl", "home")

    for _ in range(3):
        pyautogui.press("down")
        time.sleep(0.2)


def select_packet2():

    import pyautogui
    pyautogui.hotkey("shift", "tab")

    for _ in range(4):
        pyautogui.press("down")
        time.sleep(0.2)

    pyautogui.press("tab")

    for _ in range(5):
        pyautogui.press("down")
        time.sleep(0.2)


def expand_ssh_protocol():

    import pyautogui
    pyautogui.press("tab")

    for _ in range(6):
        pyautogui.press("down")

    pyautogui.press("right")


def expand_ssh_version_2():

    import pyautogui
    pyautogui.press("down")
    pyautogui.press("right")

    for _ in range(3):
        pyautogui.press("down")


# ---------------- CLI PACKET CAPTURE ----------------

def open_capture_terminal(interface):

    launch_terminal("SSH_CAPTURE")

    focus_window("SSH_CAPTURE")

    maximize_terminal()

    import pyautogui
    pyautogui.typewrite(
        f'tshark -i {interface} '
        f'-f "tcp port 22" '
        f'-Y "ssh.message_code == 20" '
        f'-T fields '
        f'-e frame.number '
        f'-e _ws.col.Info '
        f'-e ssh.kex_algorithms\n',
        interval=0
    )

    time.sleep(4)


# ---------------- SSH CLIENT ----------------

def open_ssh_terminal(user, ip):

    launch_terminal("SSH_CLIENT")

    focus_window("SSH_CLIENT")

    maximize_terminal()

    time.sleep(1)
    import pyautogui
    pyautogui.press("enter")
    time.sleep(0.5)

    pyautogui.typewrite(f"ssh {user}@{ip}\n", interval=0.05)

    time.sleep(6)

    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(0.5)

    pyautogui.typewrite("exit\n", interval=0.05)

    time.sleep(2)
    pyautogui.press("enter")
    pyautogui.typewrite("exit\n", interval=0.05)

    time.sleep(1)


# ---------------- CRYPTO EXTRACTION ----------------

def extract_ssh_crypto(user, ip):

    result = subprocess.run(
        ["ssh", "-vv", f"{user}@{ip}", "exit"],
        capture_output=True,
        text=True
    )

    data = result.stderr

    def grab(pattern, default="Not Found"):

        m = re.search(pattern, data)

        return m.group(1).strip() if m else default

    return {
        "protocol": grab(r"Remote protocol version ([0-9.]+)"),
        "cipher": grab(r"server->client cipher: ([^\s]+)"),
        "kex": grab(r"kex: algorithm: ([^\s]+)"),
        "host_key": grab(r"host key algorithm: ([^\s]+)")
    }


# ---------------- VALIDATION ----------------

WEAK_ENCRYPTION = ["des","3des","rc4","arcfour","blowfish","cast128","idea","null","none","export"]

WEAK_KEX = ["diffie-hellman-group1","diffie-hellman-group14-sha1","group-exchange-sha1"]

WEAK_HOST_KEY = ["ssh-dss","rsa1024","rsa512"]


def contains_weak(value, weak_list):

    if not value or value == "Not Found":
        return True

    v = value.lower()

    return any(w in v for w in weak_list)


def nist_validate(crypto):

    results = {}

    results["protocol"] = "PASS" if crypto.get("protocol") == "2.0" else "FAIL"

    results["encryption"] = "FAIL" if contains_weak(crypto.get("cipher"), WEAK_ENCRYPTION) else "PASS"

    results["kex"] = "FAIL" if contains_weak(crypto.get("kex"), WEAK_KEX) else "PASS"

    results["host_key"] = "FAIL" if contains_weak(crypto.get("host_key"), WEAK_HOST_KEY) else "PASS"

    final_result = "PASS" if all(v == "PASS" for v in results.values()) else "FAIL"

    return results, final_result


# ---------------- MAIN SCANNER ----------------

def run_ssh_verification(context):

    user = context.ssh_user
    ip = context.ssh_ip
    interface = context.interface


    ssh_test_data = {
        "test_case_id": "TC1_PROTECT_DATA_INFO_TRANSFER_USING_SSH",
        "user_input": f"ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa {user}@{ip}",
        "terminal_output": "",
        "crypto_details": {},
        "nist_validation": {},
        "final_result": "",
        "screenshots": [],
        "pcap_file": ""
    }


    # Phase 1
    ssh_test_data["terminal_output"] = capture_ssh_terminal_output(user, ip)


    # Phase 2
    pcap_file = launch_wireshark(interface)

    focus_window("wireshark")

    apply_ssh_filter()

    open_capture_terminal(interface)

    open_ssh_terminal(user, ip)

    focus_window("SSH_CAPTURE")

    ssh_test_data["screenshots"].append(
        take_screenshot("cli_packet_capture")
    )

    close_terminal()

    focus_window("wireshark")

    select_packet1()
    expand_ssh_protocol()
    expand_ssh_version_2()

    ssh_test_data["screenshots"].append(
        take_screenshot("ssh_key_exchange_version_2")
    )

    select_packet2()

    ssh_test_data["screenshots"].append(
        take_screenshot("ssh_encrypted_packet")
    )


    # Phase 3
    crypto = extract_ssh_crypto(user, ip)

    validation, final_result = nist_validate(crypto)

    ssh_test_data["crypto_details"] = crypto
    ssh_test_data["nist_validation"] = validation
    ssh_test_data["final_result"] = final_result


    ssh_only_pcap = pcap_file.replace("full_capture", "ssh_only_capture")

    subprocess.run([
        "tshark",
        "-r", pcap_file,
        "-Y", "ssh",
        "-w", ssh_only_pcap
    ])

    ssh_test_data["pcap_file"] = ssh_only_pcap

    subprocess.run(["pkill", "-f", "wireshark"])

    return ssh_test_data