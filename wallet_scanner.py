import time
from typing import Dict, List
from datetime import datetime
import random
import os
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import logging
from wallet_generator import WalletGenerator
import subprocess

class WalletScanner:
    def __init__(self):
        self.total_scanned = 0
        self.wallets_with_balance = []
        self.start_time = None
        self.scanning = False
        self.thread_count = 4  # Default to 4 threads
        self._executor = None
        self._futures = []
        self._lock = threading.Lock()
        self.wallet_queue = Queue(maxsize=1000)  # Buffer for generated wallets

    def generate_wallet_data(self):
        """Generate new wallet data using WalletGenerator."""
        try:
            # Generate random entropy for new seed phrase
            word_count = 12  # Can be adjusted to 15, 18, 21, or 24
            words, entropy = WalletGenerator.generate_seed_phrase(word_count)

            # Derive addresses from the seed
            seed = entropy  # In production, would apply BIP39 seed derivation
            addresses = WalletGenerator.derive_addresses(seed)

            return {
                'seed_phrase': ' '.join(words),
                'addresses': addresses
            }
        except Exception as e:
            logging.error(f"Error generating wallet: {str(e)}")
            return None

    def _wallet_generator_worker(self):
        """Continuously generate new wallets and add to queue."""
        while self.scanning:
            try:
                if self.wallet_queue.qsize() < 1000:  # Keep queue filled
                    wallet_data = self.generate_wallet_data()
                    if wallet_data:
                        self.wallet_queue.put(wallet_data)
                else:
                    time.sleep(0.1)  # Prevent CPU thrashing when queue is full
            except Exception as e:
                logging.error(f"Generator worker error: {str(e)}")
                continue

    def _scan_worker(self):
        """Worker function for scanning thread."""
        while self.scanning:
            try:
                # Get next wallet from queue
                try:
                    wallet_data = self.wallet_queue.get(timeout=1)
                except Queue.Empty:
                    continue

                # Check balances
                addresses = wallet_data['addresses']
                has_balance = False
                total_balance = 0.0

                # Check each address type
                for addr_type in ['legacy_address', 'segwit_address', 'native_segwit']:
                    if addr_type in addresses:
                        balance = float(addresses.get('balance', 0))
                        if balance > 0:
                            has_balance = True
                            total_balance += balance

                with self._lock:
                    self.total_scanned += 1
                    if has_balance:
                        wallet_info = {
                            'seed_phrase': wallet_data['seed_phrase'],
                            'addresses': addresses,
                            'total_balance': total_balance,
                            'found_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        self.wallets_with_balance.append(wallet_info)
                        self._save_to_file(wallet_info)

            except Exception as e:
                logging.error(f"Scanner worker error: {str(e)}")
                continue

    def start_scan(self):
        """Start or resume scanning."""
        with self._lock:
            if not self.scanning:
                self.start_time = time.time()
                self.scanning = True

                # Initialize thread pool if needed
                if not self._executor:
                    self._executor = ThreadPoolExecutor(max_workers=self.thread_count + 1)  # +1 for generator

                # Start wallet generator thread
                self._futures.append(self._executor.submit(self._wallet_generator_worker))

                # Start scanning threads
                for _ in range(self.thread_count):
                    self._futures.append(self._executor.submit(self._scan_worker))

    def stop_scan(self):
        """Stop scanning."""
        with self._lock:
            if self.scanning:
                self.scanning = False
                if self._executor:
                    self._executor.shutdown(wait=True)
                    self._executor = None
                    self._futures = []

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
            elapsed_time = time.time() - (self.start_time or time.time())
            scan_rate = self.total_scanned / (elapsed_time / 60) if elapsed_time > 0 else 0

            return {
                'total_scanned': self.total_scanned,
                'wallets_with_balance': len(self.wallets_with_balance),
                'scan_rate': round(scan_rate, 2),
                'active_threads': len(self._futures) if self._futures else 0,
                'queue_size': self.wallet_queue.qsize()
            }

    def _save_to_file(self, wallet_info: Dict):
        """Save wallet with balance to file."""
        try:
            # Ensure temp directory exists
            os.makedirs(os.path.join(os.getcwd(), "temp"), exist_ok=True)

            # Save to temp/wallets.txt
            filepath = os.path.join(os.getcwd(), "temp", "wallets.txt")

            with open(filepath, 'a') as f:
                f.write(f"\n=== Wallet Found at {wallet_info['found_at']} ===\n")
                f.write(f"Seed Phrase: {wallet_info['seed_phrase']}\n")
                f.write(f"Total Balance: {wallet_info['total_balance']} BTC\n")
                f.write("Addresses:\n")
                for addr_type, addr in wallet_info['addresses'].items():
                    if isinstance(addr, str):  # Only write address strings
                        f.write(f"{addr_type}: {addr}\n")
                f.write("="*50 + "\n")

        except Exception as e:
            logging.error(f"Error saving wallet: {str(e)}")

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