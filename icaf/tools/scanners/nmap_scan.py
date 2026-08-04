import subprocess
import time
import shutil
from datetime import datetime
import os

# pyautogui is imported lazily inside functions that need it,
# so that importing this module does not require a live X display.


# ---------------- TERMINAL CONTROL ----------------

def launch_terminal():
    subprocess.Popen(["gnome-terminal"])
    time.sleep(3)


def focus_terminal():
    subprocess.run(["wmctrl", "-xa", "gnome-terminal"])
    time.sleep(1)


def maximize_terminal():
    import pyautogui
    pyautogui.hotkey("alt", "f10")
    time.sleep(1)


def run_visible_command(command):
    import pyautogui
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(0.5)
    pyautogui.typewrite(command + "\n", interval=0.03)


def exit_terminal():
    import pyautogui
    pyautogui.typewrite("exit\n", interval=0.05)
    time.sleep(1)


# ---------------- BACKEND EXECUTION ----------------

def run_nmap_backend(DUT_IP):
    if not shutil.which("nmap"):
        return None

    result = subprocess.run(
        [
            "nmap",
            "-p22,80,443",   # Only required ports
            "-Pn",           # Skip host discovery
            "-n",            # Disable DNS resolution
            "--open",
            DUT_IP
        ],
        capture_output=True,
        text=True
    )

    return result.stdout


# ---------------- MAIN FUNCTION ----------------

def run_nmap_scan(context):
    import pyautogui

    DUT_IP = context.ssh_ip

    scan_data = {
        "test_case_id": "TC_DUT_CONFIGURATION_NMAP_SCAN",
        "user_input": f"nmap -p22,80,443 -Pn -n --open {DUT_IP}",
        "terminal_output": "",
        "screenshot": ""
    }

    try:
        launch_terminal()
        focus_terminal()
        maximize_terminal()

        # Visible command for screenshot
        run_visible_command(scan_data["user_input"])

        # Scan is now very fast
        time.sleep(3)

        # Backend scan
        output = run_nmap_backend(DUT_IP)

        scan_data["terminal_output"] = (
            output if output else "No output captured"
        )

        # Screenshot capture
        screenshot_name = (
            f"nmap_terminal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )

        pyautogui.screenshot(screenshot_name)
        scan_data["screenshot"] = screenshot_name

    finally:
        exit_terminal()

    return scan_data
