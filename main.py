import tkinter as tk
from tkinter import ttk, messagebox
import sys
from ui.theme import setup_theme
from ui.custom_widgets import EducationalFrame, WalletFrame, SHA256Frame
import bitcoin_utils
import wallet_generator

class BitcoinEducationApp(tk.Tk):
    def __init__(self):
        try:
            super().__init__()

            print("Initializing Bitcoin Education App...")
            # Basic window setup
            self.title("Bitcoin Wallet Education")
            self.geometry("800x600")  # Slightly smaller default size

            # Force window to top level and update
            self.lift()
            self.attributes('-topmost', True)
            self.after_idle(self.attributes, '-topmost', False)

            print("Setting up theme...")
            setup_theme(self)

            # Create a simple label to verify display
            test_label = ttk.Label(
                self,
                text="Bitcoin Wallet Education",
                style="Title.TLabel"
            )
            test_label.pack(pady=20)

            print("Creating main container...")
            self.container = ttk.Frame(self)
            self.container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            print("Setting up notebook...")
            self.notebook = ttk.Notebook(self.container)
            self.notebook.pack(fill=tk.BOTH, expand=True)

            print("Creating frames...")
            self.educational_frame = EducationalFrame(self.notebook)
            self.wallet_frame = WalletFrame(self.notebook)
            self.sha256_frame = SHA256Frame(self.notebook)

            print("Adding tabs to notebook...")
            self.notebook.add(self.educational_frame, text="Learn Bitcoin Basics")
            self.notebook.add(self.wallet_frame, text="Wallet Generator")
            self.notebook.add(self.sha256_frame, text="SHA256 Visualization")

            print("Setting up menu...")
            self.create_menu()

            # Force an update of the window
            self.update_idletasks()
            self.update()

            print("Initialization complete.")

        except Exception as e:
            print(f"Error during initialization: {str(e)}", file=sys.stderr)
            messagebox.showerror("Initialization Error", f"Error starting application: {str(e)}")
            raise

    def create_menu(self):
        try:
            menubar = tk.Menu(self)
            self.config(menu=menubar)

            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="File", menu=file_menu)
            file_menu.add_command(label="Exit", command=self.quit)

            help_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Help", menu=help_menu)
            help_menu.add_command(label="About", command=self.show_about)
        except Exception as e:
            print(f"Error creating menu: {str(e)}", file=sys.stderr)

    def show_about(self):
        messagebox.showinfo(
            "About",
            "Bitcoin Wallet Educational Tool\n\n"
            "This application is designed to teach Bitcoin wallet concepts "
            "and SHA256 hashing in an interactive way."
        )

if __name__ == "__main__":
    try:
        print("Starting Bitcoin Education App...")
        app = BitcoinEducationApp()
        print("Running main loop...")
        app.mainloop()
    except Exception as e:
        print(f"Fatal error: {str(e)}", file=sys.stderr)
        sys.exit(1)