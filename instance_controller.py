import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import sys
import os
import logging
import uuid
from typing import Dict, List, Optional
from datetime import datetime
from wallet_scanner import WalletScanner


class InstanceController:
    def __init__(self):
        self.instances: Dict[str, subprocess.Popen] = {}
        self.max_instances = 4
        self.wallet_scanner = WalletScanner()

    def start_instance(self) -> bool:
        """Start a new wallet scanner instance."""
        if len(self.instances) >= self.max_instances:
            return False

        try:
            instance_id = f"instance_{len(self.instances) + 1}"

            process = subprocess.Popen(
                [sys.executable, "main.py", "--instance-id", instance_id],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )

            self.instances[instance_id] = process
            logging.info(f"Started new instance: {instance_id}")
            return True

        except Exception as e:
            logging.error(f"Failed to start instance: {str(e)}")
            return False

    def stop_instance(self, instance_id: str) -> bool:
        """Stop a specific instance by ID."""
        if not instance_id:
            logging.error("Invalid instance ID provided")
            return False

        if instance_id not in self.instances:
            logging.error(f"Instance {instance_id} not found")
            return False

        try:
            process = self.instances[instance_id]
            if os.name == 'nt':
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
            else:
                process.terminate()
            process.wait(timeout=5)
            del self.instances[instance_id]
            logging.info(f"Successfully stopped instance: {instance_id}")
            return True

        except subprocess.TimeoutExpired:
            logging.error(f"Timeout while stopping instance {instance_id}")
            return False
        except Exception as e:
            logging.error(f"Failed to stop instance {instance_id}: {str(e)}")
            return False

    def stop_all_instances(self):
        instance_ids = list(self.instances.keys())
        for instance_id in instance_ids:
            self.stop_instance(instance_id)

    def get_instance_count(self) -> int:
        return len(self.instances)

    def get_instances_info(self) -> List[Dict]:
        info = []
        for instance_id, process in self.instances.items():
            if process.poll() is None:  # Check if process is still running
                try:
                    proc = psutil.Process(process.pid)
                    stats = self.wallet_scanner.get_statistics()
                    info.append({
                        'id': instance_id,
                        'pid': process.pid,
                        'cpu_percent': proc.cpu_percent(),
                        'memory_percent': proc.memory_percent(),
                        'status': 'Running',
                        'scan_rate': f"{stats.get('cpu_scan_rate', 0) + stats.get('gpu_scan_rate', 0):.1f}/min",
                        'wallets_scanned': stats.get('total_scanned', 0),
                        'wallets_with_balance': stats.get('wallets_with_balance', 0)
                    })
                except:
                    info.append({
                        'id': instance_id,
                        'pid': process.pid,
                        'status': 'Unknown'
                    })
        return info


class ProcessManagerFrame(ttk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.main_app = main_app
        self.processes: Dict[str, WalletScanner] = {}
        self.max_processes = 4
        self.setup_ui()

    def setup_ui(self):
        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Title
        title = ttk.Label(
            self,
            text="Bitcoin Wallet Scanner - Process Manager",
            style="Title.TLabel"
        )
        title.grid(row=0, column=0, pady=10)

        # Process status frame
        status_frame = ttk.Frame(self)
        status_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)

        # Control buttons frame
        btn_frame = ttk.Frame(status_frame)
        btn_frame.grid(row=0, column=0, pady=5, sticky="ew")

        ttk.Button(
            btn_frame,
            text="Start New Process",
            command=self.start_process,
            style="Action.TButton",
            width=20
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Stop All Processes",
            command=self.stop_all_processes,
            width=20
        ).pack(side=tk.LEFT, padx=5)

        # Process list with enhanced information
        self.tree = ttk.Treeview(
            self,
            columns=("ID", "CPU", "Memory", "Rate", "Scanned", "Found", "Status", "Action"),
            show="headings",
            height=6
        )

        # Configure columns
        columns = [
            ("ID", "Process ID", 100),
            ("CPU", "CPU %", 70),
            ("Memory", "Memory %", 80),
            ("Rate", "Scan Rate", 100),
            ("Scanned", "Wallets", 80),
            ("Found", "Found", 70),
            ("Status", "Status", 80),
            ("Action", "Action", 80)
        ]

        for col, heading, width in columns:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width)

        self.tree.grid(row=2, column=0, pady=10, padx=10, sticky="nsew")

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Status bar
        self.status_var = tk.StringVar(value="Ready to start processes")
        status_label = ttk.Label(
            self,
            textvariable=self.status_var,
            style="Info.TLabel"
        )
        status_label.grid(row=3, column=0, pady=5)

        # Bind click event for stop buttons
        self.tree.bind('<ButtonRelease-1>', self.handle_click)

        # Start auto-refresh
        self.update_process_list()

    def start_process(self):
        """Start a new wallet scanner process in a new tab."""
        if len(self.processes) >= self.max_processes:
            messagebox.showwarning(
                "Process Limit",
                f"Maximum number of processes ({self.max_processes}) reached."
            )
            return

        try:
            process_id = str(uuid.uuid4())[:8]
            scanner = WalletScanner()

            # Create new tab for this process
            process_frame = self.main_app.add_process_tab(process_id)
            if process_frame:
                self.processes[process_id] = scanner
                self.status_var.set(f"Started new process {process_id}")
                logging.info(f"Started new process: {process_id}")

        except Exception as e:
            error_message = f"Failed to start process: {str(e)}"
            logging.error(error_message)
            messagebox.showerror("Error", error_message)

    def stop_process(self, process_id: str) -> bool:
        """Stop a specific process by ID."""
        if process_id not in self.processes:
            return False

        try:
            scanner = self.processes[process_id]
            scanner.stop_scan()
            self.main_app.remove_process_tab(process_id)
            del self.processes[process_id]
            logging.info(f"Successfully stopped process: {process_id}")
            return True

        except Exception as e:
            logging.error(f"Failed to stop process {process_id}: {str(e)}")
            return False

    def stop_all_processes(self):
        """Stop all running processes."""
        process_ids = list(self.processes.keys())
        for process_id in process_ids:
            self.stop_process(process_id)
        self.status_var.set(f"Stopped all processes ({datetime.now().strftime('%H:%M:%S')})")

    def handle_click(self, event):
        """Handle click events on the treeview."""
        try:
            region = self.tree.identify("region", event.x, event.y)
            if region == "cell":
                column = self.tree.identify_column(event.x)
                item = self.tree.identify_row(event.y)
                if column == "#8":  # Action column
                    process_id = self.tree.item(item)['values'][0]
                    if process_id:
                        if self.stop_process(process_id):
                            self.status_var.set(f"Successfully stopped process {process_id}")
                        else:
                            self.status_var.set(f"Failed to stop process {process_id}")
        except Exception as e:
            logging.error(f"Error handling process stop click: {str(e)}")
            self.status_var.set("Error stopping process. Check logs for details.")

    def update_process_list(self):
        """Update the process list display."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add current processes
        for process_id, scanner in self.processes.items():
            try:
                stats = scanner.get_statistics()

                # Calculate total scan rate
                cpu_rate = float(stats.get('cpu_scan_rate', 0))
                gpu_rate = float(stats.get('gpu_scan_rate', 0))
                total_rate = f"{cpu_rate + gpu_rate:.1f}/min"

                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        process_id,
                        f"{stats.get('cpu_usage', 'N/A')}%",
                        f"{stats.get('memory_usage', 'N/A')}%",
                        total_rate,
                        stats.get('total_scanned', 'N/A'),
                        stats.get('wallets_with_balance', 'N/A'),
                        "Running" if scanner.scanning else "Stopped",
                        "Stop"
                    )
                )
            except Exception as e:
                logging.error(f"Error updating process {process_id}: {str(e)}")

        # Schedule next update
        self.after(1000, self.update_process_list)