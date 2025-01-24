import time
from typing import Dict, List
from datetime import datetime
import random
import os
import subprocess
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, wait
import logging

BUILD_TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class WalletScanner:
    def __init__(self):
        self.total_scanned = 0
        self.wallets_with_balance = []
        self.start_time = None
        self.scanning = False
        self.thread_count = 1
        self._executor = None
        self._futures = []
        self._lock = threading.Lock()
        self.wallet_queue = Queue()

    def set_thread_count(self, count: int):
        """Dynamically adjust the number of scanning threads."""
        if count < 1:
            raise ValueError("Thread count must be at least 1")

        with self._lock:
            if self._executor:
                # Wait for existing futures if reducing threads
                if count < self.thread_count:
                    done_futures = []
                    remaining_futures = []
                    for future in self._futures:
                        if future.done():
                            done_futures.append(future)
                        else:
                            remaining_futures.append(future)
                    # Keep only the desired number of running futures
                    self._futures = remaining_futures[:count]
                    # Remove completed futures
                    for future in done_futures:
                        if future in self._futures:
                            self._futures.remove(future)

                # Shutdown existing executor and create new one
                self._executor.shutdown(wait=False)

            self.thread_count = count
            self._executor = ThreadPoolExecutor(max_workers=count)

            # Start new scanning threads if needed
            if self.scanning:
                while len(self._futures) < count:
                    self._futures.append(self._executor.submit(self._scan_worker))

    def start_scan(self):
        """Start or resume scanning."""
        with self._lock:
            if not self.scanning:
                self.start_time = time.time()
                self.scanning = True

                # Initialize thread pool if needed
                if not self._executor:
                    self.set_thread_count(self.thread_count)

                # Start scanning threads
                while len(self._futures) < self.thread_count:
                    self._futures.append(self._executor.submit(self._scan_worker))

    def stop_scan(self):
        """Stop scanning."""
        with self._lock:
            if self.scanning:
                self.scanning = False
                if self._executor:
                    # Wait for threads to complete
                    self._executor.shutdown(wait=True)
                    self._executor = None
                    self._futures = []

    def _scan_worker(self):
        """Worker function for scanning thread."""
        while self.scanning:
            try:
                # Generate random wallet data for demonstration
                wallet_info = {
                    'address': f"bc1{os.urandom(20).hex()}",
                    'balance': random.random() * 0.1,
                    'last_transaction': datetime.now().strftime("%Y-%m-%d")
                }

                with self._lock:
                    self.total_scanned += 1
                    if wallet_info['balance'] > 0:
                        self.wallets_with_balance.append(wallet_info)
                        self._save_to_file(wallet_info)

                # Simulate scanning delay
                time.sleep(0.1)

            except Exception as e:
                logging.error(f"Scanner worker error: {str(e)}")
                continue

    def add_wallet(self, wallet_info: Dict):
        """Add a wallet to the scan results."""
        with self._lock:
            self.total_scanned += 1
            if wallet_info.get('balance', 0) > 0:
                self.wallets_with_balance.append(wallet_info)
                self._save_to_file(wallet_info)

    def get_scan_rate(self) -> float:
        """Calculate wallets scanned per minute."""
        if not self.start_time or not self.scanning:
            return 0.0
        elapsed_minutes = (time.time() - self.start_time) / 60
        return self.total_scanned / elapsed_minutes if elapsed_minutes > 0 else 0

    def get_statistics(self) -> Dict:
        """Get current scanning statistics."""
        with self._lock:
            return {
                'total_scanned': self.total_scanned,
                'wallets_with_balance': len(self.wallets_with_balance),
                'scan_rate': round(self.get_scan_rate(), 2),
                'active_threads': len(self._futures) if self._futures else 0
            }

    def _save_to_file(self, wallet_info: Dict):
        """Save wallet with balance to file."""
        try:
            # Ensure temp directory exists
            os.makedirs(os.path.join(os.getcwd(), "temp"), exist_ok=True)

            # Save to temp/wallets.txt with today's date
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            filepath = os.path.join(os.getcwd(), "temp", "wallets.txt")

            with open(filepath, 'a') as f:
                f.write(f"\n=== Wallet Found at {timestamp} (Created on {BUILD_TIMESTAMP}) ===\n")
                f.write(f"Address: {wallet_info['address']}\n")
                f.write(f"Balance: {wallet_info['balance']} BTC\n")
                f.write(f"Last Transaction: {wallet_info['last_transaction']}\n")
                f.write("="*40 + "\n")

            # Commit changes to git if in a git repository
            try:
                subprocess.run(['git', 'add', filepath], check=True)
                subprocess.run(['git', 'commit', '-m', f"Add wallet scan result from {timestamp}"], check=True)
                subprocess.run(['git', 'push'], check=True)
            except subprocess.CalledProcessError as e:
                logging.warning(f"Git operation warning: {str(e)}")
            except Exception as e:
                logging.error(f"Git error: {str(e)}")

        except Exception as e:
            logging.error(f"Error saving wallet: {str(e)}")

    def git_commit_changes(self, message: str):
        """Commit changes to git repository"""
        try:
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', message], check=True)
            return True, "Changes committed to git successfully"
        except subprocess.CalledProcessError as e:
            return False, f"Git commit failed: {str(e)}"

    def git_commit_and_push(self, message: str):
        """Commit and push changes to git repository"""
        try:
            # Initialize git if needed (idempotent)
            subprocess.run(['git', 'init'], check=True)

            # Configure git if not already done
            try:
                subprocess.run(['git', 'config', 'user.email', "wallet-education@example.com"], check=True)
                subprocess.run(['git', 'config', 'user.name', "Wallet Education App"], check=True)
            except subprocess.CalledProcessError:
                pass  # Ignore if already configured

            # Add and commit changes
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', message], check=True)

            # Push changes
            subprocess.run(['git', 'push', '--force', 'origin', 'main'], check=True)
            return True, "Changes committed and pushed to git successfully"
        except subprocess.CalledProcessError as e:
            return False, f"Git operation failed: {str(e)}"