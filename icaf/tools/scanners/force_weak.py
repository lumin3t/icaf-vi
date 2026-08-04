import subprocess
import time
# pyautogui imported lazily inside functions (avoids X display error at import time)
import os
from datetime import datetime


SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# ---------------- TERMINAL CONTROL ----------------

def launch_terminal():
    subprocess.Popen(["gnome-terminal"])
    time.sleep(4)


def focus_terminal():
    subprocess.run(["wmctrl", "-xa", "gnome-terminal"])
    time.sleep(1)


def maximize_terminal():
    import pyautogui
    pyautogui.hotkey("alt", "f10")
    time.sleep(1)


def close_terminal():
    import pyautogui
    pyautogui.typewrite("exit\n", interval=0.05)
    time.sleep(1)


# ---------------- SCREENSHOT ----------------

def take_screenshot(label):

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    path = f"{SCREENSHOT_DIR}/{ts}_{label}.png"

    import pyautogui
    pyautogui.screenshot(path)

    return path


# ---------------- NEGOTIATION DETECTION ----------------

def check_negotiation(command, algo):

    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True
    )

    output = result.stdout.lower()

    if "no match" in output:
        return False

    if algo.lower() in output:
        return True

    return False


# ---------------- MAIN FUNCTION ----------------

def run_ssh_weak_cipher_test(context, cipher_test_data):

    user = context.ssh_user
    ip = context.ssh_ip

    test_data = {
        "test_case_id": "TC_SSH_WEAK_NEGOTIATION",
        "results": [],
        "screenshots": []
    }

    weak_ciphers = cipher_test_data["details"]["encryption"].get("weak", [])
    weak_macs = cipher_test_data["details"]["mac"].get("weak", [])
    weak_kex = cipher_test_data["details"]["kex"].get("weak", [])
    weak_host = cipher_test_data["details"]["host_key"].get("weak", [])


    # ---------------- WEAK CIPHER TEST ----------------

    for cipher in weak_ciphers:

        cmd = f"ssh -vv -o BatchMode=no -o Ciphers={cipher} {user}@{ip} exit 2>&1 | grep 'debug1: kex:'"

        launch_terminal()
        focus_terminal()
        maximize_terminal()

        time.sleep(1)
        import pyautogui
        pyautogui.press("enter")
        time.sleep(0.5)

        pyautogui.typewrite(cmd + "\n", interval=0.03)

        time.sleep(6)

        screenshot = take_screenshot(f"weak_cipher_{cipher}")

        close_terminal()

        negotiated = check_negotiation(cmd, cipher)

        test_data["results"].append({
            "type": "cipher",
            "algorithm": cipher,
            "command": cmd,
            "negotiated": negotiated
        })

        test_data["screenshots"].append(screenshot)

        if negotiated:
            return test_data


    # ---------------- WEAK MAC TEST ----------------

    for mac in weak_macs:

        cmd = f"ssh -vv -o BatchMode=no -o Ciphers=aes128-ctr -o MACs={mac} {user}@{ip} exit 2>&1 | grep 'debug1: kex:'"

        launch_terminal()
        focus_terminal()
        maximize_terminal()

        time.sleep(1)
        pyautogui.press("enter")
        time.sleep(0.5)

        pyautogui.typewrite(cmd + "\n", interval=0.03)

        time.sleep(6)

        screenshot = take_screenshot(f"weak_mac_{mac}")

        close_terminal()

        negotiated = check_negotiation(cmd, mac)

        test_data["results"].append({
            "type": "mac",
            "algorithm": mac,
            "command": cmd,
            "negotiated": negotiated
        })

        test_data["screenshots"].append(screenshot)

        if negotiated:
            return test_data


    # ---------------- WEAK KEX TEST ----------------

    for kex in weak_kex:

        cmd = f"ssh -vv -o BatchMode=no -o KexAlgorithms={kex} {user}@{ip} exit 2>&1 | grep 'debug1: kex:'"

        launch_terminal()
        focus_terminal()
        maximize_terminal()

        time.sleep(1)
        pyautogui.press("enter")
        time.sleep(0.5)

        pyautogui.typewrite(cmd + "\n", interval=0.03)

        time.sleep(6)

        screenshot = take_screenshot(f"weak_kex_{kex}")

        close_terminal()

        negotiated = check_negotiation(cmd, kex)

        test_data["results"].append({
            "type": "kex",
            "algorithm": kex,
            "command": cmd,
            "negotiated": negotiated
        })

        test_data["screenshots"].append(screenshot)

        if negotiated:
            return test_data


    # ---------------- WEAK HOST KEY TEST ----------------

    for host in weak_host:

        cmd = f"ssh -vv -o BatchMode=no -o HostKeyAlgorithms={host} {user}@{ip} exit 2>&1 | grep 'debug1: kex:'"

        launch_terminal()
        focus_terminal()
        maximize_terminal()

        time.sleep(1)
        pyautogui.press("enter")
        time.sleep(0.5)

        pyautogui.typewrite(cmd + "\n", interval=0.03)

        time.sleep(6)

        screenshot = take_screenshot(f"weak_hostkey_{host}")

        close_terminal()

        negotiated = check_negotiation(cmd, host)

        test_data["results"].append({
            "type": "host_key",
            "algorithm": host,
            "command": cmd,
            "negotiated": negotiated
        })

        test_data["screenshots"].append(screenshot)

        if negotiated:
            return test_data


    return test_data