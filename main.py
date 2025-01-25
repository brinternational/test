import tkinter as tk
from tkinter import ttk, messagebox
import sys
from ui.theme import setup_theme
from ui.custom_widgets import WalletFrame, NodeSettingsFrame
from version import get_version_info
from bitcoin_utils import BitcoinUtils
from instance_controller import InstanceManagerFrame
import logging
import os
import threading
import time
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bitcoin_wallet.log')
    ]
)

class ConnectionManager:
    def __init__(self, app):
        self.app = app
        self.connected = False
        self.last_check = 0
        self.check_interval = 30  # seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

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
        if success != self.connected:
            self.connected = success
            self.app.update_connection_status(success, message)
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
            self.geometry("1024x768")  # Increased default size

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

            self.connection_status = ttk.Label(
                self.header_frame,
                text="Checking node connection...",
                style="Info.TLabel"
            )
            self.connection_status.pack(side=tk.RIGHT)

            # Setup notebook with tabs
            self.notebook = ttk.Notebook(self.container)
            self.notebook.pack(fill=tk.BOTH, expand=True)

            # Create and add frames
            self.instance_manager_frame = InstanceManagerFrame(self.notebook)
            self.wallet_frame = WalletFrame(self.notebook)
            self.node_settings_frame = NodeSettingsFrame(self.notebook)

            # Add tabs
            self.notebook.add(self.instance_manager_frame, text="Instances")
            self.notebook.add(self.wallet_frame, text="Wallet")
            self.notebook.add(self.node_settings_frame, text="Node Settings")

            # Start connection manager
            self.connection_manager.start()

            # Bind cleanup to window closing
            self.protocol("WM_DELETE_WINDOW", self.on_closing)

        except Exception as e:
            logging.error(f"Error during initialization: {str(e)}")
            messagebox.showerror("Error", f"Failed to start: {str(e)}")
            raise

    def update_connection_status(self, connected: bool, message: str):
        """Update the connection status display."""
        if connected:
            self.connection_status.configure(
                text="✓ Connected to node",
                foreground="#388E3C"  # Success green
            )
        else:
            self.connection_status.configure(
                text="✗ Node connection failed",
                foreground="#D32F2F"  # Error red
            )
            # Show warning only if we're not on the node settings tab
            if self.notebook.select() != str(self.node_settings_frame):
                messagebox.showwarning(
                    "Node Connection",
                    "Not connected to Bitcoin node. Please configure node settings."
                )
                self.notebook.select(2)  # Switch to node settings tab

    def on_closing(self):
        """Clean up resources before closing."""
        try:
            self.connection_manager.stop()
            self.instance_manager_frame.controller.stop_all_instances()
            logging.info("Successfully stopped all instances")
        except Exception as e:
            logging.error(f"Error stopping instances: {str(e)}")
        finally:
            self.destroy()

    def show_about(self):
        version_info = get_version_info()
        messagebox.showinfo(
            "About",
            f"Bitcoin Wallet Scanner v{version_info['version']}\n"
            f"Built on: {version_info['build_date']}\n\n"
            "This application scans for Bitcoin wallets and "
            "provides educational resources about Bitcoin technology."
        )

if __name__ == "__main__":
    try:
        app = BitcoinEducationApp()
        app.mainloop()
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        sys.exit(1)