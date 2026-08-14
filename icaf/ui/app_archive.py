"""A colorful, modern, highly stylized desktop interface for running ICAF checks."""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from icaf.config.settings import initialize_directories, settings
from icaf.core.engine import Engine
from icaf.utils.logger import logger

CLAUSES = {
    "1.1.1": "Secure Management Protocols",
    "1.2.4": "Password Policy Compliance",
    "1.6.1": "Network Security",
    "1.6.5": "Secure Remote Access",
}

# Theme Palette (Vibrant Dark Theme)
COLORS = {
    "bg_dark": "#12131C",
    "bg_card": "#1E1F2E",
    "bg_input": "#2A2B3D",
    "fg_text": "#F1F2F6",
    "fg_muted": "#8E94A7",
    "border": "#3A3C52",
    # Button Colors
    "btn_primary": "#00E676",
    "btn_primary_hover": "#33ECA0",
    "btn_primary_fg": "#091D11",
    "btn_sec": "#6C5CE7",
    "btn_sec_hover": "#81ECEC",
    "btn_sec_fg": "#FFFFFF",
    # Status Colors
    "success": "#00E676",
    "warning": "#FFB300",
    "error": "#FF5252",
}


class RoundedButton(tk.Canvas):
    """Custom high-style rounded button with smooth hover effects."""

    def __init__(
        self,
        parent,
        text: str,
        command=None,
        bg_color: str = COLORS["btn_primary"],
        hover_color: str = COLORS["btn_primary_hover"],
        fg_color: str = COLORS["btn_primary_fg"],
        container_bg: str | None = None,
        width: int = 220,
        height: int = 44,
        radius: int = 12,
        font=("Segoe UI", 10, "bold"),
    ):
        # Safely resolve parent container background color (handles ttk frames gracefully)
        if container_bg is None:
            try:
                container_bg = parent.cget("bg")
            except (AttributeError, tk.TclError):
                container_bg = COLORS["bg_card"]

        super().__init__(
            parent,
            width=width,
            height=height,
            bg=container_bg,
            highlightthickness=0,
            cursor="hand2",
        )
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.fg_color = fg_color
        self.radius = radius
        self.btn_text = text
        self.font = font
        self.enabled = True

        self._draw(self.bg_color)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw_round_rect(self, x1, y1, x2, y2, r, fill):
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.create_polygon(points, fill=fill, smooth=True)

    def _draw(self, color: str):
        self.delete("all")
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self._draw_round_rect(2, 2, w - 2, h - 2, self.radius, fill=color)
        self.create_text(
            w / 2, h / 2, text=self.btn_text, fill=self.fg_color, font=self.font
        )

    def _on_enter(self, _):
        if self.enabled:
            self._draw(self.hover_color)

    def _on_leave(self, _):
        if self.enabled:
            self._draw(self.bg_color)

    def _on_click(self, _):
        if self.enabled and self.command:
            self.command()

    def set_state(self, enabled: bool):
        self.enabled = enabled
        if enabled:
            self.configure(cursor="hand2")
            self._draw(self.bg_color)
        else:
            self.configure(cursor="arrow")
            self._draw(COLORS["border"])


class QueueLogHandler(logging.Handler):
    def __init__(self, log_queue: queue.Queue[tuple[str, str]]):
        super().__init__()
        self.log_queue = log_queue
        self.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        self.log_queue.put((self.format(record), record.levelname))


class ICAFApp(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.log_handler = QueueLogHandler(self.log_queue)
        self.running = False

        master.title("ICAF Compliance Suite")
        master.minsize(840, 700)
        master.configure(bg=COLORS["bg_dark"])

        self._apply_theme()
        self.pack(fill="both", expand=True, padx=24, pady=24)

        self._make_variables()
        self._build_header()
        self._build_form()
        self._build_log_viewer()
        self._set_clause_fields()
        self._poll_logs()

    def _apply_theme(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=COLORS["bg_dark"], foreground=COLORS["fg_text"], font=("Segoe UI", 10))
        style.configure("TFrame", background=COLORS["bg_dark"])
        style.configure("Card.TFrame", background=COLORS["bg_card"], relief="flat")

        style.configure("TLabel", background=COLORS["bg_dark"], foreground=COLORS["fg_text"])
        style.configure("Card.TLabel", background=COLORS["bg_card"], foreground=COLORS["fg_text"])
        style.configure("Muted.TLabel", background=COLORS["bg_card"], foreground=COLORS["fg_muted"], font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=COLORS["bg_dark"], foreground=COLORS["fg_text"], font=("Segoe UI", 20, "bold"))
        style.configure("SubHeader.TLabel", background=COLORS["bg_dark"], foreground=COLORS["fg_muted"], font=("Segoe UI", 10))

        style.configure("TLabelframe", background=COLORS["bg_card"], bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"], borderwidth=1)
        style.configure("TLabelframe.Label", background=COLORS["bg_card"], foreground=COLORS["btn_primary"], font=("Segoe UI", 11, "bold"))

        style.configure("TEntry", fieldbackground=COLORS["bg_input"], foreground=COLORS["fg_text"], insertcolor=COLORS["fg_text"], borderwidth=1, relief="flat")
        style.map("TEntry", fieldbackground=[("active", COLORS["bg_input"])])

        style.configure("TCombobox", fieldbackground=COLORS["bg_input"], background=COLORS["bg_input"], foreground=COLORS["fg_text"], arrowcolor=COLORS["btn_primary"], borderwidth=1)
        style.map("TCombobox", fieldbackground=[("readonly", COLORS["bg_input"])], selectbackground=[("readonly", COLORS["bg_input"])], selectforeground=[("readonly", COLORS["fg_text"])])

    def _make_variables(self) -> None:
        self.clause = tk.StringVar(value="1.6.5")
        self.profile = tk.StringVar(value="default")
        self.ssh_ip = tk.StringVar(value="10.80.127.211")
        self.ssh_user = tk.StringVar(value="dut")
        self.ssh_password = tk.StringVar()
        self.snmp_user = tk.StringVar(value="snmpuser")
        self.snmp_auth_pass = tk.StringVar()
        self.snmp_priv_pass = tk.StringVar()
        self.snmp_community = tk.StringVar(value="community")
        self.web_login_url = tk.StringVar()
        self.web_username = tk.StringVar(value="admin")
        self.web_password = tk.StringVar()
        self.oam_path = tk.StringVar()
        self.status = tk.StringVar(value="Ready to execute checks")

    def _build_header(self) -> None:
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", pady=(0, 18))

        ttk.Label(header_frame, text="ICAF Compliance Check", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header_frame,
            text="Automated security, policy, and protocol verification framework.",
            style="SubHeader.TLabel",
        ).pack(anchor="w")

    def _build_form(self) -> None:
        form = ttk.LabelFrame(self, text=" Session Parameters ", padding=16)
        form.pack(fill="x", pady=(0, 16))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        self._field(form, "Compliance Clause", ttk.Combobox(
            form, textvariable=self.clause, values=list(CLAUSES), state="readonly", width=22
        ), 0, 0)
        self.clause.trace_add("write", lambda *_: self._set_clause_fields())

        self._field(form, "DUT Profile", ttk.Combobox(
            form, textvariable=self.profile, values=self._profiles(), width=22
        ), 0, 2)

        self._field(form, "Device IP / Hostname", ttk.Entry(form, textvariable=self.ssh_ip), 1, 0)
        self._field(form, "SSH Username", ttk.Entry(form, textvariable=self.ssh_user), 1, 2)
        self._field(form, "SSH Password", ttk.Entry(form, textvariable=self.ssh_password, show="•"), 2, 0)

        # Extended Clause Options Card
        self.optional_frame = ttk.Frame(form, style="Card.TFrame", padding=12)
        self.optional_frame.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        self.optional_frame.columnconfigure(1, weight=1)
        self.optional_frame.columnconfigure(3, weight=1)

        ttk.Label(
            self.optional_frame,
            text="SNMP & Web Portal Configuration (Clause 1.1.1 Specific)",
            style="Muted.TLabel",
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        self._field(self.optional_frame, "SNMPv3 User", ttk.Entry(self.optional_frame, textvariable=self.snmp_user), 1, 0, card=True)
        self._field(self.optional_frame, "SNMP Auth Pass", ttk.Entry(self.optional_frame, textvariable=self.snmp_auth_pass, show="•"), 1, 2, card=True)
        self._field(self.optional_frame, "SNMP Priv Pass", ttk.Entry(self.optional_frame, textvariable=self.snmp_priv_pass, show="•"), 2, 0, card=True)
        self._field(self.optional_frame, "SNMP Community", ttk.Entry(self.optional_frame, textvariable=self.snmp_community), 2, 2, card=True)
        self._field(self.optional_frame, "Web Login URL", ttk.Entry(self.optional_frame, textvariable=self.web_login_url), 3, 0, card=True)
        self._field(self.optional_frame, "Web Username", ttk.Entry(self.optional_frame, textvariable=self.web_username), 3, 2, card=True)
        self._field(self.optional_frame, "Web Password", ttk.Entry(self.optional_frame, textvariable=self.web_password, show="•"), 4, 0, card=True)

        # File Chooser
        oam = ttk.Frame(form)
        oam.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        oam.columnconfigure(1, weight=1)

        ttk.Label(oam, text="OAM Excel File").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Entry(oam, textvariable=self.oam_path).grid(row=0, column=1, sticky="ew")

        # Browse Button (Custom Stylized)
        self.browse_btn = RoundedButton(
            oam,
            text="📁 Browse...",
            command=self._choose_oam,
            bg_color=COLORS["btn_sec"],
            hover_color=COLORS["btn_sec_hover"],
            fg_color=COLORS["btn_sec_fg"],
            container_bg=COLORS["bg_card"],
            width=100,
            height=32,
            radius=8,
            font=("Segoe UI", 9, "bold"),
        )
        self.browse_btn.grid(row=0, column=2, padx=(10, 0))

        # Controls & Status Container
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(8, 16))

        # Primary Execute Button
        self.run_button = RoundedButton(
            actions,
            text="▶   START CHECK",
            command=self._start_run,
            bg_color=COLORS["btn_primary"],
            hover_color=COLORS["btn_primary_hover"],
            fg_color=COLORS["btn_primary_fg"],
            container_bg=COLORS["bg_dark"],
            width=250,
            height=46,
            radius=12,
            font=("Segoe UI", 10, "bold"),
        )
        self.run_button.pack(side="left")

        self.status_label = ttk.Label(actions, textvariable=self.status, foreground=COLORS["fg_muted"], font=("Segoe UI", 10))
        self.status_label.pack(side="left", padx=20)

    def _build_log_viewer(self) -> None:
        logs = ttk.LabelFrame(self, text=" Live Diagnostics Console ", padding=8)
        logs.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            logs,
            height=12,
            state="disabled",
            wrap="word",
            font=("Consolas", 9),
            bg=COLORS["bg_dark"],
            fg=COLORS["fg_text"],
            insertbackground=COLORS["fg_text"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )

        self.log_text.tag_config("INFO", foreground=COLORS["success"])
        self.log_text.tag_config("WARNING", foreground=COLORS["warning"])
        self.log_text.tag_config("ERROR", foreground=COLORS["error"])
        self.log_text.tag_config("CRITICAL", foreground=COLORS["error"], font=("Consolas", 9, "bold"))

        scrollbar = ttk.Scrollbar(logs, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    @staticmethod
    def _field(parent: ttk.Widget, label: str, widget: ttk.Widget, row: int, column: int, card: bool = False) -> None:
        lbl_style = "Card.TLabel" if card else "TLabel"
        ttk.Label(parent, text=label, style=lbl_style).grid(row=row, column=column, sticky="w", padx=(0, 8), pady=6)
        widget.grid(row=row, column=column + 1, sticky="ew", padx=(0, 16), pady=6)

    @staticmethod
    def _profiles() -> list[str]:
        profile_dir = settings.BASE_DIR / "icaf" / "profile"
        return sorted(path.stem for path in profile_dir.glob("*.yaml")) or ["default"]

    def _set_clause_fields(self) -> None:
        if self.clause.get() == "1.1.1":
            self.optional_frame.grid()
            if not self.web_login_url.get():
                self.web_login_url.set(f"http://{self.ssh_ip.get()}/dvwa/login.php")
        else:
            self.optional_frame.grid_remove()

    def _choose_oam(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose OAM Excel file", filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if selected:
            self.oam_path.set(selected)

    def _start_run(self) -> None:
        if self.running:
            return
        if not self.ssh_ip.get().strip() or not self.ssh_user.get().strip():
            messagebox.showerror("Missing Fields", "Device IP / hostname and SSH username are required.")
            return
        if self.oam_path.get() and not Path(self.oam_path.get()).is_file():
            messagebox.showerror("File Error", "Choose a valid OAM Excel file or clear this field.")
            return

        self.running = True
        self.run_button.set_state(False)
        self.status.set("⏳ Running compliance engine...")
        self.status_label.configure(foreground=COLORS["warning"])

        self._write_log("Starting compliance test suite...", "INFO")

        values = {
            "clause": self.clause.get(),
            "profile": self.profile.get().strip() or "default",
            "ssh_user": self.ssh_user.get().strip(),
            "ssh_ip": self.ssh_ip.get().strip(),
            "ssh_password": self.ssh_password.get(),
            "snmp_user": self.snmp_user.get(),
            "snmp_auth_pass": self.snmp_auth_pass.get(),
            "snmp_priv_pass": self.snmp_priv_pass.get(),
            "snmp_community": self.snmp_community.get(),
            "web_login_url": self.web_login_url.get(),
            "web_username": self.web_username.get(),
            "web_password": self.web_password.get(),
            "oam_path": self.oam_path.get(),
        }
        threading.Thread(target=self._run_engine, args=(values,), daemon=True).start()

    def _run_engine(self, values: dict[str, str]) -> None:
        logger.addHandler(self.log_handler)
        try:
            initialize_directories()
            clause = values["clause"]
            engine = Engine(
                clause=clause,
                profile=values["profile"],
                ssh_user=values["ssh_user"],
                ssh_ip=values["ssh_ip"],
                ssh_password=values["ssh_password"],
                snmp_user=values["snmp_user"] if clause == "1.1.1" else None,
                snmp_auth_pass=values["snmp_auth_pass"] if clause == "1.1.1" else None,
                snmp_priv_pass=values["snmp_priv_pass"] if clause == "1.1.1" else None,
                snmp_community=values["snmp_community"] if clause == "1.1.1" else None,
                web_login_url=values["web_login_url"] if clause == "1.1.1" else None,
                web_username=values["web_username"] if clause == "1.1.1" else None,
                web_password=values["web_password"] if clause == "1.1.1" else None,
                oam_context=self._load_oam(values),
            )
            engine.start()
        except Exception as exc:
            logger.exception("Compliance check failed")
            self.master.after(0, lambda: self._finished(False, str(exc)))
        else:
            self.master.after(0, lambda: self._finished(True))
        finally:
            logger.removeHandler(self.log_handler)

    def _load_oam(self, values: dict[str, str]):
        if not values["oam_path"]:
            return None
        from icaf.oam.oam_manager import process_oam
        return process_oam(values["oam_path"], values["ssh_ip"])

    def _finished(self, success: bool, error: str = "") -> None:
        self.running = False
        self.run_button.set_state(True)
        if success:
            self.status.set("✔ Checks completed successfully!")
            self.status_label.configure(foreground=COLORS["success"])
            messagebox.showinfo("Execution Complete", f"Check complete. Report saved to:\n{settings.REPORT_DIR}")
        else:
            self.status.set("✖ Execution terminated on error.")
            self.status_label.configure(foreground=COLORS["error"])
            messagebox.showerror("Execution Failed", f"The check could not complete.\n\n{error}")

    def _poll_logs(self) -> None:
        while True:
            try:
                msg, level = self.log_queue.get_nowait()
                self._write_log(msg, level)
            except queue.Empty:
                break
        self.master.after(100, self._poll_logs)

    def _write_log(self, message: str, level: str = "INFO") -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n", level)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


def main() -> None:
    root = tk.Tk()
    ICAFApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()