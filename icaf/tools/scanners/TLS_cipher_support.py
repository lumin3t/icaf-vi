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
    "rsa","dh_anon"
]

WEAK_HOST_KEY = [
    "rsa1024","rsa512"
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
    time.sleep(2)
    import pyautogui
    pyautogui.press("enter")
    pyautogui.typewrite(command + "\n", interval=0.03)


# ---------------- BACKEND ----------------

def run_nmap_backend(ip):

    if not shutil.which("nmap"):
        return None

    result = subprocess.run(
        ["nmap", "--script", "ssl-enum-ciphers", "-p", "443", ip],
        capture_output=True,
        text=True
    )

    return result.stdout


# ---------------- HELPERS ----------------

def unique_list(values):

    return list(sorted(set(values)))


# ---------------- TLS PARSER ----------------

def parse_tls_versions(output):

    tls_data = {
        "TLSv1.2": {"encryption": [], "mac": [], "kex": []},
        "TLSv1.3": {"encryption": [], "mac": [], "kex": []}
    }

    current_version = None

    for line in output.splitlines():

        line = line.strip()

        if "TLSv1.2:" in line:
            current_version = "TLSv1.2"
            continue

        if "TLSv1.3:" in line:
            current_version = "TLSv1.3"
            continue

        if "TLS_" in line:

            cipher = line.replace("|", "").strip().split(" ")[0].lower()

            if "_with_" in cipher:

                kex = cipher.split("_with_")[0]
                enc = cipher.split("_with_")[1]
                mac = enc.split("_")[-1]

                tls_data[current_version]["kex"].append(kex)
                tls_data[current_version]["encryption"].append(enc)
                tls_data[current_version]["mac"].append(mac)

            else:

                parts = cipher.split("_")

                enc = "_".join(parts[1:-1])
                mac = parts[-1]

                tls_data[current_version]["kex"].append("tls13")
                tls_data[current_version]["encryption"].append(enc)
                tls_data[current_version]["mac"].append(mac)

    for version in tls_data:

        tls_data[version]["encryption"] = unique_list(
            tls_data[version]["encryption"]
        )

        tls_data[version]["mac"] = unique_list(
            tls_data[version]["mac"]
        )

        tls_data[version]["kex"] = unique_list(
            tls_data[version]["kex"]
        )

    return tls_data


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

def run_httpsCipher_detection(context):

    ip = context.ssh_ip

    cipher_test_data = {
        "test_case_id": "TC1_HTTPS_CRYPTO_HARDENING",
        "user_input": f"nmap --script ssl-enum-ciphers -p 443 {ip}",
        "terminal_output": "",
        "result": "",
        "details": {
            "TLSv1.2": {},
            "TLSv1.3": {},
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


    tls_data = parse_tls_versions(output)


    enc_strong_12, enc_weak_12 = classify(
        tls_data["TLSv1.2"]["encryption"], WEAK_ENCRYPTION
    )

    mac_strong_12, mac_weak_12 = classify(
        tls_data["TLSv1.2"]["mac"], WEAK_MAC
    )

    kex_strong_12, kex_weak_12 = classify(
        tls_data["TLSv1.2"]["kex"], WEAK_KEX
    )


    enc_strong_13, enc_weak_13 = classify(
        tls_data["TLSv1.3"]["encryption"], WEAK_ENCRYPTION
    )

    mac_strong_13, mac_weak_13 = classify(
        tls_data["TLSv1.3"]["mac"], WEAK_MAC
    )

    kex_strong_13, kex_weak_13 = classify(
        tls_data["TLSv1.3"]["kex"], WEAK_KEX
    )


    cipher_test_data["details"]["TLSv1.2"] = {
        "encryption": {"strong": enc_strong_12, "weak": enc_weak_12},
        "mac": {"strong": mac_strong_12, "weak": mac_weak_12},
        "kex": {"strong": kex_strong_12, "weak": kex_weak_12},
    }

    cipher_test_data["details"]["TLSv1.3"] = {
        "encryption": {"strong": enc_strong_13, "weak": enc_weak_13},
        "mac": {"strong": mac_strong_13, "weak": mac_weak_13},
        "kex": {"strong": kex_strong_13, "weak": kex_weak_13},
    }


    cipher_test_data["result"] = (
        "FAIL"
        if (
            enc_weak_12
            or mac_weak_12
            or kex_weak_12
            or enc_weak_13
            or mac_weak_13
            or kex_weak_13
        )
        else "PASS"
    )


    screenshot_name = f"cipher_terminal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    import pyautogui
    pyautogui.screenshot(screenshot_name)

    cipher_test_data["screenshot"] = screenshot_name


    pyautogui.typewrite("exit\n", interval=0.05)

    time.sleep(1)

    return cipher_test_data