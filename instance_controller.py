import subprocess
import tkinter as tk
from tkinter import ttk
import psutil
import sys
import os
import logging
from typing import Dict, List
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
        if instance_id not in self.instances:
            return False

        try:
            process = self.instances[instance_id]
            if os.name == 'nt':
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
            else:
                process.terminate()
            process.wait(timeout=5)
            del self.instances[instance_id]
            logging.info(f"Stopped instance: {instance_id}")
            return True

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

class InstanceManagerFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.controller = InstanceController()
        self.setup_ui()

    def setup_ui(self):
        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Title
        title = ttk.Label(
            self,
            text="Bitcoin Wallet Scanner - Instance Manager",
            style="Title.TLabel"
        )
        title.grid(row=0, column=0, pady=10)

        # Instance status frame
        status_frame = ttk.Frame(self)
        status_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)

        # Control buttons frame
        btn_frame = ttk.Frame(status_frame)
        btn_frame.grid(row=0, column=0, pady=5, sticky="ew")

        ttk.Button(
            btn_frame,
            text="Start New Instance",
            command=self.start_instance,
            style="Action.TButton",
            width=20
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Stop All Instances",
            command=self.stop_all_instances,
            width=20
        ).pack(side=tk.LEFT, padx=5)

        # Instances list with enhanced information
        self.tree = ttk.Treeview(
            self,
            columns=("ID", "PID", "CPU", "Memory", "Rate", "Scanned", "Found", "Status", "Action"),
            show="headings",
            height=6
        )

        # Configure columns
        columns = [
            ("ID", "Instance ID", 100),
            ("PID", "Process ID", 80),
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
        self.status_var = tk.StringVar(value="Ready to start instances")
        status_label = ttk.Label(
            self,
            textvariable=self.status_var,
            style="Info.TLabel"
        )
        status_label.grid(row=3, column=0, pady=5)

        # Bind click event for stop buttons
        self.tree.bind('<ButtonRelease-1>', self.handle_click)

        # Start auto-refresh
        self.update_instance_list()

    def start_instance(self):
        if self.controller.start_instance():
            self.status_var.set(f"Started new instance ({datetime.now().strftime('%H:%M:%S')})")
        else:
            self.status_var.set("Failed to start instance - maximum limit reached")

    def stop_all_instances(self):
        self.controller.stop_all_instances()
        self.status_var.set(f"Stopped all instances ({datetime.now().strftime('%H:%M:%S')})")

    def handle_click(self, event):
        """Handle click events on the treeview."""
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            item = self.tree.identify_row(event.y)
            if column == "#9":  # Action column
                instance_id = self.tree.item(item)['values'][0]
                if self.controller.stop_instance(instance_id):
                    self.status_var.set(f"Stopped instance {instance_id}")
                else:
                    self.status_var.set(f"Failed to stop instance {instance_id}")

    def update_instance_list(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add current instances
        for info in self.controller.get_instances_info():
            # Handle the memory_percent formatting
            memory_percent = info.get('memory_percent', 'N/A')
            if isinstance(memory_percent, (int, float)):
                memory_display = f"{memory_percent:.1f}%"
            else:
                memory_display = "N/A"

            self.tree.insert(
                "",
                tk.END,
                values=(
                    info['id'],
                    info['pid'],
                    f"{info.get('cpu_percent', 'N/A')}%",
                    memory_display,
                    info.get('scan_rate', 'N/A'),
                    info.get('wallets_scanned', 'N/A'),
                    info.get('wallets_with_balance', 'N/A'),
                    info['status'],
                    "Stop"  # Clickable stop button
                )
            )

        # Schedule next update
        self.after(1000, self.update_instance_list)