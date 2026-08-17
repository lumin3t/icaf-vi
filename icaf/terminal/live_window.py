"""
icaf/terminal/live_window.py
Real-time animated terminal window
"""

import tkinter as tk
from tkinter import scrolledtext
import time
import threading
from icaf.utils.logger import logger


class LiveTerminalWindow:
    """Opens a real window that looks and behaves like a live terminal"""

    def __init__(self):
        self.root = None
        self.text_widget = None
        self.lines = []
        self.running = True
        self.start()

    def start(self):
        """Start the GUI in a separate thread"""
        def run_gui():
            self.root = tk.Tk()
            self.root.title("TCAF Live Terminal - Alpine DUT")
            self.root.geometry("1200x700")
            self.root.configure(bg="#300a24")

            # Title bar style
            title = tk.Label(self.root, text="   localhost:~# TCAF Live Session", 
                           bg="#300a24", fg="#00ff00", font=("DejaVu Sans Mono", 12, "bold"))
            title.pack(fill="x")

            self.text_widget = scrolledtext.ScrolledText(
                self.root, bg="#1e001e", fg="#00ff80", 
                font=("DejaVu Sans Mono", 11), wrap=tk.WORD
            )
            self.text_widget.pack(fill="both", expand=True, padx=10, pady=10)

            self.add_line("bhavya@Ubuntu:~/icaf_1.6.5$ ssh root@192.168.56.102")
            self.add_line("root@192.168.56.102's password: ")
            self.add_line("Welcome to Alpine!", delay=0.5)
            self.add_line("localhost:~# ", delay=0.8)

            self.root.protocol("WM_DELETE_WINDOW", self.on_close)
            self.root.mainloop()

        threading.Thread(target=run_gui, daemon=True).start()
        time.sleep(2.0)  # Wait for window to open

    def add_line(self, text, delay=0.6):
        """Add line with typing effect"""
        if not self.text_widget:
            return

        def type_line():
            self.lines.append(text)
            self.text_widget.insert(tk.END, text + "\n")
            self.text_widget.see(tk.END)
            time.sleep(delay)

        threading.Thread(target=type_line, daemon=True).start()

    def on_close(self):
        self.running = False
        if self.root:
            self.root.destroy()

    def run_command(self, command):
        """Simulate typing a command"""
        self.add_line(command)
        time.sleep(0.8)

    def add_output(self, output):
        """Add command output"""
        for line in output.splitlines():
            self.add_line(line, delay=0.3)


# Global instance
live_terminal = LiveTerminalWindow()