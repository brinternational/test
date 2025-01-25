import tkinter as tk
from tkinter import ttk, messagebox
import logging
import os
import threading
from datetime import datetime
from wallet_scanner import WalletScanner
from typing import Dict
from bitcoin_utils import BitcoinUtils # Added import for BitcoinUtils
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bitcoin_wallet.log')
    ]
)

class NodeSettingsFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.bitcoin_utils = BitcoinUtils()
        self.setup_ui()
        self.check_connection()

    def setup_ui(self):
        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Node Settings Frame
        settings_frame = ttk.LabelFrame(self, text="Bitcoin Node Settings")
        settings_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Connection status
        status_frame = ttk.Frame(settings_frame)
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_indicator = ttk.Label(
            status_frame, 
            text="●",
            font=("Arial", 12),
            foreground="gray"
        )
        self.status_indicator.pack(side=tk.LEFT, padx=5)

        ttk.Label(status_frame, text="Connection Status:").pack(side=tk.LEFT, padx=5)
        self.status_label = ttk.Label(status_frame, text="Checking...")
        self.status_label.pack(side=tk.LEFT, padx=5)

        # Node Settings
        settings_container = ttk.Frame(settings_frame)
        settings_container.pack(fill=tk.X, padx=5, pady=5)

        # Node URL
        url_frame = ttk.Frame(settings_container)
        url_frame.pack(fill=tk.X, pady=2)
        ttk.Label(url_frame, text="Node URL:").pack(side=tk.LEFT, padx=5)
        self.url_var = tk.StringVar(value=self.bitcoin_utils.NODE_URL)
        ttk.Entry(url_frame, textvariable=self.url_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Node Port
        port_frame = ttk.Frame(settings_container)
        port_frame.pack(fill=tk.X, pady=2)
        ttk.Label(port_frame, text="Port:").pack(side=tk.LEFT, padx=5)
        self.port_var = tk.StringVar(value=self.bitcoin_utils.NODE_PORT)
        ttk.Entry(port_frame, textvariable=self.port_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Wallet Save Location
        wallet_frame = ttk.Frame(settings_container)
        wallet_frame.pack(fill=tk.X, pady=2)
        ttk.Label(wallet_frame, text="Wallet Save Location:").pack(side=tk.LEFT, padx=5)
        self.wallet_dir_var = tk.StringVar(value="C:/temp")
        ttk.Entry(wallet_frame, textvariable=self.wallet_dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(wallet_frame, text="Browse", command=self.browse_wallet_dir).pack(side=tk.LEFT, padx=5)

        # Buttons
        button_frame = ttk.Frame(settings_container)
        button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(
            button_frame,
            text="Save Settings",
            command=self.save_settings
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Test Connection",
            command=self.check_connection
        ).pack(side=tk.LEFT, padx=5)

        # Node info display
        self.info_text = tk.Text(settings_frame, height=10, width=50)
        self.info_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

    def browse_wallet_dir(self):
        from tkinter import filedialog
        directory = filedialog.askdirectory(initialdir=self.wallet_dir_var.get())
        if directory:
            self.wallet_dir_var.set(directory)

    def save_settings(self):
        try:
            # Update Bitcoin Utils settings
            self.bitcoin_utils.configure_node(
                self.url_var.get(),
                self.port_var.get(),
                self.bitcoin_utils.RPC_USER,  # Keep existing RPC credentials
                self.bitcoin_utils.RPC_PASS
            )

            # Save wallet directory
            wallet_dir = self.wallet_dir_var.get()
            os.makedirs(wallet_dir, exist_ok=True)

            # Update config file
            self.bitcoin_utils.save_config(
                url=self.url_var.get(),
                port=self.port_var.get(),
                wallet_dir=wallet_dir
            )

            messagebox.showinfo("Success", "Settings saved successfully")
            self.check_connection()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def check_connection(self):
        try:
            success, info = self.bitcoin_utils.test_node_connection()

            if success:
                self.status_indicator.config(foreground="green")
                self.status_label.config(text="Connected", foreground="green")
            else:
                self.status_indicator.config(foreground="red")
                self.status_label.config(text="Disconnected", foreground="red")

            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, info)

        except Exception as e:
            self.status_indicator.config(foreground="red")
            self.status_label.config(text="Error", foreground="red")
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, f"Error: {str(e)}\nUsing simulation mode.")

class SummaryTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_ui()
        self.start_update_thread()

    def setup_ui(self):
        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Status Frame
        status_frame = ttk.LabelFrame(self, text="Overall Statistics")
        status_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.stats_text = tk.Text(status_frame, height=12, width=50)
        self.stats_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

    def start_update_thread(self):
        self.update_thread = threading.Thread(target=self.update_stats, daemon=True)
        self.update_thread.start()

    def update_stats(self):
        while True:
            try:
                if hasattr(self, 'stats_text') and hasattr(self, 'get_combined_stats'):
                    stats = self.get_combined_stats()
                    if stats:
                        stats_text = (
                            f"=== Combined Statistics ===\n"
                            f"Active Scanners: {stats['active_scanners']}\n"
                            f"Total Scanned: {stats['total_scanned']}\n"
                            f"Total CPU Processed: {stats['cpu_processed']}\n"
                            f"Total GPU Processed: {stats['gpu_processed']}\n"
                            f"Total Found Wallets: {stats['wallets_with_balance']}\n"
                            f"Combined CPU Rate: {stats['cpu_scan_rate']}/min\n"
                            f"Combined GPU Rate: {stats['gpu_scan_rate']}/min\n"
                            f"Total Queue Size: {stats['queue_size']}\n"
                            f"Last Updated: {datetime.now().strftime('%H:%M:%S')}\n"
                            f"========================="
                        )
                        self.stats_text.delete(1.0, tk.END)
                        self.stats_text.insert(tk.END, stats_text)
            except Exception as e:
                logging.error(f"Error updating summary stats: {str(e)}")
            finally:
                threading.Event().wait(1.0)

class WalletScannerTab(ttk.Frame):
    def __init__(self, parent, tab_id: str):
        super().__init__(parent)
        self.tab_id = tab_id
        self.scanner = WalletScanner()
        self.setup_ui()

    def setup_ui(self):
        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Status Frame
        status_frame = ttk.LabelFrame(self, text="Scanner Status")
        status_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Control buttons
        btn_frame = ttk.Frame(status_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self.start_btn = ttk.Button(btn_frame, text="Start Scanning", command=self.start_scanning)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="Stop Scanning", command=self.stop_scanning)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn['state'] = 'disabled'

        # Thread count control
        thread_frame = ttk.Frame(status_frame)
        thread_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(thread_frame, text="Threads:").pack(side=tk.LEFT, padx=5)
        self.thread_var = tk.StringVar(value="4")
        thread_spinbox = ttk.Spinbox(
            thread_frame, 
            from_=1, 
            to=16, 
            textvariable=self.thread_var,
            width=5,
            command=self.update_threads
        )
        thread_spinbox.pack(side=tk.LEFT, padx=5)

        # Statistics Frame
        stats_frame = ttk.LabelFrame(self, text="Statistics")
        stats_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.stats_text = tk.Text(stats_frame, height=10, width=50)
        self.stats_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        # Start statistics update thread
        self.update_thread = threading.Thread(target=self.update_stats, daemon=True)
        self.update_thread.start()

    def update_threads(self):
        try:
            threads = int(self.thread_var.get())
            self.scanner.set_thread_count(threads)
        except ValueError:
            pass

    def start_scanning(self):
        try:
            self.scanner.start_scan()
            self.start_btn['state'] = 'disabled'
            self.stop_btn['state'] = 'normal'
            logging.info(f"Scanner started in tab {self.tab_id}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start scanner: {str(e)}")
            logging.error(f"Failed to start scanner in tab {self.tab_id}: {str(e)}")

    def stop_scanning(self):
        try:
            self.scanner.stop_scan()
            self.start_btn['state'] = 'normal'
            self.stop_btn['state'] = 'disabled'
            logging.info(f"Scanner stopped in tab {self.tab_id}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop scanner: {str(e)}")
            logging.error(f"Failed to stop scanner in tab {self.tab_id}: {str(e)}")

    def update_stats(self):
        while True:
            try:
                if hasattr(self, 'stats_text'):
                    stats = self.scanner.get_statistics()
                    stats_text = (
                        f"Total Scanned: {stats['total_scanned']}\n"
                        f"CPU Processed: {stats['cpu_processed']}\n"
                        f"GPU Processed: {stats['gpu_processed']}\n"
                        f"Found Wallets: {stats['wallets_with_balance']}\n"
                        f"CPU Scan Rate: {stats['cpu_scan_rate']}/min\n"
                        f"GPU Scan Rate: {stats['gpu_scan_rate']}/min\n"
                        f"Queue Size: {stats['queue_size']}\n"
                        f"Last Updated: {datetime.now().strftime('%H:%M:%S')}"
                    )

                    self.stats_text.delete(1.0, tk.END)
                    self.stats_text.insert(tk.END, stats_text)
            except Exception as e:
                logging.error(f"Error updating stats in tab {self.tab_id}: {str(e)}")
            finally:
                threading.Event().wait(1.0)  # Update every second

class BitcoinEducationApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # Create temp directory for wallets
        os.makedirs("C:/temp", exist_ok=True)

        self.title("Bitcoin Wallet Education")
        self.geometry("800x600")

        # Setup main container
        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add connection status indicator
        self.setup_status_bar()

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Add control buttons
        self.setup_controls()

        # Dictionary to store tabs
        self.tabs: Dict[str, WalletScannerTab] = {}

        # Create summary tab
        self.summary_tab = SummaryTab(self.notebook)
        self.notebook.add(self.summary_tab, text="Summary")

        # Create node settings tab
        self.node_settings = NodeSettingsFrame(self.notebook)
        self.notebook.add(self.node_settings, text="Node Settings")

        # Add get_combined_stats method to summary tab
        self.summary_tab.get_combined_stats = self.get_combined_stats

        # Create initial scanner tab
        self.add_scanner_tab()

        # Start connection check thread
        self.start_connection_check()

    def setup_status_bar(self):
        status_frame = ttk.Frame(self.container)
        status_frame.pack(fill=tk.X, pady=(0, 5))

        self.connection_indicator = ttk.Label(
            status_frame, 
            text="●",
            font=("Arial", 12),
            foreground="gray"
        )
        self.connection_indicator.pack(side=tk.LEFT, padx=5)

        self.connection_text = ttk.Label(
            status_frame,
            text="Checking connection..."
        )
        self.connection_text.pack(side=tk.LEFT)

    def start_connection_check(self):
        def check_connection():
            while True:
                try:
                    bitcoin_utils = BitcoinUtils()
                    if bitcoin_utils.get_node_info():
                        self.connection_indicator.config(foreground="green")
                        self.connection_text.config(text="Connected to node")
                    else:
                        self.connection_indicator.config(foreground="red")
                        self.connection_text.config(text="Simulation mode")
                except Exception:
                    self.connection_indicator.config(foreground="red")
                    self.connection_text.config(text="Simulation mode")
                finally:
                    threading.Event().wait(5.0)  # Check every 5 seconds

        thread = threading.Thread(target=check_connection, daemon=True)
        thread.start()

    def setup_controls(self):
        control_frame = ttk.Frame(self.container)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            control_frame,
            text="Add Scanner",
            command=self.add_scanner_tab
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            control_frame,
            text="Remove Current Scanner",
            command=self.remove_current_tab
        ).pack(side=tk.LEFT, padx=5)

    def get_combined_stats(self):
        """Combine statistics from all running scanners."""
        if not self.tabs:
            return None

        combined_stats = {
            'active_scanners': len(self.tabs),
            'total_scanned': 0,
            'cpu_processed': 0,
            'gpu_processed': 0,
            'wallets_with_balance': 0,
            'cpu_scan_rate': 0,
            'gpu_scan_rate': 0,
            'queue_size': 0
        }

        for tab in self.tabs.values():
            stats = tab.scanner.get_statistics()
            combined_stats['total_scanned'] += int(stats['total_scanned'].replace(',', ''))
            combined_stats['cpu_processed'] += int(stats['cpu_processed'].replace(',', ''))
            combined_stats['gpu_processed'] += int(stats['gpu_processed'].replace(',', ''))
            combined_stats['wallets_with_balance'] += int(stats['wallets_with_balance'].replace(',', ''))
            combined_stats['cpu_scan_rate'] += float(stats['cpu_scan_rate'])
            combined_stats['gpu_scan_rate'] += float(stats['gpu_scan_rate'])
            combined_stats['queue_size'] += int(stats['queue_size'].replace(',', ''))

        # Format numbers for display
        combined_stats['total_scanned'] = f"{combined_stats['total_scanned']:,}"
        combined_stats['cpu_processed'] = f"{combined_stats['cpu_processed']:,}"
        combined_stats['gpu_processed'] = f"{combined_stats['gpu_processed']:,}"
        combined_stats['wallets_with_balance'] = f"{combined_stats['wallets_with_balance']:,}"
        combined_stats['cpu_scan_rate'] = f"{combined_stats['cpu_scan_rate']:.1f}"
        combined_stats['gpu_scan_rate'] = f"{combined_stats['gpu_scan_rate']:.1f}"
        combined_stats['queue_size'] = f"{combined_stats['queue_size']:,}"

        return combined_stats

    def add_scanner_tab(self):
        if len(self.tabs) >= 4:  # Limit to 4 scanners
            messagebox.showwarning(
                "Limit Reached",
                "Maximum number of scanners (4) reached."
            )
            return

        tab_id = f"scanner_{len(self.tabs) + 1}"
        scanner_tab = WalletScannerTab(self.notebook, tab_id)
        self.notebook.add(scanner_tab, text=f"Scanner {len(self.tabs) + 1}")
        self.tabs[tab_id] = scanner_tab
        self.notebook.select(scanner_tab)

    def remove_current_tab(self):
        current_tab = self.notebook.select()
        if not current_tab or str(current_tab) == str(self.summary_tab) or str(current_tab) == str(self.node_settings): #Added node_settings check
            return

        tab_id = None
        for id, tab in self.tabs.items():
            if str(tab) == str(current_tab):
                tab_id = id
                break

        if tab_id:
            self.tabs[tab_id].stop_scanning()  # Stop the scanner
            self.notebook.forget(current_tab)  # Remove the tab
            del self.tabs[tab_id]  # Remove from our dictionary

    def on_closing(self):
        """Handle application shutdown."""
        try:
            # Stop all scanners
            for tab in self.tabs.values():
                tab.stop_scanning()
            self.quit()
        except Exception as e:
            logging.error(f"Error during shutdown: {str(e)}")
            self.quit()

if __name__ == "__main__":
    try:
        app = BitcoinEducationApp()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        messagebox.showerror("Fatal Error", str(e))