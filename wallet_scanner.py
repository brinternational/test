import time
from typing import Dict
from datetime import datetime
import random
import os
import threading
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import logging
from wallet_generator import WalletGenerator
import base58

class WalletScanner:
    def __init__(self):
        self.total_scanned = 0
        self.wallets_with_balance = []
        self.start_time = None
        self.scanning = False
        self.thread_count = 1  # Default to 1 thread
        self._scan_executor = None
        self._gen_executor = None
        self._futures = []
        self._lock = threading.Lock()
        self.wallet_queue = Queue(maxsize=10000)

        # Ensure wallet save directory exists
        self.save_dir = r"C:\test\temp"
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            logging.info(f"Wallet save directory created/verified: {self.save_dir}")
        except Exception as e:
            logging.error(f"Failed to create wallet directory {self.save_dir}: {str(e)}")

    def _wallet_generator_worker(self):
        """Continuously generate new wallets and add to queue."""
        logging.info("Generator worker started")
        while self.scanning:
            try:
                if self.wallet_queue.qsize() < self.wallet_queue.maxsize * 0.9:
                    word_count = 12  # Standard BIP39 length
                    words, entropy = WalletGenerator.generate_seed_phrase(word_count)

                    wallet_data = {
                        'seed_phrase': ' '.join(words),
                        'entropy': entropy,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

                    self.wallet_queue.put(wallet_data)
                else:
                    time.sleep(0.01)
            except Exception as e:
                logging.error(f"Generator worker error: {str(e)}")
                continue

    def _scan_worker(self):
        """Worker function for scanning thread."""
        logging.info("Scan worker started")
        while self.scanning:
            try:
                try:
                    wallet_data = self.wallet_queue.get(timeout=0.1)
                except Empty:
                    continue

                entropy = wallet_data['entropy']
                version_byte = b'\x00'  # mainnet
                combined = version_byte + entropy[:20]
                checksum = self.generate_checksum(combined)
                address = base58.b58encode(combined + checksum).decode('utf-8')

                # Mock balance check (random for demo)
                balance = random.randint(0, 100000) / 100000000.0

                with self._lock:
                    self.total_scanned += 1
                    if balance > 0:
                        wallet_info = {
                            'seed_phrase': wallet_data['seed_phrase'],
                            'address': address,
                            'balance': balance,
                            'found_at': wallet_data['timestamp']
                        }
                        self.wallets_with_balance.append(wallet_info)
                        self._save_to_file(wallet_info)

            except Exception as e:
                logging.error(f"Scanner worker error: {str(e)}")
                continue

    @staticmethod
    def generate_checksum(payload: bytes) -> bytes:
        """Generate double SHA256 checksum."""
        import hashlib
        return hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]

    def start_scan(self):
        """Start or resume scanning."""
        try:
            with self._lock:
                if not self.scanning:
                    logging.info(f"Starting scan with {self.thread_count} worker threads")
                    self.scanning = True
                    self.start_time = time.time()

                    # Shutdown existing executors
                    if self._scan_executor:
                        self._scan_executor.shutdown(wait=False)
                        self._scan_executor = None
                    if self._gen_executor:
                        self._gen_executor.shutdown(wait=False)
                        self._gen_executor = None

                    # Clear futures list
                    self._futures = []

                    # Create separate executors for generator and scanners
                    self._gen_executor = ThreadPoolExecutor(max_workers=1)
                    self._scan_executor = ThreadPoolExecutor(max_workers=self.thread_count)

                    # Start generator thread first
                    gen_future = self._gen_executor.submit(self._wallet_generator_worker)
                    self._futures = [gen_future]  # Generator is always first

                    # Start scan workers
                    for _ in range(self.thread_count):
                        scan_future = self._scan_executor.submit(self._scan_worker)
                        self._futures.append(scan_future)

                    logging.info(f"Started {self.thread_count} scan workers plus 1 generator")

        except Exception as e:
            logging.error(f"Error starting scan: {str(e)}")
            self.scanning = False
            self._shutdown_executors()

    def _shutdown_executors(self):
        """Safely shut down thread pool executors."""
        if self._scan_executor:
            self._scan_executor.shutdown(wait=False)
            self._scan_executor = None
        if self._gen_executor:
            self._gen_executor.shutdown(wait=False)
            self._gen_executor = None

    def stop_scan(self):
        """Stop scanning."""
        with self._lock:
            if self.scanning:
                logging.info("Stopping scan...")
                self.scanning = False
                self._shutdown_executors()
                self._futures = []
                logging.info("Scan stopped")

    def get_statistics(self):
        """Get current scanning statistics."""
        with self._lock:
            elapsed_time = time.time() - (self.start_time or time.time())
            scan_rate = self.total_scanned / (elapsed_time / 60) if elapsed_time > 0 else 0

            # Count only scan workers (excluding generator)
            active_scan_threads = sum(1 for f in self._futures[1:] if not f.done())

            return {
                'total_scanned': self.total_scanned,
                'wallets_with_balance': len(self.wallets_with_balance),
                'scan_rate': round(scan_rate, 2),
                'active_threads': active_scan_threads,
                'queue_size': self.wallet_queue.qsize()
            }

    def set_thread_count(self, count: int):
        """Set the number of scanning threads."""
        if count < 1:
            raise ValueError("Thread count must be at least 1")

        with self._lock:
            old_count = self.thread_count
            self.thread_count = count
            logging.info(f"Thread count changed from {old_count} to {count}")

            # If scanning is active, restart with new thread count
            if self.scanning:
                self.stop_scan()
                self.start_scan()

    def _save_to_file(self, wallet_info: Dict):
        """Save wallet with balance to file."""
        try:
            filepath = os.path.join(self.save_dir, "wallets.txt")

            with open(filepath, 'a') as f:
                f.write(f"\n=== Wallet Found at {wallet_info['found_at']} ===\n")
                f.write(f"Seed Phrase: {wallet_info['seed_phrase']}\n")
                f.write(f"Address: {wallet_info['address']}\n")
                f.write(f"Balance: {wallet_info['balance']} BTC\n")
                f.write("="*50 + "\n")

            logging.info(f"Saved wallet with balance {wallet_info['balance']} BTC to {filepath}")

        except Exception as e:
            logging.error(f"Error saving wallet to {filepath}: {str(e)}")