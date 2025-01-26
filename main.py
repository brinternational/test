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
    level=logging.DEBUG,  # Changed from INFO to DEBUG
    format='%(asctime)s - %(levelname)s - [%(threadName)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bitcoin_wallet.log')
    ]
)

# Add simulation mode flag
class NodeSettingsFrame(ttk.Frame):
    def __init__(self, parent):
        logging.debug("Initializing NodeSettingsFrame")
        super().__init__(parent)
        self.bitcoin_utils = BitcoinUtils()
        self._connection_check_after = None
        self.simulation_mode = False
        self.setup_ui()
        self.start_connection_check()
        logging.debug("NodeSettingsFrame initialization complete")

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

        # RPC Username
        user_frame = ttk.Frame(settings_container)
        user_frame.pack(fill=tk.X, pady=2)
        ttk.Label(user_frame, text="RPC Username:").pack(side=tk.LEFT, padx=5)
        self.user_var = tk.StringVar(value=self.bitcoin_utils.RPC_USER)
        ttk.Entry(user_frame, textvariable=self.user_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # RPC Password
        pass_frame = ttk.Frame(settings_container)
        pass_frame.pack(fill=tk.X, pady=2)
        ttk.Label(pass_frame, text="RPC Password:").pack(side=tk.LEFT, padx=5)
        self.pass_var = tk.StringVar(value=self.bitcoin_utils.RPC_PASS)
        ttk.Entry(pass_frame, textvariable=self.pass_var, show="*").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

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
                self.user_var.get(),
                self.pass_var.get()
            )

            # Save wallet directory and all settings
            wallet_dir = self.wallet_dir_var.get()
            os.makedirs(wallet_dir, exist_ok=True)

            # Save to config file
            self.bitcoin_utils.save_config(
                url=self.url_var.get(),
                port=self.port_var.get(),
                username=self.user_var.get(),
                password=self.pass_var.get(),
                wallet_dir=wallet_dir
            )

            messagebox.showinfo("Success", "Settings saved successfully")
            self.check_connection()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def check_connection(self):
        """Test connection to Bitcoin node with non-blocking checks."""
        logging.debug("Starting node connection check")
        try:
            success = self.bitcoin_utils.test_connection_async()
            logging.debug(f"Connection test result: {'Success' if success else 'Failed'}")
            if success:
                node_info = self.bitcoin_utils.get_node_info()
                logging.info(f"Connected to node - Info: {node_info}")
                self.status_indicator.config(foreground="green")
                self.status_label.config(text="Connected", foreground="green")

                status_text = (
                    f"Connected to Bitcoin Node\n"
                    f"Network: {node_info['chain']}\n"
                    f"Block Height: {node_info['blocks']:,}\n"
                    f"Connected Peers: {node_info['peers']}"
                )

                self.info_text.delete(1.0, tk.END)
                self.info_text.insert(tk.END, status_text)
                self.simulation_mode = False
            else:
                logging.warning("Node connection failed, enabling simulation mode")
                self.enable_simulation_mode("Node connection failed")
        except Exception as e:
            logging.error(f"Connection check error: {str(e)}", exc_info=True)
            self.enable_simulation_mode(str(e))

    def enable_simulation_mode(self, error_msg):
        """Enable simulation mode with appropriate UI updates."""
        self.simulation_mode = True
        self.status_indicator.config(foreground="orange")
        self.status_label.config(text="Simulation Mode", foreground="orange")

        status_text = (
            f"Running in Simulation Mode\n"
            f"Node Error: {error_msg}\n\n"
            f"The application will run with simulated data.\n"
            f"Some features may be limited."
        )

        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, status_text)

    def start_connection_check(self):
        """Start periodic connection checks in a non-blocking way."""
        def schedule_check():
            if hasattr(self, 'status_label'):
                self.check_connection()
                self._connection_check_after = self.after(5000, schedule_check)

        schedule_check()

    def on_destroy(self):
        """Clean up scheduled tasks."""
        if self._connection_check_after:
            self.after_cancel(self._connection_check_after)


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
        self._stats_update_after_id = None
        self._is_updating = False
        self.simulation_mode = False
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

        self.start_btn = ttk.Button(btn_frame, text="▶ Start", command=self.toggle_scanning)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="Stop Scanning", command=self.stop_scanning)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn['state'] = 'disabled'

        # Thread count control
        thread_frame = ttk.Frame(status_frame)
        thread_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(thread_frame, text="Threads:").pack(side=tk.LEFT, padx=5)
        self.thread_var = tk.StringVar(value="4")
        self.thread_spinbox = ttk.Spinbox(
            thread_frame, 
            from_=1, 
            to=16, 
            textvariable=self.thread_var,
            width=5,
            command=self.update_threads
        )
        self.thread_spinbox.pack(side=tk.LEFT, padx=5)

        # Statistics Frame
        stats_frame = ttk.LabelFrame(self, text="Statistics")
        stats_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.stats_text = tk.Text(stats_frame, height=10, width=50)
        self.stats_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        # Don't start the update thread immediately
        self.schedule_stats_update()

    def schedule_stats_update(self):
        """Schedule the next statistics update using tkinter's after()"""
        if not self._is_updating and hasattr(self, 'stats_text'):
            self._is_updating = True
            self.after(1000, self._update_stats)

    def _update_stats(self):
        """Update statistics in a non-blocking way"""
        try:
            stats = self.get_statistics()
            if stats and hasattr(self, 'stats_text'):
                stats_text = (
                    f"=== Node Connection Status ===\n"
                    f"Network: {stats['node_chain']}\n"
                    f"Block Height: {stats['node_height']:,}\n"
                    f"\n=== Scan Statistics ===\n"
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
            self._is_updating = False
            # Schedule next update if we're still visible
            if self.winfo_viewable():
                self.schedule_stats_update()

    def update_threads(self):
        """Update thread count with improved error handling"""
        try:
            threads = int(self.thread_var.get())
            if threads < 1:
                raise ValueError("Thread count must be at least 1")

            # Update thread count in a non-blocking way
            self.after(0, lambda: self._safe_update_threads(threads))
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            self.thread_var.set("4")  # Reset to default

    def _safe_update_threads(self, threads):
        """Safely update thread count without blocking the UI"""
        try:
            self.scanner.set_thread_count(threads)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update thread count: {str(e)}")
            self.thread_var.set("4")  # Reset to default on error


    def toggle_scanning(self):
        """Toggle wallet scanning with simulation mode support."""
        try:
            # Check if we're in simulation mode
            if hasattr(self.master.master, 'node_settings'):
                self.simulation_mode = self.master.master.node_settings.simulation_mode

            if not self.simulation_mode:
                # Try connecting to node before starting
                success = BitcoinUtils.test_connection_async()
                if not success:
                    if messagebox.askyesno(
                        "Node Connection Failed",
                        "Bitcoin node connection failed. Would you like to continue in simulation mode?"
                    ):
                        self.simulation_mode = True
                    else:
                        return

            # Start or stop scanning based on current state
            if not self.scanner.scanning:
                self.start_scanning()
            else:
                self.stop_scanning()

        except Exception as e:
            messagebox.showerror("Error", f"Error toggling scanner: {str(e)}")

    def start_scanning(self):
        """Start wallet scanning with simulation mode support."""
        if self.scanner.scanning:
            return

        try:
            self.scanner.start_scan(simulation_mode=self.simulation_mode)
            self.start_btn.config(text="■ Stop", state='normal')
            self.thread_spinbox.config(state='disabled')
            self.schedule_stats_update()

            logging.info(f"Scanner started in tab {self.tab_id} (Simulation: {self.simulation_mode})")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start scanner: {str(e)}")
            logging.error(f"Failed to start scanner in tab {self.tab_id}: {str(e)}")

    def stop_scanning(self):
        """Stop wallet scanning."""
        if not self.scanner.scanning:
            return

        try:
            self.scanner.stop_scan()
            self.start_btn.config(text="▶ Start", state='normal')
            self.thread_spinbox.config(state='normal')
            logging.info(f"Scanner stopped in tab {self.tab_id}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop scanner: {str(e)}")
            logging.error(f"Failed to stop scanner in tab {self.tab_id}: {str(e)}")

    def update_stats(self):
        while True:
            try:
                if hasattr(self, 'stats_text'):
                    stats = self.get_statistics()
                    if stats:
                        stats_text = (
                            f"=== Node Connection Status ===\n"
                            f"Network: {stats['node_chain']}\n"
                            f"Block Height: {stats['node_height']:,}\n"
                            f"\n=== Scan Statistics ===\n"
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

    def get_statistics(self):
        """Get current node information."""
        try:
            # Verify live node connection
            BitcoinUtils.verify_live_node()
            node_info = BitcoinUtils.get_node_info()

            cpu_rate_per_min = self.scanner.cpu_scan_rate * 60
            gpu_rate_per_min = self.scanner.gpu_scan_rate * 60
            
            stats = {
                'total_scanned': f"{self.scanner.shared_total.value:,}",
                'cpu_processed': f"{self.scanner.cpu_processed.value:,}",
                'gpu_processed': f"{self.scanner.gpu_processed.value:,}",
                'wallets_with_balance': f"{self.scanner.shared_balance_count.value:,}",
                'cpu_scan_rate': f"{cpu_rate_per_min:,.1f}",
                'gpu_scan_rate': f"{gpu_rate_per_min:,.1f}",
                'queue_size': f"{self.scanner.wallet_queue.qsize():,}",
                'node_chain': node_info['chain'],
                'node_height': node_info['blocks']
            }
            return stats

        except Exception as e:
            logging.error(f"Instance {self.tab_id}: Failed to get statistics - no live node connection: {str(e)}")
            self.stop_scanning()  # Stop scanning if we lose node connection
            raise


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
                    bitcoin_utils.verify_live_node()
                    node_info = bitcoin_utils.get_node_info()

                    self.connection_indicator.config(foreground="green")
                    self.connection_text.config(text=f"Connected to node - Chain: {node_info['chain']}")
                except Exception as e:
                    self.connection_indicator.config(foreground="red")
                    self.connection_text.config(text=f"Node Error: {str(e)}")
                    logging.error(f"Node connection error: {str(e)}")
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
            'cpu_scan_rate': 0.0,
            'gpu_scan_rate': 0.0,
            'queue_size': 0
        }

        for tab in self.tabs.values():
            stats = tab.scanner.get_statistics()
            # Convert string numbers with commas to float/int
            combined_stats['total_scanned'] += int(stats['total_scanned'].replace(',', ''))
            combined_stats['cpu_processed'] += int(stats['cpu_processed'].replace(',', ''))
            combined_stats['gpu_processed'] += int(stats['gpu_processed'].replace(',', ''))
            combined_stats['wallets_with_balance'] += int(stats['wallets_with_balance'].replace(',', ''))
            combined_stats['cpu_scan_rate'] += float(stats['cpu_scan_rate'].replace(',', ''))
            combined_stats['gpu_scan_rate'] += float(stats['gpu_scan_rate'].replace(',', ''))
            combined_stats['queue_size'] += int(stats['queue_size'].replace(',', ''))

        # Format numbers for display
        for key in ['total_scanned', 'cpu_processed', 'gpu_processed', 'wallets_with_balance', 'queue_size']:
            combined_stats[key] = f"{combined_stats[key]:,}"

        # Format rates with one decimal place
        combined_stats['cpu_scan_rate'] = f"{combined_stats['cpu_scan_rate']:.1f}"
        combined_stats['gpu_scan_rate'] = f"{combined_stats['gpu_scan_rate']:.1f}"

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