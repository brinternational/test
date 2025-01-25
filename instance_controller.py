import subprocess
import tkinter as tk
from tkinter import ttk
import psutil
import sys
import os
import logging
from typing import Dict, List
from datetime import datetime

class InstanceController:
    def __init__(self):
        self.instances: Dict[str, subprocess.Popen] = {}
        self.max_instances = 4
        
    def start_instance(self) -> bool:
        """Start a new wallet scanner instance."""
        if len(self.instances) >= self.max_instances:
            return False
            
        try:
            # Create a unique identifier for this instance
            instance_id = f"instance_{len(self.instances) + 1}"
            
            # Start the instance as a separate process
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
        """Stop a specific wallet scanner instance."""
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
        """Stop all running wallet scanner instances."""
        instance_ids = list(self.instances.keys())
        for instance_id in instance_ids:
            self.stop_instance(instance_id)
    
    def get_instance_count(self) -> int:
        """Get the number of running instances."""
        return len(self.instances)
    
    def get_instances_info(self) -> List[Dict]:
        """Get information about all running instances."""
        info = []
        for instance_id, process in self.instances.items():
            if process.poll() is None:  # Check if process is still running
                try:
                    proc = psutil.Process(process.pid)
                    info.append({
                        'id': instance_id,
                        'pid': process.pid,
                        'cpu_percent': proc.cpu_percent(),
                        'memory_percent': proc.memory_percent(),
                        'status': 'Running'
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
        
        # Title with smaller font
        title = ttk.Label(
            self,
            text="Bitcoin Wallet Scanner - Instance Manager",
            style="Title.TLabel"
        )
        title.grid(row=0, column=0, pady=10)
        
        # Control buttons frame
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, pady=5)
        
        ttk.Button(
            btn_frame,
            text="Start New Instance",
            command=self.start_instance,
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Stop All Instances",
            command=self.stop_all_instances,
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        # Instances list
        self.tree = ttk.Treeview(
            self,
            columns=("ID", "PID", "CPU", "Memory", "Status", "Action"),
            show="headings",
            height=6
        )
        
        # Configure columns
        self.tree.heading("ID", text="Instance ID")
        self.tree.heading("PID", text="Process ID")
        self.tree.heading("CPU", text="CPU %")
        self.tree.heading("Memory", text="Memory %")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Action", text="Action")
        
        # Set column widths
        self.tree.column("ID", width=100)
        self.tree.column("PID", width=80)
        self.tree.column("CPU", width=70)
        self.tree.column("Memory", width=80)
        self.tree.column("Status", width=80)
        self.tree.column("Action", width=80)
        
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
        
        # Start auto-refresh
        self.update_instance_list()
        
    def start_instance(self):
        """Start a new wallet scanner instance."""
        if self.controller.start_instance():
            self.status_var.set(f"Started new instance ({datetime.now().strftime('%H:%M:%S')})")
        else:
            self.status_var.set("Failed to start instance - maximum limit reached")
            
    def stop_all_instances(self):
        """Stop all running instances."""
        self.controller.stop_all_instances()
        self.status_var.set(f"Stopped all instances ({datetime.now().strftime('%H:%M:%S')})")
        
    def update_instance_list(self):
        """Update the instances list view."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Add current instances
        for info in self.controller.get_instances_info():
            self.tree.insert(
                "",
                tk.END,
                values=(
                    info['id'],
                    info['pid'],
                    f"{info.get('cpu_percent', 'N/A')}%",
                    f"{info.get('memory_percent', 'N/A'):.1f}%",
                    info['status'],
                    "Stop"
                )
            )
            
        # Schedule next update
        self.after(1000, self.update_instance_list)
