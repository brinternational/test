import tkinter as tk
from tkinter import ttk, messagebox
import sys
from ui.theme import setup_theme
from ui.custom_widgets import WalletFrame, NodeSettingsFrame
from version import get_version_info
from bitcoin_utils import BitcoinUtils
from instance_controller import ProcessManagerFrame  # Updated import
import logging
import os
import threading
import time
from typing import Optional
from flask import Flask
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bitcoin_wallet.log')
    ]
)

# Initialize Flask app
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bitcoin Education App API"

def run_flask():
    flask_app.run(host='0.0.0.0', port=5000)

class ConnectionManager:
    def __init__(self, app):
        self.app = app
        self.connected = False
        self.last_check = 0
        self.check_interval = 15  # Reduced interval for more responsive checks
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._initial_check_done = False

    def start(self):
        if not self._thread or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._check_loop, daemon=True)
            self._thread.start()

    def stop(self):
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join()

    def _check_loop(self):
        while not self._stop_event.is_set():
            self.check_connection()
            self._stop_event.wait(self.check_interval)

    def check_connection(self) -> bool:
        success, message = BitcoinUtils.test_node_connection()
        if success != self.connected or not self._initial_check_done:
            self.connected = success
            self._initial_check_done = True
            self.app.update_connection_status(success, message, show_warning=True)
        return success

class BitcoinEducationApp(tk.Tk):
    def __init__(self):
        try:
            super().__init__()

            # Create temp directory for wallets
            temp_dir = os.path.join("C:", "temp")
            os.makedirs(temp_dir, exist_ok=True)
            logging.info(f"Temp directory created/verified: {temp_dir}")

            # Log version information
            version_info = get_version_info()
            logging.info(f"Starting Bitcoin Wallet Education v{version_info['version']}")
            logging.info(f"Build Date: {version_info['build_date']}")
            logging.info(f"Runtime: {version_info['runtime_timestamp']}")

            # Initialize connection manager
            self.connection_manager = ConnectionManager(self)

            # Basic window setup
            self.title(f"Bitcoin Wallet v{version_info['version']}")
            self.geometry("1024x768")

            # Setup theme
            setup_theme(self)

            # Create main container
            self.container = ttk.Frame(self)
            self.container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Header with connection status
            self.header_frame = ttk.Frame(self.container)
            self.header_frame.pack(fill=tk.X, pady=(0, 10))

            # Title and status in header
            title = ttk.Label(
                self.header_frame,
                text="Bitcoin Wallet Scanner",
                style="Title.TLabel"
            )
            title.pack(side=tk.LEFT)

            # Connection status with icon
            self.connection_frame = ttk.Frame(self.header_frame)
            self.connection_frame.pack(side=tk.RIGHT)

            self.connection_icon = ttk.Label(
                self.connection_frame,
                text="○",
                foreground="#666666"
            )
            self.connection_icon.pack(side=tk.LEFT, padx=(0, 5))

            self.connection_status = ttk.Label(
                self.connection_frame,
                text="Checking node connection...",
                style="Info.TLabel"
            )
            self.connection_status.pack(side=tk.LEFT)

            # Setup main notebook with tabs
            self.notebook = ttk.Notebook(self.container)
            self.notebook.pack(fill=tk.BOTH, expand=True)

            # Create and add process manager frame (replaces instance manager)
            self.process_manager_frame = ProcessManagerFrame(self.notebook, self)
            self.node_settings_frame = NodeSettingsFrame(self.notebook)

            # Add main tabs
            self.notebook.add(self.process_manager_frame, text="Processes")
            self.notebook.add(self.node_settings_frame, text="Node Settings")

            # Dictionary to track process tabs
            self.process_tabs = {}

            # Start connection manager
            self.connection_manager.start()

            # Bind cleanup to window closing
            self.protocol("WM_DELETE_WINDOW", self.on_closing)

            # Initial connection check
            self.after(1000, self.connection_manager.check_connection)

        except Exception as e:
            logging.error(f"Error during initialization: {str(e)}")
            messagebox.showerror("Error", f"Failed to start: {str(e)}")
            raise

    def add_process_tab(self, process_id: str):
        """Add a new process tab to the notebook."""
        if process_id not in self.process_tabs:
            process_frame = WalletFrame(self.notebook)
            self.notebook.add(process_frame, text=f"Process {process_id}")
            self.process_tabs[process_id] = process_frame
            self.notebook.select(self.notebook.index(process_frame))
            return process_frame
        return None

    def remove_process_tab(self, process_id: str):
        """Remove a process tab from the notebook."""
        if process_id in self.process_tabs:
            process_frame = self.process_tabs[process_id]
            self.notebook.forget(self.notebook.index(process_frame))
            del self.process_tabs[process_id]

    def update_connection_status(self, connected: bool, message: str, show_warning: bool = False):
        """Update the connection status display."""
        if connected:
            self.connection_status.configure(
                text="Connected to node",
                foreground="#388E3C"
            )
            self.connection_icon.configure(
                text="●",
                foreground="#388E3C"
            )
        else:
            self.connection_status.configure(
                text="Node connection failed",
                foreground="#D32F2F"
            )
            self.connection_icon.configure(
                text="○",
                foreground="#D32F2F"
            )
            if show_warning and self.notebook.select() != str(self.node_settings_frame):
                self.show_connection_warning(message)
                self.notebook.select(1)  # Switch to node settings tab

    def show_connection_warning(self, message: str):
        """Display a warning about node connection issues."""
        messagebox.showwarning(
            "Node Connection Required",
            f"Bitcoin node connection failed:\n\n{message}\n\n"
            "Please configure your node settings to continue."
        )

    def on_closing(self):
        """Clean up resources before closing."""
        try:
            self.connection_manager.stop()
            for process_id in list(self.process_tabs.keys()):
                self.remove_process_tab(process_id)
            logging.info("Successfully stopped all processes")
        except Exception as e:
            logging.error(f"Error stopping processes: {str(e)}")
        finally:
            self.destroy()

if __name__ == "__main__":
    try:
        # Start Flask server in a separate thread
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()

        # Start Tkinter application
        app = BitcoinEducationApp()
        app.mainloop()
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        sys.exit(1)