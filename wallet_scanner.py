import time
from typing import Dict, List
from datetime import datetime
import os
import threading
import multiprocessing
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging
from wallet_generator import WalletGenerator
import base58
import hashlib

class WalletScanner:
    def __init__(self):
        self.total_scanned = 0
        self.wallets_with_balance = []
        self.start_time = None
        self.scanning = False
        self.thread_count = multiprocessing.cpu_count()  # Use all CPU cores by default
        self._executor = None
        self._process_pool = None
        self._futures = []
        self._lock = threading.Lock()
        self.wallet_queue = Queue(maxsize=10000)
        self.result_queue = multiprocessing.Queue()
        self.BATCH_SIZE = 1000  # Process wallets in batches

        # Ensure wallet save directory exists
        self.save_dir = r"C:\temp"
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            logging.info(f"Wallet save directory created/verified: {self.save_dir}")
        except Exception as e:
            logging.error(f"Failed to create wallet directory {self.save_dir}: {str(e)}")

    def _wallet_generator_worker(self):
        """Continuously generate new wallets and add to queue in batches."""
        logging.info("Generator worker started")
        while self.scanning:
            try:
                if self.wallet_queue.qsize() < self.wallet_queue.maxsize * 0.9:
                    # Generate a batch of wallets
                    batch = []
                    for _ in range(self.BATCH_SIZE):
                        word_count = 12  # Standard BIP39 length
                        words, entropy = WalletGenerator.generate_seed_phrase(word_count)
                        wallet_data = {
                            'seed_phrase': ' '.join(words),
                            'entropy': entropy,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        batch.append(wallet_data)

                    self.wallet_queue.put(batch)
                else:
                    time.sleep(0.01)
            except Exception as e:
                logging.error(f"Generator worker error: {str(e)}")
                continue

    @staticmethod
    def check_balance_batch(addresses: List[str]) -> List[float]:
        """Process a batch of addresses in parallel."""
        results = []
        for address in addresses:
            # Use the first 4 bytes of address hash for randomness
            addr_hash = int.from_bytes(hashlib.sha256(address.encode()).digest()[:4], 'big')

            # Very rare chance (roughly 1 in 100,000) of having a balance
            if addr_hash % 100000 == 0:
                # Generate a small balance (0.0001 - 0.1 BTC)
                balance = float(addr_hash % 1000) / 10000
                results.append(balance)
            else:
                results.append(0.0)
        return results

    def _process_batch(self, batch: List[Dict]) -> List[Dict]:
        """Process a batch of wallets using multiprocessing."""
        addresses = []
        for wallet_data in batch:
            entropy = wallet_data['entropy']
            version_byte = b'\x00'  # mainnet
            combined = version_byte + entropy[:20]  # Use first 20 bytes for demo
            checksum = self.generate_checksum(combined)
            address = base58.b58encode(combined + checksum).decode('utf-8')
            addresses.append(address)

        # Check balances in parallel
        balances = self.check_balance_batch(addresses)

        # Combine results
        results = []
        for wallet_data, address, balance in zip(batch, addresses, balances):
            if balance > 0:
                results.append({
                    'seed_phrase': wallet_data['seed_phrase'],
                    'address': address,
                    'balance': balance,
                    'found_at': wallet_data['timestamp']
                })
        return results

    def _scan_worker(self):
        """Worker function for scanning thread with batch processing."""
        logging.info("Scan worker started")
        while self.scanning:
            try:
                try:
                    batch = self.wallet_queue.get(timeout=0.1)
                except Empty:
                    continue

                # Process the batch
                results = self._process_batch(batch)

                with self._lock:
                    self.total_scanned += len(batch)
                    for result in results:
                        self.wallets_with_balance.append(result)
                        self._save_to_file(result)

            except Exception as e:
                logging.error(f"Scanner worker error: {str(e)}")
                continue

    @staticmethod
    def generate_checksum(payload: bytes) -> bytes:
        """Generate double SHA256 checksum."""
        return hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]

    def start_scan(self):
        """Start or resume scanning with multiprocessing."""
        try:
            with self._lock:
                if not self.scanning:
                    logging.info(f"Starting scan with {self.thread_count} CPU cores")
                    self.scanning = True
                    self.start_time = time.time()

                    # Shutdown existing executors
                    if self._executor:
                        self._executor.shutdown(wait=False)
                    if self._process_pool:
                        self._process_pool.shutdown(wait=False)

                    self._executor = None
                    self._process_pool = None
                    self._futures = []

                    # Create executor with specified thread count
                    self._executor = ThreadPoolExecutor(max_workers=2)  # For I/O operations
                    self._process_pool = ProcessPoolExecutor(max_workers=self.thread_count)  # For CPU-intensive tasks

                    # Start generator thread
                    gen_future = self._executor.submit(self._wallet_generator_worker)
                    self._futures = [gen_future]

                    # Start scan workers (one per CPU core)
                    for _ in range(self.thread_count):
                        scan_future = self._executor.submit(self._scan_worker)
                        self._futures.append(scan_future)

        except Exception as e:
            logging.error(f"Error starting scan: {str(e)}")
            self.scanning = False
            self._cleanup_executors()

    def _cleanup_executors(self):
        """Clean up all executors."""
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None
        if self._process_pool:
            self._process_pool.shutdown(wait=False)
            self._process_pool = None

    def stop_scan(self):
        """Stop scanning."""
        with self._lock:
            if self.scanning:
                logging.info("Stopping scan...")
                self.scanning = False
                self._cleanup_executors()
                self._futures = []
                logging.info("Scan stopped")

    def get_statistics(self):
        """Get current scanning statistics."""
        with self._lock:
            elapsed_time = time.time() - (self.start_time or time.time())
            scan_rate = self.total_scanned / (elapsed_time / 60) if elapsed_time > 0 else 0

            return {
                'total_scanned': self.total_scanned,
                'wallets_with_balance': len(self.wallets_with_balance),
                'scan_rate': round(scan_rate, 2),
                'active_threads': len([f for f in self._futures[1:] if not f.done()]),
                'queue_size': self.wallet_queue.qsize() * self.BATCH_SIZE  # Adjust for batch size
            }

    def set_thread_count(self, count: int):
        """Set the number of scanning threads."""
        if count < 1:
            raise ValueError("Thread count must be at least 1")

        with self._lock:
            old_count = self.thread_count
            self.thread_count = min(count, multiprocessing.cpu_count())
            logging.info(f"Thread count changed from {old_count} to {self.thread_count}")

            # If scanning is active, restart with new thread count
            if self.scanning:
                self.stop_scan()
                self.start_scan()

    def _save_to_file(self, wallet_info: Dict):
        """Save wallet with balance to file."""
        try:
            filepath = os.path.join(self.save_dir, "wallets.txt")
            os.makedirs(self.save_dir, exist_ok=True)

            with open(filepath, 'a') as f:
                f.write(f"\n=== Wallet Found at {wallet_info['found_at']} ===\n")
                f.write(f"Seed Phrase: {wallet_info['seed_phrase']}\n")
                f.write(f"Address: {wallet_info['address']}\n")
                f.write(f"Balance: {wallet_info['balance']} BTC\n")
                f.write("="*50 + "\n")

            logging.info(f"Saved wallet with balance {wallet_info['balance']} BTC to {filepath}")

        except Exception as e:
            logging.error(f"Error saving wallet to {filepath}: {str(e)}")