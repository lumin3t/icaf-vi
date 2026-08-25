from __future__ import annotations

import logging
import queue
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Import existing backend dependencies
from icaf.config.settings import initialize_directories, settings
from icaf.clauses.catalog import clause_names
from icaf.core.engine import Engine
from icaf.utils.logger import logger

CLAUSES = clause_names()


# ----------------------------------------------------------------------
# QSS Modern Stylesheet (Web-App UI Look & Feel)
# ----------------------------------------------------------------------
STYLESHEET = """
QMainWindow {
    background-color: #0F1017;
}

QWidget {
    font-family: 'Segoe UI', system-ui, sans-serif;
    color: #E2E8F0;
    font-size: 13px;
}

/* Card Container */
QFrame#Card {
    background-color: #181926;
    border: 1px solid #2A2C40;
    border-radius: 12px;
}

/* Section Header Bar */
QFrame#SectionHeader {
    background-color: #12131F;
    border-bottom: 1px solid #2A2C40;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}

/* Input Fields */
QLineEdit, QComboBox {
    background-color: #202234;
    border: 1px solid #32354E;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F8FAFC;
    selection-background-color: #6C5CE7;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #00E676;
    background-color: #25283D;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #181926;
    border: 1px solid #32354E;
    selection-background-color: #6C5CE7;
    selection-color: #FFFFFF;
    outline: none;
}

/* Buttons */
QPushButton#PrimaryButton {
    background-color: #00E676;
    color: #052312;
    font-weight: bold;
    font-size: 14px;
    border-radius: 8px;
    padding: 10px 24px;
    border: none;
}

QPushButton#PrimaryButton:hover {
    background-color: #33ECA0;
}

QPushButton#PrimaryButton:disabled {
    background-color: #2A2C40;
    color: #64748B;
}

QPushButton#SecondaryButton {
    background-color: #2A2C40;
    color: #E2E8F0;
    font-weight: 600;
    border-radius: 8px;
    padding: 8px 16px;
    border: 1px solid #3A3C52;
}

QPushButton#SecondaryButton:hover {
    background-color: #3A3C52;
    border-color: #6C5CE7;
}

/* Console Output */
QTextEdit#ConsoleLog {
    background-color: #0B0C10;
    border: 1px solid #2A2C40;
    border-radius: 10px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
    padding: 10px;
}

/* Labels */
QLabel#FieldLabel {
    color: #94A3B8;
    font-size: 12px;
    font-weight: 600;
}

QLabel#HeaderTitle {
    font-size: 22px;
    font-weight: bold;
    color: #FFFFFF;
}

QLabel#HeaderSubtitle {
    font-size: 13px;
    color: #64748B;
}

QLabel#StatusBadge {
    background-color: #202234;
    border-radius: 6px;
    padding: 4px 10px;
    font-weight: 600;
}
"""


# ----------------------------------------------------------------------
# Thread-Safe Logging Handler Signal
# ----------------------------------------------------------------------
class LogBridge(QObject):
    log_signal = pyqtSignal(str, str)


class QtLogHandler(logging.Handler):
    def __init__(self, bridge: LogBridge):
        super().__init__()
        self.bridge = bridge
        self.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.bridge.log_signal.emit(msg, record.levelname)


# ----------------------------------------------------------------------
# Main GUI Window
# ----------------------------------------------------------------------
class ICAFAppWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("ICAF Compliance Suite")
        self.resize(980, 800)
        self.setMinimumSize(850, 650)
        self.setStyleSheet(STYLESHEET)

        self.running = False
        self.log_bridge = LogBridge()
        self.log_bridge.log_signal.connect(self._append_log)
        self.log_handler = QtLogHandler(self.log_bridge)

        self._init_ui()

    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        # 1. Header
        main_layout.addWidget(self._build_header())

        # 2. Form Panel
        main_layout.addWidget(self._build_form_card())

        # 3. Actions / Run Bar
        main_layout.addWidget(self._build_actions_bar())

        # 4. Diagnostics Log Output
        main_layout.addWidget(self._build_console_card(), stretch=1)

        # Initial State Toggle
        self._on_clause_changed(self.clause_combo.currentText())

    def _build_header(self) -> QWidget:
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title = QLabel("ICAF Compliance Check", objectName="HeaderTitle")
        subtitle = QLabel("Automated security, policy, and protocol verification framework.", objectName="HeaderSubtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        return header

    def _build_form_card(self) -> QFrame:
        card = QFrame(objectName="Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 20)
        card_layout.setSpacing(14)

        # Title / Nav Header inside card
        header_bar = QWidget()
        hb_layout = QHBoxLayout(header_bar)
        hb_layout.setContentsMargins(0, 0, 0, 6)
        
        card_title = QLabel("Session Parameters")
        card_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #00E676;")
        hb_layout.addWidget(card_title)
        hb_layout.addStretch()

        card_layout.addWidget(header_bar)

        # Main Grid Form
        form_grid = QVBoxLayout()
        form_grid.setSpacing(12)

        # Row 1: Clause & Profile
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        self.clause_combo = QComboBox()
        self.clause_combo.addItems(list(CLAUSES.keys()))
        self.clause_combo.setCurrentText("1.6.5")
        self.clause_combo.currentTextChanged.connect(self._on_clause_changed)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(self._get_profiles())

        row1.addLayout(self._create_field("Compliance Clause", self.clause_combo))
        row1.addLayout(self._create_field("DUT Profile", self.profile_combo))
        form_grid.addLayout(row1)

        # Row 2: IP & Username
        row2 = QHBoxLayout()
        row2.setSpacing(16)
        self.ssh_ip = QLineEdit("10.80.127.211")
        self.ssh_user = QLineEdit("dut")
        row2.addLayout(self._create_field("Device IP / Hostname", self.ssh_ip))
        row2.addLayout(self._create_field("SSH Username", self.ssh_user))
        form_grid.addLayout(row2)

        # Row 3: SSH Password & OAM File
        row3 = QHBoxLayout()
        row3.setSpacing(16)
        self.ssh_pass = QLineEdit()
        self.ssh_pass.setEchoMode(QLineEdit.EchoMode.Password)

        # OAM File Field with button inline
        oam_container = QWidget()
        oam_layout = QHBoxLayout(oam_container)
        oam_layout.setContentsMargins(0, 0, 0, 0)
        oam_layout.setSpacing(8)

        self.oam_path = QLineEdit()
        self.browse_btn = QPushButton("🗁 Browse...", objectName="SecondaryButton")
        self.browse_btn.clicked.connect(self._choose_oam)

        oam_layout.addWidget(self.oam_path)
        oam_layout.addWidget(self.browse_btn)

        row3.addLayout(self._create_field("SSH Password", self.ssh_pass))
        row3.addLayout(self._create_field("OAM Excel File", oam_container))
        form_grid.addLayout(row3)

        card_layout.addLayout(form_grid)

        # Conditional Extended Option Bar (Clause 1.1.1)
        self.optional_card = QFrame(objectName="Card")
        self.optional_card.setStyleSheet("QFrame#Card { background-color: #12131F; border-color: #2A2C40; }")
        opt_layout = QVBoxLayout(self.optional_card)
        opt_layout.setContentsMargins(16, 12, 16, 16)

        opt_title = QLabel("SNMP & Web Portal Configuration (Clause 1.1.1 Specific)", objectName="FieldLabel")
        opt_title.setStyleSheet("color: #8E94A7; margin-bottom: 6px;")
        opt_layout.addWidget(opt_title)

        # SNMP & Web Input Grid
        opt_grid1 = QHBoxLayout()
        self.snmp_user = QLineEdit("snmpuser")
        self.snmp_auth = QLineEdit()
        self.snmp_auth.setEchoMode(QLineEdit.EchoMode.Password)
        self.snmp_priv = QLineEdit()
        self.snmp_priv.setEchoMode(QLineEdit.EchoMode.Password)

        opt_grid1.addLayout(self._create_field("SNMPv3 User", self.snmp_user))
        opt_grid1.addLayout(self._create_field("SNMP Auth Pass", self.snmp_auth))
        opt_grid1.addLayout(self._create_field("SNMP Priv Pass", self.snmp_priv))
        opt_layout.addLayout(opt_grid1)

        opt_grid2 = QHBoxLayout()
        self.snmp_comm = QLineEdit("community")
        self.web_url = QLineEdit()
        self.web_user = QLineEdit("admin")
        self.web_pass = QLineEdit()
        self.web_pass.setEchoMode(QLineEdit.EchoMode.Password)

        opt_grid2.addLayout(self._create_field("SNMP Community", self.snmp_comm))
        opt_grid2.addLayout(self._create_field("Web Login URL", self.web_url))
        opt_grid2.addLayout(self._create_field("Web User", self.web_user))
        opt_grid2.addLayout(self._create_field("Web Password", self.web_pass))
        opt_layout.addLayout(opt_grid2)

        card_layout.addWidget(self.optional_card)

        return card

    def _build_actions_bar(self) -> QWidget:
        actions = QWidget()
        layout = QHBoxLayout(actions)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(16)

        self.run_button = QPushButton("▶  START COMPLIANCE CHECK", objectName="PrimaryButton")
        self.run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_button.clicked.connect(self._start_run)

        self.status_badge = QLabel("Ready to execute checks", objectName="StatusBadge")
        self.status_badge.setStyleSheet("color: #8E94A7; background-color: #181926; border: 1px solid #2A2C40;")

        layout.addWidget(self.run_button)
        layout.addWidget(self.status_badge)
        layout.addStretch()

        return actions

    def _build_console_card(self) -> QFrame:
        card = QFrame(objectName="Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(8)

        console_title = QLabel("Live Diagnostics Console", objectName="FieldLabel")
        console_title.setStyleSheet("color: #8E94A7;")

        self.log_text = QTextEdit(objectName="ConsoleLog")
        self.log_text.setReadOnly(True)

        layout.addWidget(console_title)
        layout.addWidget(self.log_text)
        return card

    def _create_field(self, label_text: str, widget: QWidget) -> QVBoxLayout:
        vbox = QVBoxLayout()
        vbox.setSpacing(4)
        lbl = QLabel(label_text, objectName="FieldLabel")
        vbox.addWidget(lbl)
        vbox.addWidget(widget)
        return vbox

    def _get_profiles(self) -> list[str]:
        profile_dir = settings.BASE_DIR / "icaf" / "profile"
        profiles = sorted(path.stem for path in profile_dir.glob("*.yaml"))
        return profiles if profiles else ["default"]

    def _on_clause_changed(self, clause_value: str) -> None:
        if clause_value == "1.1.1":
            self.optional_card.show()
            if not self.web_url.text():
                self.web_url.setText(f"http://{self.ssh_ip.text().strip()}/dvwa/login.php")
        else:
            self.optional_card.hide()

    def _choose_oam(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "Choose OAM Excel File", "", "Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        if selected:
            self.oam_path.setText(selected)

    def _start_run(self) -> None:
        if self.running:
            return

        if not self.ssh_ip.text().strip() or not self.ssh_user.text().strip():
            QMessageBox.critical(self, "Missing Fields", "Device IP / hostname and SSH username are required.")
            return

        if self.oam_path.text().strip() and not Path(self.oam_path.text().strip()).is_file():
            QMessageBox.critical(self, "File Error", "Choose a valid OAM Excel file or clear this field.")
            return

        self.running = True
        self.run_button.setEnabled(False)
        self.status_badge.setText("⌛︎ Running compliance engine...")
        self.status_badge.setStyleSheet("color: #FFB300; background-color: #262010; border: 1px solid #524210;")

        self._append_log("Starting compliance test suite...", "INFO")

        values = {
            "clause": self.clause_combo.currentText(),
            "profile": self.profile_combo.currentText().strip() or "default",
            "ssh_user": self.ssh_user.text().strip(),
            "ssh_ip": self.ssh_ip.text().strip(),
            "ssh_password": self.ssh_pass.text(),
            "snmp_user": self.snmp_user.text(),
            "snmp_auth_pass": self.snmp_auth.text(),
            "snmp_priv_pass": self.snmp_priv.text(),
            "snmp_community": self.snmp_comm.text(),
            "web_login_url": self.web_url.text(),
            "web_username": self.web_user.text(),
            "web_password": self.web_pass.text(),
            "oam_path": self.oam_path.text().strip(),
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
            self._finish_signal(False, str(exc))
        else:
            self._finish_signal(True)
        finally:
            logger.removeHandler(self.log_handler)

    def _load_oam(self, values: dict[str, str]):
        if not values["oam_path"]:
            return None
        from icaf.oam.oam_manager import process_oam
        return process_oam(values["oam_path"], values["ssh_ip"])

    def _finish_signal(self, success: bool, error: str = "") -> None:
        # Safely invoke UI update on main thread
        QApplication.instance().postEvent(
            self,
            _FinishEvent(success, error)
        )

    def customEvent(self, event) -> None:
        if isinstance(event, _FinishEvent):
            self._finished(event.success, event.error)

    def _finished(self, success: bool, error: str = "") -> None:
        self.running = False
        self.run_button.setEnabled(True)

        if success:
            self.status_badge.setText("✔ Checks completed successfully!")
            self.status_badge.setStyleSheet("color: #00E676; background-color: #0A2618; border: 1px solid #105232;")
            QMessageBox.information(self, "Execution Complete", f"Check complete. Report saved to:\n{settings.REPORT_DIR}")
        else:
            self.status_badge.setText("✖ Execution terminated on error.")
            self.status_badge.setStyleSheet("color: #FF5252; background-color: #281014; border: 1px solid #521018;")
            QMessageBox.critical(self, "Execution Failed", f"The check could not complete.\n\n{error}")

    def _append_log(self, message: str, level: str) -> None:
        color_map = {
            "INFO": "#00E676",
            "WARNING": "#FFB300",
            "ERROR": "#FF5252",
            "CRITICAL": "#FF5252",
        }
        color = color_map.get(level, "#E2E8F0")

        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
        self.log_text.insertHtml(f'<span style="color: {color};">{message}</span><br>')
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)


# Custom event wrapper for thread-safe UI updates upon completion
from PyQt6.QtCore import QEvent

class _FinishEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, success: bool, error: str):
        super().__init__(_FinishEvent.EVENT_TYPE)
        self.success = success
        self.error = error


def main() -> None:
    app = QApplication(sys.argv)
    window = ICAFAppWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
