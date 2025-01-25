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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bitcoin_wallet.log')
    ]
)

class BitcoinEducationApp(tk.Tk):
    def __init__(self):
        try:
            super().__init__()

            # Create temp directory for wallets if it doesn't exist
            temp_dir = os.path.join("C:", "temp")  # Updated to use C:\temp
            os.makedirs(temp_dir, exist_ok=True)
            logging.info(f"Temp directory created/verified: {temp_dir}")

            # Log version information at startup
            version_info = get_version_info()
            logging.info(f"Starting Bitcoin Wallet Education v{version_info['version']}")
            logging.info(f"Build Date: {version_info['build_date']}")
            logging.info(f"Runtime: {version_info['runtime_timestamp']}")

            # Basic window setup
            self.title(f"Bitcoin Wallet v{version_info['version']}")
            self.geometry("900x600")

            # Setup dark theme
            setup_theme(self)

            # Create main container
            self.container = ttk.Frame(self)
            self.container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Simple header
            header = ttk.Label(
                self.container,
                text="Bitcoin Wallet Scanner",
                style="Title.TLabel"
            )
            header.pack(pady=(10, 20))

            # Setup notebook with tabs
            self.notebook = ttk.Notebook(self.container)
            self.notebook.pack(fill=tk.BOTH, expand=True)

            # Create and add frames
            self.instance_manager_frame = InstanceManagerFrame(self.notebook)
            self.wallet_frame = WalletFrame(self.notebook)
            self.node_settings_frame = NodeSettingsFrame(self.notebook)

            # Add tabs in preferred order
            self.notebook.add(self.instance_manager_frame, text="Instances")
            self.notebook.add(self.wallet_frame, text="Wallet")
            self.notebook.add(self.node_settings_frame, text="Node Settings")

            # Test node connection and update status
            self.check_node_connection()

            # Bind cleanup to window closing
            self.protocol("WM_DELETE_WINDOW", self.on_closing)

        except Exception as e:
            logging.error(f"Error during initialization: {str(e)}")
            messagebox.showerror("Error", f"Failed to start: {str(e)}")
            raise

    def check_node_connection(self):
        """Test connection to Bitcoin node and update application state."""
        success, message = BitcoinUtils.test_node_connection()
        if not success:
            messagebox.showwarning(
                "Node Connection",
                "Not connected to Bitcoin node. Please configure node settings before scanning."
            )
            # Switch to node settings tab
            self.notebook.select(2)

    def on_closing(self):
        """Clean up resources before closing the application."""
        try:
            # Stop all running instances
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