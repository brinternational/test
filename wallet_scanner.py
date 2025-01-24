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
        self.thread_count = 4  # Default to 4 threads
        self._executor = None
        self._futures = []
        self._lock = threading.Lock()
        self.wallet_queue = Queue(maxsize=10000)  # Increased buffer size for faster processing

        # Ensure wallet save directory exists
        self.save_dir = r"C:\test\temp"
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            logging.info(f"Wallet save directory created/verified: {self.save_dir}")
        except Exception as e:
            logging.error(f"Failed to create wallet directory {self.save_dir}: {str(e)}")

    def _wallet_generator_worker(self):
        """Continuously generate new wallets and add to queue."""
        while self.scanning:
            try:
                if self.wallet_queue.qsize() < self.wallet_queue.maxsize * 0.9:  # Keep queue 90% filled
                    # Generate random entropy for new seed phrase
                    word_count = 12  # Standard BIP39 length
                    words, entropy = WalletGenerator.generate_seed_phrase(word_count)

                    # Create wallet data
                    wallet_data = {
                        'seed_phrase': ' '.join(words),
                        'entropy': entropy,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

                    self.wallet_queue.put(wallet_data)
                else:
                    time.sleep(0.01)  # Reduced sleep time for faster generation
            except Exception as e:
                logging.error(f"Generator worker error: {str(e)}")
                continue

    def _scan_worker(self):
        """Worker function for scanning thread."""
        while self.scanning:
            try:
                # Get next wallet from queue with short timeout
                try:
                    wallet_data = self.wallet_queue.get(timeout=0.1)
                except Empty:
                    continue

                # Process wallet data
                entropy = wallet_data['entropy']

                # Basic address generation (for educational purposes)
                version_byte = b'\x00'  # mainnet
                combined = version_byte + entropy[:20]  # Use first 20 bytes for demo
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
                    self.scanning = True
                    self.start_time = time.time()

                    # Stop existing executor if any
                    if self._executor:
                        self._executor.shutdown(wait=True)

                    # Clear futures list
                    self._futures = []

                    # Initialize new thread pool with exactly thread_count workers
                    self._executor = ThreadPoolExecutor(max_workers=self.thread_count)

                    # Start exactly thread_count workers
                    for _ in range(self.thread_count):
                        self._futures.append(self._executor.submit(self._scan_worker))

                    # Add one generator worker outside the thread count
                    self._futures.append(ThreadPoolExecutor(max_workers=1).submit(self._wallet_generator_worker))

                    logging.info(f"Started scanning with {self.thread_count} scan workers and 1 generator")

        except Exception as e:
            logging.error(f"Error starting scan: {str(e)}")
            self.scanning = False
            if self._executor:
                self._executor.shutdown(wait=False)

    def stop_scan(self):
        """Stop scanning."""
        with self._lock:
            if self.scanning:
                self.scanning = False
                if self._executor:
                    self._executor.shutdown(wait=True)
                    self._executor = None
                self._futures = []
                logging.info("Scanning stopped")

    def get_statistics(self):
        """Get current scanning statistics."""
        with self._lock:
            elapsed_time = time.time() - (self.start_time or time.time())
            scan_rate = self.total_scanned / (elapsed_time / 60) if elapsed_time > 0 else 0

            # Count only active scanning threads (excluding generator)
            active_threads = sum(1 for f in self._futures[:-1] if not f.done())  # Exclude generator thread

            return {
                'total_scanned': self.total_scanned,
                'wallets_with_balance': len(self.wallets_with_balance),
                'scan_rate': round(scan_rate, 2),
                'active_threads': active_threads,
                'queue_size': self.wallet_queue.qsize()
            }

    def set_thread_count(self, count: int):
        """Set the number of scanning threads."""
        if count < 1:
            raise ValueError("Thread count must be at least 1")

        with self._lock:
            self.thread_count = count
            logging.info(f"Thread count set to {count}")

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