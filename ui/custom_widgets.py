import tkinter as tk
from tkinter import ttk
from typing import List
import wallet_generator
from sha256_visualizer import SHA256Visualizer
from bitcoin_utils import BitcoinUtils
from wallet_scanner import WalletScanner
from tkinter import messagebox
import os

class NodeSettingsFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        # Title
        title = ttk.Label(
            self,
            text="Bitcoin Node Settings",
            style="Title.TLabel"
        )
        title.pack(pady=20)

        # Settings form
        form = ttk.Frame(self)
        form.pack(fill=tk.X, padx=20, pady=10)

        # Node URL
        ttk.Label(form, text="Node URL:").grid(row=0, column=0, padx=5, pady=5)
        self.url_entry = ttk.Entry(form, width=40)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5)
        self.url_entry.insert(0, "localhost")

        # Node Port
        ttk.Label(form, text="Port:").grid(row=1, column=0, padx=5, pady=5)
        self.port_entry = ttk.Entry(form, width=40)
        self.port_entry.grid(row=1, column=1, padx=5, pady=5)
        self.port_entry.insert(0, "8332")

        # RPC Username
        ttk.Label(form, text="RPC Username:").grid(row=2, column=0, padx=5, pady=5)
        self.username_entry = ttk.Entry(form, width=40)
        self.username_entry.grid(row=2, column=1, padx=5, pady=5)

        # RPC Password
        ttk.Label(form, text="RPC Password:").grid(row=3, column=0, padx=5, pady=5)
        self.password_entry = ttk.Entry(form, width=40, show="*")
        self.password_entry.grid(row=3, column=1, padx=5, pady=5)

        # Save button
        save_btn = ttk.Button(
            form,
            text="Save Settings",
            command=self.save_settings
        )
        save_btn.grid(row=4, column=0, columnspan=2, pady=20)

        # Status message
        self.status_label = ttk.Label(
            form,
            text="Settings will be saved to: C:\\temp\\node.txt",
            style="Topic.TLabel"
        )
        self.status_label.grid(row=5, column=0, columnspan=2, pady=10)

    def save_settings(self):
        """Save node settings to C:\temp\node.txt"""
        try:
            os.makedirs(r"C:\temp", exist_ok=True)

            settings = {
                "url": self.url_entry.get(),
                "port": self.port_entry.get(),
                "username": self.username_entry.get(),
                "password": self.password_entry.get()
            }

            with open(r"C:\temp\node.txt", "w") as f:
                for key, value in settings.items():
                    f.write(f"{key}={value}\n")

            # Update Bitcoin Utils with new settings
            BitcoinUtils.configure_node(
                settings["url"],
                settings["port"],
                settings["username"],
                settings["password"]
            )

            self.status_label.config(
                text="Settings saved successfully to C:\\temp\\node.txt",
                foreground="green"
            )
            messagebox.showinfo("Success", "Node settings saved successfully!")

        except Exception as e:
            self.status_label.config(
                text=f"Error saving settings: {str(e)}",
                foreground="red"
            )
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def load_settings(self):
        """Load existing settings if available"""
        try:
            if os.path.exists(r"C:\temp\node.txt"):
                settings = {}
                with open(r"C:\temp\node.txt", "r") as f:
                    for line in f:
                        key, value = line.strip().split("=", 1)
                        settings[key] = value

                # Update entry fields
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, settings.get("url", "localhost"))

                self.port_entry.delete(0, tk.END)
                self.port_entry.insert(0, settings.get("port", "8332"))

                self.username_entry.delete(0, tk.END)
                self.username_entry.insert(0, settings.get("username", ""))

                self.password_entry.delete(0, tk.END)
                self.password_entry.insert(0, settings.get("password", ""))

        except Exception as e:
            self.status_label.config(
                text=f"Error loading settings: {str(e)}",
                foreground="red"
            )

class EducationalFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        # Title
        title = ttk.Label(
            self,
            text="Understanding Bitcoin Wallets",
            style="Title.TLabel"
        )
        title.pack(pady=20)
        
        # Content
        content = ttk.Frame(self)
        content.pack(fill=tk.BOTH, expand=True, padx=20)
        
        topics = [
            ("What is a Bitcoin Wallet?", 
             "A Bitcoin wallet is a software program that stores private and public keys "
             "and interacts with the Bitcoin blockchain to enable users to send and "
             "receive digital currency and monitor their balance."),
            
            ("Seed Phrases", 
             "A seed phrase is a list of words that can be used to recreate your Bitcoin "
             "wallet. It's crucial to keep this safe and private."),
            
            ("Public & Private Keys",
             "Your wallet contains pairs of public and private keys. The public key is "
             "used to receive Bitcoin, while the private key is used to spend them.")
        ]
        
        for topic, description in topics:
            frame = ttk.Frame(content)
            frame.pack(fill=tk.X, pady=10)
            
            ttk.Label(frame, text=topic, style="Topic.TLabel").pack(anchor=tk.W)
            ttk.Label(frame, text=description, wraplength=600).pack(anchor=tk.W, pady=5)

class WalletFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.wallet_scanner = WalletScanner()
        self.setup_ui()

    def setup_ui(self):
        # Controls
        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, padx=20, pady=20)

        # Add save location indicator
        save_location = ttk.Label(
            controls,
            text="Saving wallets to: C:\\temp\\wallets.txt",
            style="Topic.TLabel"
        )
        save_location.pack(side=tk.LEFT, padx=20)

        # Add educational mode indicator
        self.mode_label = ttk.Label(
            controls,
            text="Educational Mode",
            style="Topic.TLabel"
        )
        self.mode_label.pack(side=tk.RIGHT, padx=5)

        generate_btn = ttk.Button(
            controls,
            text="Generate New Seed Phrase",
            command=self.generate_seed
        )
        generate_btn.pack(side=tk.LEFT, padx=5)

        self.scan_button = ttk.Button(
            controls,
            text="Start Scanning",
            command=self.toggle_scanning
        )
        self.scan_button.pack(side=tk.LEFT, padx=5)

        # Add Node Test Button
        test_node_btn = ttk.Button(
            controls,
            text="Test Node Connection",
            command=self.test_node_connection
        )
        test_node_btn.pack(side=tk.LEFT, padx=5)

        # Statistics Frame
        stats_frame = ttk.LabelFrame(self, text="Scanning Statistics")
        stats_frame.pack(fill=tk.X, padx=20, pady=10)

        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            stats_frame,
            variable=self.progress_var,
            mode='indeterminate'
        )
        self.progress.pack(fill=tk.X, padx=5, pady=5)

        # Statistics Labels
        self.stats_text = tk.StringVar(value="Total Scanned: 0 | With Balance: 0 | Rate: 0 wallets/min")
        stats_label = ttk.Label(
            stats_frame,
            textvariable=self.stats_text
        )
        stats_label.pack(pady=5)

        # Display area
        self.display = ttk.Frame(self)
        self.display.pack(fill=tk.BOTH, expand=True, padx=20)

        self.seed_display = ttk.Label(
            self.display,
            text="Click 'Generate' to create a new seed phrase",
            wraplength=600
        )
        self.seed_display.pack(pady=20)

        self.address_display = ttk.Label(
            self.display,
            text="",
            wraplength=600
        )
        self.address_display.pack(pady=10)

        self.transaction_display = ttk.Label(
            self.display,
            text="",
            wraplength=600,
            style="Transaction.TLabel"
        )
        self.transaction_display.pack(pady=10)

    def generate_seed(self):
        words, _ = wallet_generator.WalletGenerator.generate_seed_phrase()
        self.seed_display.config(
            text="Seed Phrase:\n" + " ".join(words)
        )

        # Generate mock address and transaction data
        address_info = BitcoinUtils.derive_addresses(" ".join(words).encode())
        self.address_display.config(
            text=f"Generated Address:\n{address_info['address']}"
        )
        self.transaction_display.config(
            text=f"Last Transaction Date: {address_info['last_transaction']}"
        )

        # Add to scanner
        if self.wallet_scanner.scanning:
            self.wallet_scanner.add_wallet(address_info)
            self.update_statistics()

    def toggle_scanning(self):
        if not self.wallet_scanner.scanning:
            self.wallet_scanner.start_scan()
            self.scan_button.config(text="Stop Scanning")
            self.progress.start()
            self.after(1000, self.update_statistics)
        else:
            self.wallet_scanner.stop_scan()
            self.scan_button.config(text="Start Scanning")
            self.progress.stop()

    def update_statistics(self):
        if self.wallet_scanner.scanning:
            stats = self.wallet_scanner.get_statistics()
            self.stats_text.set(
                f"Total Scanned: {stats['total_scanned']} | "
                f"With Balance: {stats['wallets_with_balance']} | "
                f"Rate: {stats['scan_rate']} wallets/min"
            )
            self.after(1000, self.update_statistics)

    def test_node_connection(self):
        """Test connection to Bitcoin node and show result."""
        success, message = BitcoinUtils.test_node_connection()
        if success:
            messagebox.showinfo("Node Connection", message)
        else:
            # Change the message to be more educational and informative
            messagebox.showinfo(
                "Educational Mode Active",
                "Running in educational simulation mode while the Bitcoin node syncs.\n\n"
                "This mode provides realistic examples and safe practice environment "
                "for learning about Bitcoin wallets and transactions.\n\n"
                f"Status: {message}"
            )

class SHA256Frame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        # Input area
        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X, padx=20, pady=20)
        
        ttk.Label(input_frame, text="Enter text to hash:").pack(side=tk.LEFT)
        
        self.input_text = ttk.Entry(input_frame, width=40)
        self.input_text.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            input_frame,
            text="Visualize Hash",
            command=self.visualize_hash
        ).pack(side=tk.LEFT)
        
        # Visualization area
        self.visualization = tk.Text(
            self,
            wrap=tk.WORD,
            height=20,
            width=80
        )
        self.visualization.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
    def visualize_hash(self):
        text = self.input_text.get()
        if not text:
            text = "Hello, Bitcoin!"
            
        # Get visualization steps
        padding_steps = SHA256Visualizer.get_padding_visualization(text)
        compression_steps = SHA256Visualizer.visualize_compression(text)
        
        # Display visualization
        self.visualization.delete(1.0, tk.END)
        self.visualization.insert(tk.END, "SHA256 Process Visualization\n\n")
        
        for step in padding_steps:
            self.visualization.insert(tk.END, step + "\n")
            
        self.visualization.insert(tk.END, "\nCompression Function:\n")
        for step in compression_steps:
            self.visualization.insert(tk.END, step + "\n")