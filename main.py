import tkinter as tk
from tkinter import ttk, messagebox
import sys
from ui.theme import setup_theme
from ui.custom_widgets import EducationalFrame, WalletFrame, SHA256Frame, NodeSettingsFrame
from version import get_version_info
import logging

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
                text="Bitcoin Wallet Education",
                style="Title.TLabel"
            )
            header.pack(pady=(10, 20))

            # Setup notebook with tabs
            self.notebook = ttk.Notebook(self.container)
            self.notebook.pack(fill=tk.BOTH, expand=True)

            # Create and add frames
            self.educational_frame = EducationalFrame(self.notebook)
            self.wallet_frame = WalletFrame(self.notebook)
            self.sha256_frame = SHA256Frame(self.notebook)
            self.node_settings_frame = NodeSettingsFrame(self.notebook)

            self.notebook.add(self.educational_frame, text="Learn")
            self.notebook.add(self.wallet_frame, text="Wallet")
            self.notebook.add(self.sha256_frame, text="SHA256")
            self.notebook.add(self.node_settings_frame, text="Node Settings")

            # Simple status bar with version
            status_text = f"Educational Mode Active - v{version_info['version']}"
            self.status_bar = ttk.Label(
                self.container,
                text=status_text,
                style="TLabel"
            )
            self.status_bar.pack(pady=10)

        except Exception as e:
            logging.error(f"Error during initialization: {str(e)}")
            messagebox.showerror("Error", f"Failed to start: {str(e)}")
            raise

    def show_about(self):
        version_info = get_version_info()
        messagebox.showinfo(
            "About",
            f"Bitcoin Wallet Educational Tool v{version_info['version']}\n"
            f"Built on: {version_info['build_date']}\n\n"
            "This application is designed to teach Bitcoin wallet concepts "
            "and SHA256 hashing in an interactive way."
        )

if __name__ == "__main__":
    try:
        app = BitcoinEducationApp()
        app.mainloop()
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        sys.exit(1)