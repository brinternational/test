import tkinter as tk
from tkinter import ttk, messagebox
import sys
import socket
from ui.theme import setup_theme
from ui.custom_widgets import WalletFrame, NodeSettingsFrame
from version import get_version_info
from bitcoin_utils import BitcoinUtils
from instance_controller import ProcessManagerFrame
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
    """Run Flask server with consistent port."""
    try:
        port = 44555  # Using a fixed port
        logging.info(f"Starting Flask server on port {port}")
        flask_app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logging.error(f"Flask server error: {str(e)}")
        raise

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

            # Basic window setup
            self.title(f"Bitcoin Wallet Education v{version_info['version']}")
            self.geometry("1024x768")

            # Setup theme
            setup_theme(self)

            # Create main container
            self.container = ttk.Frame(self)
            self.container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Setup notebook with tabs
            self.notebook = ttk.Notebook(self.container)
            self.notebook.pack(fill=tk.BOTH, expand=True)

            # Create and add process manager frame
            self.process_manager_frame = ProcessManagerFrame(self.notebook, self)
            self.node_settings_frame = NodeSettingsFrame(self.notebook)

            # Add main tabs
            self.notebook.add(self.process_manager_frame, text="Processes")
            self.notebook.add(self.node_settings_frame, text="Node Settings")

            # Dictionary to track process tabs
            self.process_tabs = {}

            # Bind cleanup to window closing
            self.protocol("WM_DELETE_WINDOW", self.on_closing)

            logging.info("Application initialized successfully")

        except Exception as e:
            logging.error(f"Error during initialization: {str(e)}")
            messagebox.showerror("Error", f"Failed to start: {str(e)}")
            raise

    def add_process_tab(self, process_id: str):
        """Add a new process tab to the notebook."""
        if process_id not in self.process_tabs:
            try:
                process_frame = WalletFrame(self.notebook)
                self.notebook.add(process_frame, text=f"Process {process_id}")
                self.process_tabs[process_id] = process_frame
                self.notebook.select(self.notebook.index(process_frame))
                logging.info(f"Added new process tab: {process_id}")
                return process_frame
            except Exception as e:
                logging.error(f"Error adding process tab {process_id}: {str(e)}")
                return None
        return None

    def remove_process_tab(self, process_id: str):
        """Remove a process tab from the notebook."""
        if process_id in self.process_tabs:
            try:
                process_frame = self.process_tabs[process_id]
                self.notebook.forget(self.notebook.index(process_frame))
                del self.process_tabs[process_id]
                logging.info(f"Removed process tab: {process_id}")
            except Exception as e:
                logging.error(f"Error removing process tab {process_id}: {str(e)}")

    def on_closing(self):
        """Clean up resources before closing."""
        try:
            for process_id in list(self.process_tabs.keys()):
                self.remove_process_tab(process_id)
            logging.info("Successfully stopped all processes")
        except Exception as e:
            logging.error(f"Error stopping processes: {str(e)}")
        finally:
            self.quit()

if __name__ == "__main__":
    try:
        # Start Flask server in a separate thread
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()
        logging.info("Flask server thread started")

        # Give Flask time to start
        time.sleep(1)

        # Start Tkinter application
        app = BitcoinEducationApp()
        app.mainloop()
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        sys.exit(1)