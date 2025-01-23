import tkinter as tk
from tkinter import ttk, messagebox
from ui.theme import setup_theme
from ui.custom_widgets import EducationalFrame, WalletFrame, SHA256Frame
import bitcoin_utils
import wallet_generator

class BitcoinEducationApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Bitcoin Wallet Education")
        self.geometry("1024x768")
        
        # Setup custom theme
        setup_theme(self)
        
        # Create main container
        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create notebook for tabbed interface
        self.notebook = ttk.Notebook(self.container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.wallet_frame = WalletFrame(self.notebook)
        self.sha256_frame = SHA256Frame(self.notebook)
        self.educational_frame = EducationalFrame(self.notebook)
        
        self.notebook.add(self.educational_frame, text="Learn Bitcoin Basics")
        self.notebook.add(self.wallet_frame, text="Wallet Generator")
        self.notebook.add(self.sha256_frame, text="SHA256 Visualization")
        
        # Set up menu
        self.create_menu()
        
    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.quit)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
    def show_about(self):
        messagebox.showinfo(
            "About",
            "Bitcoin Wallet Educational Tool\n\n"
            "This application is designed to teach Bitcoin wallet concepts "
            "and SHA256 hashing in an interactive way."
        )

if __name__ == "__main__":
    app = BitcoinEducationApp()
    app.mainloop()
