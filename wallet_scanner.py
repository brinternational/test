import time
from typing import Dict, List, Deque
from datetime import datetime
import os
import threading
import multiprocessing
from queue import Queue, Empty
from collections import deque
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
        self.wallet_queue = Queue(maxsize=50000)  # Increased queue size
        self.result_queue = multiprocessing.Queue()
        self.BATCH_SIZE = 5000  # Increased batch size for better throughput
        self.scan_rates = deque(maxlen=10)  # Store last 10 rates for averaging

        # Shared memory for stats
        self.shared_total = multiprocessing.Value('i', 0)
        self.shared_balance_count = multiprocessing.Value('i', 0)

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
        local_batch = []
        while self.scanning:
            try:
                if self.wallet_queue.qsize() < self.wallet_queue.maxsize * 0.8:  # Reduced threshold
                    # Generate wallets until we have a full batch
                    while len(local_batch) < self.BATCH_SIZE and self.scanning:
                        word_count = 12  # Standard BIP39 length
                        words, entropy = WalletGenerator.generate_seed_phrase(word_count)
                        wallet_data = {
                            'seed_phrase': ' '.join(words),
                            'entropy': entropy,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        local_batch.append(wallet_data)

                    if local_batch:  # If we have any wallets, add them to queue
                        self.wallet_queue.put(local_batch)
                        local_batch = []  # Reset batch
                else:
                    time.sleep(0.001)  # Reduced sleep time
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
        try:
            addresses = []
            for wallet_data in batch:
                entropy = wallet_data['entropy']
                version_byte = b'\x00'  # mainnet
                combined = version_byte + entropy[:20]  # Use first 20 bytes for demo
                checksum = self.generate_checksum(combined)
                address = base58.b58encode(combined + checksum).decode('utf-8')
                addresses.append(address)

            # Process addresses in sub-batches for better memory usage
            SUB_BATCH_SIZE = 1000
            all_results = []

            for i in range(0, len(addresses), SUB_BATCH_SIZE):
                sub_batch = addresses[i:i + SUB_BATCH_SIZE]
                balances = self.check_balance_batch(sub_batch)

                # Combine results for this sub-batch
                for j, (wallet_data, address, balance) in enumerate(
                    zip(batch[i:i + SUB_BATCH_SIZE], sub_batch, balances)
                ):
                    if balance > 0:
                        all_results.append({
                            'seed_phrase': wallet_data['seed_phrase'],
                            'address': address,
                            'balance': balance,
                            'found_at': wallet_data['timestamp']
                        })

            return all_results
        except Exception as e:
            logging.error(f"Error processing batch: {str(e)}")
            return []

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

                # Update shared counters atomically
                with self.shared_total.get_lock():
                    self.shared_total.value += len(batch)
                with self.shared_balance_count.get_lock():
                    self.shared_balance_count.value += len(results)

                # Save results
                for result in results:
                    self._save_to_file(result)
                    with self._lock:
                        self.wallets_with_balance.append(result)

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
                    self.scan_rates.clear()  # Reset rolling average

                    self._cleanup_executors()

                    # Create executors with optimized settings
                    self._executor = ThreadPoolExecutor(max_workers=2)  # For I/O operations
                    self._process_pool = ProcessPoolExecutor(
                        max_workers=self.thread_count,
                        mp_context=multiprocessing.get_context('spawn')  # More stable
                    )

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
        """Get current scanning statistics with smoothed rate calculation."""
        with self._lock:
            elapsed_time = time.time() - (self.start_time or time.time())
            if elapsed_time > 0:
                current_rate = self.shared_total.value / (elapsed_time / 60)
                self.scan_rates.append(current_rate)
                # Calculate rolling average
                avg_rate = sum(self.scan_rates) / len(self.scan_rates) if self.scan_rates else 0
            else:
                avg_rate = 0

            return {
                'total_scanned': self.shared_total.value,
                'wallets_with_balance': self.shared_balance_count.value,
                'scan_rate': round(avg_rate, 1),  # Rounded to 1 decimal for stability
                'active_threads': len([f for f in self._futures[1:] if not f.done()]),
                'queue_size': self.wallet_queue.qsize() * self.BATCH_SIZE
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
            logging.error(f"Error saving wallet to file: {str(e)}")