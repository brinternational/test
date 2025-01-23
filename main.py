import tkinter as tk
from tkinter import ttk, messagebox
import sys
from ui.theme import setup_theme
from ui.custom_widgets import EducationalFrame, WalletFrame, SHA256Frame, NodeSettingsFrame

class BitcoinEducationApp(tk.Tk):
    def __init__(self):
        try:
            super().__init__()

            # Basic window setup
            self.title("Bitcoin Wallet")
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

            # Simple status bar
            self.status_bar = ttk.Label(
                self.container,
                text="Educational Mode Active",
                style="TLabel"
            )
            self.status_bar.pack(pady=10)

        except Exception as e:
            print(f"Error during initialization: {str(e)}", file=sys.stderr)
            messagebox.showerror("Error", f"Failed to start: {str(e)}")
            raise

    def show_about(self):
        messagebox.showinfo(
            "About",
            "Bitcoin Wallet Educational Tool\n\n"
            "This application is designed to teach Bitcoin wallet concepts "
            "and SHA256 hashing in an interactive way."
        )

if __name__ == "__main__":
    try:
        app = BitcoinEducationApp()
        app.mainloop()
    except Exception as e:
        print(f"Fatal error: {str(e)}", file=sys.stderr)
        sys.exit(1)