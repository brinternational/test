import tkinter as tk
from tkinter import ttk
from typing import List
import wallet_generator
from sha256_visualizer import SHA256Visualizer
from bitcoin_utils import BitcoinUtils
from wallet_scanner import WalletScanner
from tkinter import messagebox
import os
from datetime import datetime
import subprocess

class NodeSettingsFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.config_file = BitcoinUtils.CONFIG_FILE
        self.setup_ui()
        # Load settings from config file
        BitcoinUtils.load_config()
        self.load_default_settings()

    def setup_ui(self):
        # Use grid for the main frame
        self.grid_columnconfigure(0, weight=1)

        # Title
        title = ttk.Label(
            self,
            text="Bitcoin Node Settings",
            style="Title.TLabel"
        )
        title.grid(row=0, column=0, pady=20)

        # Settings form
        form = ttk.Frame(self)
        form.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        # Configure form grid
        form.grid_columnconfigure(1, weight=1)

        # Node URL
        ttk.Label(form, text="Node URL:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.url_entry = ttk.Entry(form, width=40)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Node Port
        ttk.Label(form, text="Port:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.port_entry = ttk.Entry(form, width=40)
        self.port_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # RPC Username
        ttk.Label(form, text="RPC Username:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.username_entry = ttk.Entry(form, width=40)
        self.username_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # RPC Password
        ttk.Label(form, text="RPC Password:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.password_entry = ttk.Entry(form, width=40, show="*")
        self.password_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # Button frame
        button_frame = ttk.Frame(form)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)

        # Save button
        save_btn = ttk.Button(
            button_frame,
            text="Save Settings",
            command=self.save_settings
        )
        save_btn.pack(side=tk.LEFT, padx=5)

        # Test Connection button
        test_btn = ttk.Button(
            button_frame,
            text="Test Connection",
            command=self.test_connection
        )
        test_btn.pack(side=tk.LEFT, padx=5)

        # Connection status
        self.status_frame = ttk.Frame(form)
        self.status_frame.grid(row=5, column=0, columnspan=2, pady=10)

        self.status_label = ttk.Label(
            self.status_frame,
            text="Settings saved in memory",
            style="Topic.TLabel"
        )
        self.status_label.pack()

    def load_default_settings(self):
        """Load settings from BitcoinUtils after config file has been loaded"""
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, BitcoinUtils.NODE_URL)

        self.port_entry.delete(0, tk.END)
        self.port_entry.insert(0, BitcoinUtils.NODE_PORT)

        self.username_entry.delete(0, tk.END)
        self.username_entry.insert(0, BitcoinUtils.RPC_USER)

        self.password_entry.delete(0, tk.END)
        self.password_entry.insert(0, BitcoinUtils.RPC_PASS)

    def save_settings(self):
        """Save settings to C:\temp\node_settings.txt"""
        try:
            # Create C:\temp directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            # Configure Bitcoin utils
            BitcoinUtils.configure_node(
                self.url_entry.get(),
                self.port_entry.get(),
                self.username_entry.get(),
                self.password_entry.get()
            )

            # Save settings to file
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.config_file, 'w') as f:
                f.write(f"# Node settings last updated: {timestamp}\n")
                f.write(f"url={self.url_entry.get()}\n")
                f.write(f"port={self.port_entry.get()}\n")
                f.write(f"username={self.username_entry.get()}\n")
                f.write(f"password={self.password_entry.get()}\n")
                f.write(f"last_updated={datetime.now().strftime('%Y-%m-%d')}\n")

            self.status_label.config(
                text="Settings saved successfully",
                foreground="#388E3C"  # Success green color
            )
            messagebox.showinfo("Success", "Node settings saved successfully")

        except Exception as e:
            error_message = f"Error saving settings: {str(e)}"
            self.status_label.config(
                text=error_message,
                foreground="#D32F2F"  # Error red color
            )
            messagebox.showerror("Error", error_message)

    def test_connection(self):
        """Test connection to Bitcoin node and update status."""
        self.status_label.config(text="Testing connection...")
        self.update()  # Force UI update

        success, message = BitcoinUtils.test_node_connection()

        if success:
            self.status_label.config(
                text="Connected successfully",
                foreground="#388E3C"  # Success green
            )
        else:
            self.status_label.config(
                text="Connection failed",
                foreground="#D32F2F"  # Error red
            )

        messagebox.showinfo("Connection Test", message)

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
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)

        # Create main scrollable frame
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas.winfo_reqwidth())
        canvas.configure(yscrollcommand=scrollbar.set)

        # Grid layout for canvas and scrollbar
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)

        # Title and mode indicator in header frame
        header = ttk.Frame(scrollable_frame)
        header.pack(fill=tk.X, padx=10, pady=5)

        title = ttk.Label(
            header,
            text="Bitcoin Wallet Scanner",
            style="Title.TLabel"
        )
        title.pack(side=tk.LEFT)

        # Remove mode label since we don't need it
        self.mode_label = ttk.Label(
            header,
            text="",  # Remove text completely
            style="Topic.TLabel"
        )
        self.mode_label.pack(side=tk.RIGHT)

        # Prominent scan button
        self.scan_button = ttk.Button(
            scrollable_frame,
            text="▶ Start Scanning",
            command=self.toggle_scanning,
            style='Action.TButton',
            cursor="hand2",
            width=25  # Make button wider
        )
        self.scan_button.pack(pady=10, padx=10, fill=tk.X)

        # Hardware acceleration frame
        accel_frame = ttk.LabelFrame(scrollable_frame, text="Hardware Settings")
        accel_frame.pack(fill=tk.X, padx=10, pady=5)

        # Acceleration options
        options_frame = ttk.Frame(accel_frame)
        options_frame.pack(fill=tk.X, padx=5, pady=5)

        self.cpu_var = tk.BooleanVar(value=True)
        self.gpu_var = tk.BooleanVar(value=False)
        self.npu_var = tk.BooleanVar(value=False)

        for text, var in [("CPU", self.cpu_var), ("GPU", self.gpu_var), ("NPU", self.npu_var)]:
            frame = ttk.Frame(options_frame)
            frame.pack(side=tk.LEFT, padx=5)

            ttk.Checkbutton(
                frame,
                text=text,
                variable=var,
                command=self.update_acceleration,
                style='Clickable.TCheckbutton'
            ).pack(side=tk.LEFT)

        # Thread control with label
        thread_frame = ttk.Frame(accel_frame)
        thread_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(thread_frame, text="Thread Count:").pack(side=tk.LEFT, padx=5)
        self.thread_spinbox = ttk.Spinbox(
            thread_frame,
            from_=1,
            to=16,
            width=3,
            command=self.update_thread_count
        )
        self.thread_spinbox.set(4)
        self.thread_spinbox.pack(side=tk.LEFT)


        # Progress frame
        progress_frame = ttk.LabelFrame(scrollable_frame, text="Progress")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            mode='indeterminate'
        )
        self.progress.pack(fill=tk.X, padx=5, pady=5)

        # Statistics display
        stats_frame = ttk.LabelFrame(scrollable_frame, text="Statistics")
        stats_frame.pack(fill=tk.X, padx=10, pady=5)

        self.stats_text = tk.StringVar(value="Click 'Start Scanning' to begin")
        ttk.Label(
            stats_frame,
            textvariable=self.stats_text,
            wraplength=400
        ).pack(padx=5, pady=5)

        # Results area
        results_frame = ttk.LabelFrame(scrollable_frame, text="Results")
        results_frame.pack(fill=tk.BOTH, padx=10, pady=5)

        self.results_display = ttk.Label(
            results_frame,
            text="Scanning results will appear here",
            wraplength=400
        )
        self.results_display.pack(padx=5, pady=5)

    def toggle_scanning(self):
        """Toggle wallet scanning on/off."""
        # Check node connection first
        success, message = BitcoinUtils.test_node_connection()
        if not success:
            messagebox.showwarning(
                "Node Connection Required",
                "Please configure and connect to a Bitcoin node before scanning.\n\n"
                "Go to Node Settings tab to configure your connection."
            )
            # Switch to node settings tab using parent notebook
            parent = self.winfo_parent()
            while parent:
                widget = self.nametowidget(parent)
                if isinstance(widget, ttk.Notebook):
                    widget.select(3)  # Index of node_settings_frame
                    break
                parent = widget.winfo_parent()
            return

        if not self.wallet_scanner.scanning:
            # Start scanning
            self.wallet_scanner.start_scan()
            self.scan_button.config(text="Stop Scanning")
            self.progress.start()
            self.thread_spinbox.config(state='disabled')  # Disable during scanning
            self.update_statistics()
            self.results_display.config(text="Scanning in progress...")
        else:
            # Stop scanning
            self.wallet_scanner.stop_scan()
            self.scan_button.config(text="▶ Start Scanning")
            self.progress.stop()
            self.thread_spinbox.config(state='normal')  # Re-enable after stopping
            self.results_display.config(text="Scanning stopped")

    def update_statistics(self):
        """Update scanning statistics display."""
        if self.wallet_scanner.scanning:
            stats = self.wallet_scanner.get_statistics()
            cpu_rate = stats['cpu_scan_rate']
            gpu_rate = stats['gpu_scan_rate']

            self.stats_text.set(
                f"Total Scanned: {stats['total_scanned']} | "
                f"With Balance: {stats['wallets_with_balance']} | "
                f"CPU Rate: {cpu_rate} w/min | "
                f"GPU Rate: {gpu_rate} w/min | "
                f"Active Threads: {stats['active_threads']} | "
                f"Queue: {stats['queue_size']}"
            )

            # Continue updating while scanning
            self.after(100, self.update_statistics)  # Update more frequently

    def update_thread_count(self):
        """Update the number of scanning threads."""
        try:
            new_count = int(self.thread_spinbox.get())
            if new_count < 1:
                raise ValueError("Thread count must be at least 1")

            self.wallet_scanner.set_thread_count(new_count)
            self.update_statistics()

        except ValueError as e:
            messagebox.showerror("Error", str(e))
            self.thread_spinbox.set(self.wallet_scanner.thread_count)

    def update_acceleration(self):
        """Update hardware acceleration preferences."""
        # Ensure at least one acceleration method is enabled
        if not any([self.cpu_var.get(), self.gpu_var.get(), self.npu_var.get()]):
            self.cpu_var.set(True)  # Force CPU if all are disabled
            messagebox.showwarning(
                "Acceleration Warning",
                "At least one acceleration method must be enabled. CPU will remain enabled."
            )

        # Update scanner preferences
        self.wallet_scanner.set_acceleration_preferences(
            cpu_enabled=self.cpu_var.get(),
            gpu_enabled=self.gpu_var.get(),
            npu_enabled=self.npu_var.get()
        )

        # Restart scanning if active
        if self.wallet_scanner.scanning:
            self.wallet_scanner.stop_scan()
            self.wallet_scanner.start_scan()



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