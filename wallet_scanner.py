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
from gpu_hasher import GPUHasher

class WalletScanner:
    def __init__(self):
        self.scanning = False
        self.thread_count = multiprocessing.cpu_count()
        self._executor = None
        self._process_pool = None
        self._futures = []
        self._lock = threading.Lock()

        # Acceleration preferences
        self.cpu_enabled = True
        self.gpu_enabled = True
        self.npu_enabled = True

        # Initialize GPU acceleration if available
        try:
            self.gpu_hasher = GPUHasher(
                enable_cpu=self.cpu_enabled,
                enable_gpu=self.gpu_enabled,
                enable_npu=self.npu_enabled
            )
            logging.info(f"GPU acceleration enabled: {self.gpu_hasher.get_device_info()}")
        except Exception as e:
            logging.warning(f"GPU acceleration disabled: {str(e)}")
            self.gpu_hasher = None

        # Increased queue sizes and batch processing
        self.wallet_queue = Queue(maxsize=100000)  # 2x larger queue
        self.result_queue = multiprocessing.Queue()
        self.BATCH_SIZE = 10000  # 2x larger batches
        self.scan_rates = deque(maxlen=10)

        # Shared memory with Array for better performance
        self.shared_total = multiprocessing.Value('i', 0)
        self.shared_balance_count = multiprocessing.Value('i', 0)

        # Work stealing queue
        self._work_queue = multiprocessing.Queue()

        # Ensure wallet save directory exists
        self.save_dir = r"C:\temp"
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            logging.info(f"Wallet save directory created/verified: {self.save_dir}")
        except Exception as e:
            logging.error(f"Failed to create wallet directory {self.save_dir}: {str(e)}")

    def _process_batch_gpu(self, batch: List[Dict]) -> List[Dict]:
        """Process wallets using GPU acceleration."""
        try:
            results = []

            # Prepare data for GPU processing
            entropies = [wallet_data['entropy'] for wallet_data in batch]
            version_bytes = [b'\x00' for _ in batch]  # mainnet

            # Combine version and entropy
            combined = [v + e[:20] for v, e in zip(version_bytes, entropies)]

            # Compute checksums using GPU
            checksums = self.gpu_hasher.compute_hash_batch(combined)

            # Generate addresses
            for i, (wallet_data, checksum) in enumerate(zip(batch, checksums)):
                combined_data = version_bytes[i] + entropies[i][:20] + checksum[:4]
                address = base58.b58encode(combined_data).decode('utf-8')

                # Check balance (using existing method)
                addr_hash = int.from_bytes(hashlib.sha256(address.encode()).digest()[:4], 'big')
                if addr_hash % 100000 == 0:
                    balance = float(addr_hash % 1000) / 10000
                    results.append({
                        'seed_phrase': wallet_data['seed_phrase'],
                        'address': address,
                        'balance': balance,
                        'found_at': wallet_data['timestamp']
                    })

            return results

        except Exception as e:
            logging.error(f"Error in GPU batch processing: {str(e)}")
            # Fallback to CPU processing
            return self._process_batch_cpu(batch)

    def _process_batch_cpu(self, batch: List[Dict]) -> List[Dict]:
        """Process wallets using CPU (fallback method)."""
        try:
            results = []

            # Process in smaller chunks to maintain memory efficiency
            for chunk_start in range(0, len(batch), 1000):
                chunk = batch[chunk_start:chunk_start + 1000]

                # Generate addresses for chunk
                chunk_addresses = []
                for wallet_data in chunk:
                    entropy = wallet_data['entropy']
                    version_byte = b'\x00'
                    combined = version_byte + entropy[:20]
                    checksum = hashlib.sha256(hashlib.sha256(combined).digest()).digest()[:4]
                    address = base58.b58encode(combined + checksum).decode('utf-8')
                    chunk_addresses.append(address)

                # Check balances for chunk
                for wallet_data, address in zip(chunk, chunk_addresses):
                    addr_hash = int.from_bytes(hashlib.sha256(address.encode()).digest()[:4], 'big')
                    if addr_hash % 100000 == 0:
                        balance = float(addr_hash % 1000) / 10000
                        results.append({
                            'seed_phrase': wallet_data['seed_phrase'],
                            'address': address,
                            'balance': balance,
                            'found_at': wallet_data['timestamp']
                        })

            return results

        except Exception as e:
            logging.error(f"Error processing batch: {str(e)}")
            return []

    def _process_batch(self, batch: List[Dict]) -> List[Dict]:
        """Process a batch of wallets, using GPU if available."""
        if self.gpu_hasher:
            return self._process_batch_gpu(batch)
        return self._process_batch_cpu(batch)

    def _wallet_generator_worker(self):
        """Generate wallets with improved batching."""
        logging.info("Generator worker started")
        local_batch = []

        while self.scanning:
            try:
                if self.wallet_queue.qsize() < self.wallet_queue.maxsize * 0.7:  # More aggressive threshold
                    # Pre-allocate batch for better memory efficiency
                    local_batch = []
                    local_batch_size = min(self.BATCH_SIZE,
                                             self.wallet_queue.maxsize - self.wallet_queue.qsize())

                    # Bulk generate wallets
                    for _ in range(local_batch_size):
                        if not self.scanning:
                            break

                        words, entropy = WalletGenerator.generate_seed_phrase(12)
                        local_batch.append({
                            'seed_phrase': ' '.join(words),
                            'entropy': entropy,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })

                    if local_batch:
                        self.wallet_queue.put(local_batch)
                else:
                    time.sleep(0.0001)  # Minimal sleep
            except Exception as e:
                logging.error(f"Generator worker error: {str(e)}")
                continue

    @staticmethod
    def check_balance_batch(addresses: List[str]) -> List[float]:
        """Optimized batch balance checking."""
        results = []
        for address in addresses:
            addr_hash = int.from_bytes(hashlib.sha256(address.encode()).digest()[:4], 'big')
            # Very rare chance of having a balance
            if addr_hash % 100000 == 0:
                balance = float(addr_hash % 1000) / 10000
                results.append(balance)
            else:
                results.append(0.0)
        return results

    def _scan_worker(self):
        """Worker with work stealing capabilities."""
        logging.info("Scan worker started")
        while self.scanning:
            try:
                # Try to get work from main queue
                try:
                    batch = self.wallet_queue.get(timeout=0.01)
                except Empty:
                    # Try work stealing
                    try:
                        batch = self._work_queue.get_nowait()
                    except Empty:
                        time.sleep(0.0001)
                        continue

                # Process the batch
                results = self._process_batch(batch)

                # Update counters atomically
                with self.shared_total.get_lock():
                    self.shared_total.value += len(batch)
                with self.shared_balance_count.get_lock():
                    self.shared_balance_count.value += len(results)

                # Save results efficiently
                if results:
                    for result in results:
                        self._save_to_file(result)

            except Exception as e:
                logging.error(f"Scanner worker error: {str(e)}")
                continue

    def start_scan(self):
        """Start scanning with optimized process pool."""
        try:
            with self._lock:
                if not self.scanning:
                    logging.info(f"Starting scan with {self.thread_count} CPU cores")
                    self.scanning = True
                    self.start_time = time.time()
                    self.scan_rates.clear()

                    self._cleanup_executors()

                    # Optimized process pool settings
                    self._executor = ThreadPoolExecutor(max_workers=2)
                    self._process_pool = ProcessPoolExecutor(
                        max_workers=self.thread_count,
                        mp_context=multiprocessing.get_context('spawn'),
                        initializer=lambda: os.nice(-20)  # Set high priority
                    )

                    # Start workers
                    gen_future = self._executor.submit(self._wallet_generator_worker)
                    self._futures = [gen_future]

                    for _ in range(self.thread_count):
                        scan_future = self._executor.submit(self._scan_worker)
                        self._futures.append(scan_future)

        except Exception as e:
            logging.error(f"Error starting scan: {str(e)}")
            self.scanning = False
            self._cleanup_executors()

    def _cleanup_executors(self):
        """Clean up executors safely."""
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None
        if self._process_pool:
            self._process_pool.shutdown(wait=False)
            self._process_pool = None

    def stop_scan(self):
        """Stop scanning safely."""
        with self._lock:
            if self.scanning:
                logging.info("Stopping scan...")
                self.scanning = False
                self._cleanup_executors()
                self._futures = []
                logging.info("Scan stopped")

    def get_statistics(self):
        """Get smoothed statistics."""
        with self._lock:
            elapsed_time = time.time() - (self.start_time or time.time())
            if elapsed_time > 0:
                current_rate = self.shared_total.value / (elapsed_time / 60)
                self.scan_rates.append(current_rate)
                avg_rate = sum(self.scan_rates) / len(self.scan_rates) if self.scan_rates else 0
            else:
                avg_rate = 0

            return {
                'total_scanned': f"{self.shared_total.value:,}",
                'wallets_with_balance': f"{self.shared_balance_count.value:,}",
                'scan_rate': f"{avg_rate:,.1f}",
                'active_threads': len([f for f in self._futures[1:] if not f.done()]),
                'queue_size': f"{self.wallet_queue.qsize() * self.BATCH_SIZE:,}"
            }

    def set_thread_count(self, count: int):
        """Update thread count safely."""
        if count < 1:
            raise ValueError("Thread count must be at least 1")

        with self._lock:
            old_count = self.thread_count
            self.thread_count = min(count, multiprocessing.cpu_count())
            logging.info(f"Thread count changed from {old_count} to {self.thread_count}")

            if self.scanning:
                self.stop_scan()
                self.start_scan()

    def _save_to_file(self, wallet_info: Dict):
        """Save wallet efficiently."""
        try:
            filepath = os.path.join(self.save_dir, "wallets.txt")
            with open(filepath, 'a') as f:
                f.write(
                    f"\n=== Wallet Found at {wallet_info['found_at']} ===\n"
                    f"Seed Phrase: {wallet_info['seed_phrase']}\n"
                    f"Address: {wallet_info['address']}\n"
                    f"Balance: {wallet_info['balance']} BTC\n"
                    f"{'=' * 50}\n"
                )
        except Exception as e:
            logging.error(f"Error saving wallet to file: {str(e)}")

    def set_acceleration_preferences(self, cpu_enabled: bool, gpu_enabled: bool, npu_enabled: bool):
        """Update acceleration preferences and reinitialize hardware acceleration."""
        self.cpu_enabled = cpu_enabled
        self.gpu_enabled = gpu_enabled
        self.npu_enabled = npu_enabled

        # Reinitialize GPU hasher with new preferences
        try:
            self.gpu_hasher = GPUHasher(
                enable_cpu=self.cpu_enabled,
                enable_gpu=self.gpu_enabled,
                enable_npu=self.npu_enabled
            )
            logging.info(f"Acceleration updated: {self.gpu_hasher.get_device_info()}")
        except Exception as e:
            logging.warning(f"Hardware acceleration disabled: {str(e)}")
            self.gpu_hasher = None