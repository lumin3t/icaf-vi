import subprocess
import time
# pyautogui imported lazily inside functions (avoids X display error at import time)
import shutil
from datetime import datetime


# ---------------- WEAK CRYPTO DEFINITIONS ----------------

WEAK_ENCRYPTION = [
    "des","3des","rc4","arcfour","blowfish","cast128","idea","null","none","export"
]

WEAK_MAC = [
    "md5","hmac-md5","sha1","hmac-sha1"
]

WEAK_KEX = [
    "diffie-hellman-group1",
    "diffie-hellman-group14-sha1",
    "group-exchange-sha1"
]

WEAK_HOST_KEY = [
    "ssh-dss","rsa1024","rsa512"
]


# ---------------- TERMINAL ----------------

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


def run_visible_nmap(command):
    time.sleep(1)
    import pyautogui
    pyautogui.press("enter")
    time.sleep(0.5)
    pyautogui.typewrite(command + "\n", interval=0.03)


# ---------------- BACKEND ----------------

def run_nmap_backend(ip):

    if not shutil.which("nmap"):
        return None

    result = subprocess.run(
        [
            "nmap",
            "-p22",
            "--script", "ssh2-enum-algos",
            "-Pn",
            "-n",
            ip
        ],
        capture_output=True,
        text=True
    )

    return result.stdout


# ---------------- PARSER ----------------

def extract_section(output, section_name):

    values = []
    capture = False

    for line in output.splitlines():

        stripped = line.strip().lower()

        if stripped.startswith(f"|   {section_name}:"):
            capture = True
            continue

        if capture and stripped.startswith("|   ") and "_algorithms:" in stripped and section_name not in stripped:
            break

        if capture and stripped.startswith("|       "):

            val = stripped.replace("|", "").strip()

            if val:
                values.append(val)

    return values


# ---------------- CLASSIFICATION ----------------

def classify(items, weak_keywords):

    strong = []
    weak = []

    for item in items:

        if any(w in item for w in weak_keywords):
            weak.append(item)
        else:
            strong.append(item)

    return strong, weak


# ---------------- MAIN SCANNER ----------------

def run_cipher_detection(context):

    ip = context.ssh_ip

    cipher_test_data = {
        "test_case_id": "TC1_SSH_CRYPTO_HARDENING",
        "user_input": f"nmap -p22 --script ssh2-enum-algos -Pn -n {ip}",
        "terminal_output": "",
        "result": "",
        "details": {
            "encryption": {},
            "mac": {},
            "kex": {},
            "host_key": {}
        },
        "screenshot": ""
    }

    launch_terminal()
    focus_terminal()
    maximize_terminal()

    run_visible_nmap(cipher_test_data["user_input"])

    time.sleep(6)

    output = run_nmap_backend(ip)

    cipher_test_data["terminal_output"] = output

    if not output:
        cipher_test_data["result"] = "FAIL"
        return cipher_test_data


    encryption = extract_section(output, "encryption_algorithms")
    mac = extract_section(output, "mac_algorithms")
    kex = extract_section(output, "kex_algorithms")
    host_key = extract_section(output, "server_host_key_algorithms")


    enc_strong, enc_weak = classify(encryption, WEAK_ENCRYPTION)
    mac_strong, mac_weak = classify(mac, WEAK_MAC)
    kex_strong, kex_weak = classify(kex, WEAK_KEX)
    hk_strong, hk_weak = classify(host_key, WEAK_HOST_KEY)


    cipher_test_data["details"]["encryption"] = {
        "strong": enc_strong,
        "weak": enc_weak
    }

    cipher_test_data["details"]["mac"] = {
        "strong": mac_strong,
        "weak": mac_weak
    }

    cipher_test_data["details"]["kex"] = {
        "strong": kex_strong,
        "weak": kex_weak
    }

    cipher_test_data["details"]["host_key"] = {
        "strong": hk_strong,
        "weak": hk_weak
    }


    cipher_test_data["result"] = (
        "FAIL" if (enc_weak or mac_weak or kex_weak or hk_weak) else "PASS"
    )


    screenshot_name = f"cipher_terminal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    import pyautogui
    pyautogui.screenshot(screenshot_name)

    cipher_test_data["screenshot"] = screenshot_name


    pyautogui.typewrite("exit\n", interval=0.05)

    time.sleep(1)

    return cipher_test_data