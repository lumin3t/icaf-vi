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


# ---------------- PHASE 1 ----------------

def capture_tls_terminal_output(ip):

    result = subprocess.run(
        ["openssl", "s_client", "-connect", f"{ip}:443"],
        capture_output=True,
        text=True,
        input=""
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


def apply_tls_filter():

    import pyautogui
    pyautogui.hotkey("ctrl", "/")

    time.sleep(1)

    pyautogui.typewrite("tls", interval=0.05)

    pyautogui.press("enter")

    time.sleep(2)


# ---------------- PACKET NAVIGATION ----------------

def select_packet():

    import pyautogui
    pyautogui.press("tab")

    pyautogui.hotkey("ctrl", "home")

    time.sleep(0.3)

    pyautogui.press("down")

    pyautogui.press("tab")

    for _ in range(4):
        pyautogui.press("down")

    pyautogui.press("right")

    pyautogui.press("down")

    pyautogui.press("right")

    for _ in range(4):
        pyautogui.press("down")

    pyautogui.press("right")

    for _ in range(7):
        pyautogui.press("down")


# ---------------- CAPTURE TERMINAL ----------------

def open_capture_terminal(interface):

    launch_terminal("TLS_CAPTURE")

    focus_window("TLS_CAPTURE")

    maximize_terminal()

    time.sleep(1)
    import pyautogui
    pyautogui.press("enter")
    pyautogui.typewrite(
        f'tshark -i {interface} '
        f'-f "tcp port 443" '
        f'-Y "tls" '
        f'-T fields '
        f'-e frame.number '
        f'-e _ws.col.Info '
        f'-e tls.handshake.ciphersuite\n',
        interval=0
    )

    time.sleep(4)


# ---------------- TLS CLIENT ----------------

def open_tls_terminal(ip):

    launch_terminal("TLS_CLIENT")

    focus_window("TLS_CLIENT")

    maximize_terminal()

    time.sleep(1)
    import pyautogui
    pyautogui.press("enter")
    pyautogui.typewrite(
        f"openssl s_client -connect {ip}:443\n",
        interval=0.05
    )

    time.sleep(6)

    pyautogui.hotkey("ctrl", "c")

    time.sleep(1)

    pyautogui.typewrite("exit\n", interval=0.05)

    time.sleep(1)


# ---------------- CRYPTO EXTRACTION ----------------

def extract_tls_crypto(ip):

    result = subprocess.run(
        ["openssl", "s_client", "-connect", f"{ip}:443"],
        capture_output=True,
        text=True,
        input=""
    )

    data = result.stdout

    protocol = "Not Found"
    cipher = "Not Found"

    match = re.search(
        r"New,\s*(TLSv[0-9.]+),\s*Cipher is\s*([A-Z0-9_\-]+)",
        data
    )

    if match:
        protocol = match.group(1)
        cipher = match.group(2)

    return {
        "protocol": protocol,
        "cipher": cipher
    }


# ---------------- VALIDATION ----------------

WEAK_TLS = ["des", "3des", "rc4", "null", "export"]


def contains_weak(value, weak_list):

    if not value or value == "Not Found":
        return True

    v = value.lower()

    return any(w in v for w in weak_list)


def tls_validate(crypto):

    results = {}

    results["protocol"] = (
        "PASS" if crypto.get("protocol") in ["TLSv1.2", "TLSv1.3"] else "FAIL"
    )

    results["cipher"] = (
        "FAIL" if contains_weak(crypto.get("cipher"), WEAK_TLS) else "PASS"
    )

    final_result = (
        "PASS" if all(v == "PASS" for v in results.values()) else "FAIL"
    )

    return results, final_result


# ---------------- MAIN SCANNER ----------------

def run_tls_verification(context):

    ip = context.ssh_ip
    interface = context.interface

    tls_test_data = {
        "test_case_id": "TC2_PROTECT_DATA_INFO_TRANSFER_USING_HTTPS",
        "user_input": f"openssl s_client -connect {ip}:443",
        "terminal_output": "",
        "crypto_details": {},
        "nist_validation": {},
        "final_result": "",
        "screenshots": [],
        "pcap_file": ""
    }


    # Phase 1
    tls_test_data["terminal_output"] = capture_tls_terminal_output(ip)


    # Phase 2
    pcap_file = launch_wireshark(interface)

    focus_window("wireshark")

    apply_tls_filter()

    open_capture_terminal(interface)

    open_tls_terminal(ip)

    focus_window("TLS_CAPTURE")

    tls_test_data["screenshots"].append(
        take_screenshot("cli_tls_capture")
    )

    close_terminal()

    focus_window("wireshark")

    select_packet()

    tls_test_data["screenshots"].append(
        take_screenshot("tls_server_hello_packet")
    )


    # Phase 3
    crypto = extract_tls_crypto(ip)

    validation, final_result = tls_validate(crypto)

    tls_test_data["crypto_details"] = crypto
    tls_test_data["nist_validation"] = validation
    tls_test_data["final_result"] = final_result


    tls_only_pcap = pcap_file.replace("full_capture", "tls_only_capture")

    subprocess.run([
        "tshark",
        "-r", pcap_file,
        "-Y", "tls",
        "-w", tls_only_pcap
    ])

    tls_test_data["pcap_file"] = tls_only_pcap

    subprocess.run(["pkill", "-f", "wireshark"])

    return tls_test_data