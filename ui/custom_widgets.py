import tkinter as tk
from tkinter import ttk
from typing import List
import wallet_generator
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

class WalletFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.wallet_scanner = WalletScanner()
        self.instance_info = self.wallet_scanner.get_instance_info()
        self.setup_ui()

    def setup_ui(self):
        # Configure grid layout for full width
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Make content area expandable

        # Header section
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        header_frame.grid_columnconfigure(1, weight=1)

        # Title and instance info
        ttk.Label(
            header_frame,
            text=f"Bitcoin Wallet Scanner (Instance: {self.instance_info['instance_id']})",
            style="Title.TLabel"
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))

        # Instance details in a compact format
        details_frame = ttk.Frame(header_frame)
        details_frame.grid(row=1, column=0, columnspan=2, sticky="ew")

        # Left side: Instance info
        info_frame = ttk.Frame(details_frame)
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.instance_info_label = ttk.Label(
            info_frame,
            text=self._get_instance_info_text(),
            style='Info.TLabel'
        )
        self.instance_info_label.pack(side=tk.LEFT)

        # Right side: Controls
        controls_frame = ttk.Frame(details_frame)
        controls_frame.pack(side=tk.RIGHT)

        # Thread control
        ttk.Label(controls_frame, text="Threads:").pack(side=tk.LEFT, padx=2)
        self.thread_spinbox = ttk.Spinbox(
            controls_frame,
            from_=1,
            to=16,
            width=3
        )
        self.thread_spinbox.set(4)
        self.thread_spinbox.pack(side=tk.LEFT, padx=2)

        # Hardware acceleration options
        accel_frame = ttk.Frame(controls_frame)
        accel_frame.pack(side=tk.LEFT, padx=5)

        self.cpu_var = tk.BooleanVar(value=True)
        self.gpu_var = tk.BooleanVar(value=False)
        self.npu_var = tk.BooleanVar(value=False)

        for text, var in [("CPU", self.cpu_var), ("GPU", self.gpu_var), ("NPU", self.npu_var)]:
            ttk.Checkbutton(
                accel_frame,
                text=text,
                variable=var,
                command=self.update_acceleration
            ).pack(side=tk.LEFT, padx=2)

        # Main content area (using grid for better space utilization)
        content_frame = ttk.Frame(self)
        content_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(1, weight=1)

        # Control bar
        control_bar = ttk.Frame(content_frame)
        control_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Scan button
        self.scan_button = ttk.Button(
            control_bar,
            text="▶ Start Scanning",
            command=self.toggle_scanning,
            style='Action.TButton',
            width=15
        )
        self.scan_button.pack(side=tk.LEFT)

        # Status and rate display
        self.rate_label = ttk.Label(
            control_bar,
            text="Rate: Waiting to start...",
            style='Info.TLabel'
        )
        self.rate_label.pack(side=tk.RIGHT)

        # Statistics panel (2-column grid)
        stats_frame = ttk.LabelFrame(content_frame, text="Scanning Statistics")
        stats_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        stats_frame.grid_columnconfigure(1, weight=1)

        # Progress bar
        ttk.Label(stats_frame, text="Progress:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            stats_frame,
            variable=self.progress_var,
            mode='determinate'
        )
        self.progress.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # Statistics grid
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        stats_grid.grid_columnconfigure(1, weight=1)

        # Statistics labels
        self.stats_labels = {}
        stats = [
            ("Total Scanned", "total_scanned"),
            ("Scan Rate", "scan_rate"),
            ("Found with Balance", "wallets_with_balance"),
            ("Active Threads", "active_threads"),
            ("Queue Size", "queue_size"),
            ("CPU Usage", "cpu_usage"),
            ("Memory Usage", "memory_usage"),
            ("Network Status", "network_status")
        ]

        for i, (label, key) in enumerate(stats):
            row = i // 2
            col = i % 2
            frame = ttk.Frame(stats_grid)
            frame.grid(row=row, column=col, sticky="ew", padx=5, pady=2)
            frame.grid_columnconfigure(1, weight=1)

            ttk.Label(frame, text=f"{label}:").grid(row=0, column=0, sticky="e", padx=5)
            self.stats_labels[key] = ttk.Label(frame, text="--")
            self.stats_labels[key].grid(row=0, column=1, sticky="w", padx=5)

        # Results area
        results_frame = ttk.LabelFrame(content_frame, text="Scan Results")
        results_frame.grid(row=2, column=0, sticky="nsew", pady=5)
        results_frame.grid_columnconfigure(0, weight=1)

        self.results_text = tk.Text(
            results_frame,
            height=8,
            wrap=tk.WORD,
            font=("Consolas", 10)
        )
        self.results_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Scrollbar for results
        results_scroll = ttk.Scrollbar(
            results_frame,
            orient="vertical",
            command=self.results_text.yview
        )
        results_scroll.grid(row=0, column=1, sticky="ns")
        self.results_text.configure(yscrollcommand=results_scroll.set)

        # Start periodic updates
        self.update_statistics()

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
            self.results_text.delete("1.0", tk.END) #added to clear previous text
            self.results_text.insert(tk.END, "Scanning in progress...")
        else:
            # Stop scanning
            self.wallet_scanner.stop_scan()
            self.scan_button.config(text="▶ Start Scanning")
            self.progress.stop()
            self.thread_spinbox.config(state='normal')  # Re-enable after stopping
            self.results_text.insert(tk.END, "Scanning stopped")

    def update_statistics(self):
        """Update scanning statistics display."""
        if self.wallet_scanner.scanning:
            stats = self.wallet_scanner.get_statistics()

            try:
                # Remove commas before converting to float
                cpu_rate = float(stats['cpu_scan_rate'].replace(',', ''))
                gpu_rate = float(stats['gpu_scan_rate'].replace(',', ''))
                total_rate = cpu_rate + gpu_rate
                self.rate_label.config(
                    text=f"Processing Rate: {total_rate:,.1f} wallets/min "
                         f"(CPU: {cpu_rate:,.1f}/min, GPU: {gpu_rate:,.1f}/min)"
                )
            except (KeyError, ValueError, AttributeError):
                self.rate_label.config(text="Rate: Calculating...")

            for key, label in self.stats_labels.items():
                try:
                    value = stats[key]
                    # Format numbers with commas for display
                    if isinstance(value, (int, float)):
                        value = f"{value:,}"
                    label.config(text=str(value))
                except (KeyError, ValueError):
                    label.config(text="--")

            self.progress_var.set(stats.get('progress', 0))

            # Continue updating while scanning
            self.after(1000, self.update_statistics)


    def update_thread_count(self):
        """Update the number of scanning threads."""
        try:
            new_count = int(self.thread_spinbox.get())
            if new_count < 1:
                raise ValueError("Thread count must be at least 1")

            self.wallet_scanner.set_thread_count(new_count)
            self.instance_info = self.wallet_scanner.get_instance_info()  # Refresh instance info
            self.instance_info_label.config(text=self._get_instance_info_text())
            self.update_statistics()

        except ValueError as e:
            messagebox.showerror("Error", str(e))
            self.thread_spinbox.set(new_count)  # Set to actual value being used

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

    def _get_instance_info_text(self):
        """Get formatted instance information text."""
        return (
            f"Instance ID: {self.instance_info['instance_id']} | "
            f"Instance #: {self.instance_info['instance_number']} | "
            f"File: {self.instance_info['wallet_file']} | "
            f"CPU Threads: {self.instance_info['cpu_threads']} | "
            f"GPU: {'Enabled' if self.instance_info['gpu_enabled'] else 'Disabled'}"
        )