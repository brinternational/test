import time
from typing import Dict, List, Deque
from datetime import datetime
import os
import logging
import threading
import multiprocessing
from queue import Queue, Empty
from collections import deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import base58
import hashlib
from gpu_hasher import GPUHasher
import uuid
from wallet_generator import WalletGenerator
from bitcoin_utils import BitcoinUtils

class WalletScanner:
    _instance_counter = multiprocessing.Value('i', 0)

    # Add class-level batch size constants
    CPU_BATCH_SIZE = 1000
    GPU_BATCH_SIZE = 10000

    def __init__(self):
        self.instance_id = str(uuid.uuid4())[:8]
        with WalletScanner._instance_counter.get_lock():
            WalletScanner._instance_counter.value += 1
            self.instance_number = WalletScanner._instance_counter.value

        self.scanning = False
        self.simulation_mode = False
        self.cpu_thread_count = max(multiprocessing.cpu_count() // 2, 1)
        self.gpu_thread_count = 256
        self._executor = None
        self._process_pool = None
        self._futures = []
        self._lock = threading.Lock()
        self._stats_lock = threading.Lock()
        self._stats_thread = None
        self._stats_stop_event = threading.Event()

        # Initialize acceleration settings
        self.cpu_enabled = True
        self.gpu_enabled = False  # Default to False since we're focusing on live node verification
        self.npu_enabled = False
        self.gpu_hasher = None

        self.save_dir = os.path.normpath("C:/temp")
        self._setup_save_directory()

        # Initialize queues and counters without immediate node verification
        self.wallet_queue = Queue(maxsize=1000)
        self.result_queue = multiprocessing.Queue()

        # Initialize shared counters
        self.shared_total = multiprocessing.Value('i', 0)
        self.shared_balance_count = multiprocessing.Value('i', 0)
        self.cpu_processed = multiprocessing.Value('i', 0)
        self.gpu_processed = multiprocessing.Value('i', 0)

        # Initialize scan rate tracking
        self.cpu_scan_rates = deque(maxlen=10)
        self.gpu_scan_rates = deque(maxlen=10)
        self.scan_rates = deque(maxlen=10)  # Combined rates
        self.last_cpu_time = time.time()
        self.last_gpu_time = time.time()

        # Add cached stats to prevent blocking
        self._cached_stats = {
            'total_scanned': "0",
            'cpu_processed': "0",
            'gpu_processed': "0",
            'wallets_with_balance': "0",
            'cpu_scan_rate': "0.0",
            'gpu_scan_rate': "0.0",
            'queue_size': "0",
            'node_chain': 'unknown',
            'node_height': 0
        }
        self._last_stats_update = 0
        self._stats_update_interval = 1.0  # Update every second

    def verify_wallet(self, address: str) -> float:
        """Verify wallet balance either through node or simulation."""
        if self.simulation_mode:
            # Simulate balance check
            addr_hash = int.from_bytes(hashlib.sha256(address.encode()).digest(), 'big')
            if addr_hash % 10000000 == 0:  # Simulate rare finds
                return float(addr_hash % 100) / 100000
            return 0.0
        else:
            return BitcoinUtils.verify_wallet(address)

    def get_node_info(self):
        """Get node information with simulation fallback."""
        if self.simulation_mode:
            return {
                'chain': 'simulated',
                'blocks': 0,
                'peers': 0
            }
        return BitcoinUtils.get_node_info()

    def start_scan(self, simulation_mode: bool = False):
        """Start wallet scanning with non-blocking initialization."""
        if self.scanning:
            return

        try:
            with self._lock:
                logging.debug(f"Instance {self.instance_id}: Starting scan initialization")
                self.simulation_mode = simulation_mode

                def init_scanner():
                    try:
                        if not simulation_mode:
                            BitcoinUtils.verify_live_node()
                            logging.info(f"Instance {self.instance_id}: Connected to Bitcoin node")

                        self.scanning = True
                        self.start_time = time.time()

                        # Reset statistics
                        self._reset_statistics()
                        self._cleanup_executors()
                        self._set_process_priority()

                        # Configure thread pools
                        executor_workers = self.cpu_thread_count * 2 if os.name == 'nt' else self.cpu_thread_count

                        self._executor = ThreadPoolExecutor(
                            max_workers=executor_workers,
                            thread_name_prefix=f"WalletScanner-{self.instance_id}"
                        )

                        self._process_pool = ProcessPoolExecutor(
                            max_workers=self.cpu_thread_count,
                            mp_context=multiprocessing.get_context('spawn'),
                            initializer=self._process_initializer
                        )

                        # Start workers
                        gen_future = self._executor.submit(self._wallet_generator_worker)
                        self._futures = [gen_future]

                        for _ in range(executor_workers):
                            scan_future = self._executor.submit(self._scan_worker)
                            self._futures.append(scan_future)

                        if self.gpu_enabled and self.gpu_hasher:
                            gpu_future = self._executor.submit(self._gpu_scan_worker)
                            self._futures.append(gpu_future)

                        logging.info(f"Instance {self.instance_id}: Scan initialization complete")

                    except Exception as e:
                        logging.error(f"Instance {self.instance_id}: Error in scanner initialization: {str(e)}")
                        self.stop_scan()

                # Run initialization in separate thread
                threading.Thread(target=init_scanner, daemon=True).start()

        except Exception as e:
            logging.error(f"Instance {self.instance_id}: Error starting scan: {str(e)}")
            self.scanning = False
            raise

    def get_statistics(self):
        """Get current statistics with non-blocking behavior."""
        current_time = time.time()

        # Return cached stats if not enough time has passed
        if current_time - self._last_stats_update < self._stats_update_interval:
            return self._cached_stats

        try:
            with self._stats_lock:
                # Get node info based on mode
                if self.simulation_mode:
                    node_info = {
                        'chain': 'simulated',
                        'blocks': 0
                    }
                else:
                    try:
                        node_info = BitcoinUtils.get_node_info()
                    except Exception as e:
                        logging.warning(f"Failed to get node info: {str(e)}")
                        node_info = {'chain': 'unknown', 'blocks': 0}

                cpu_rate = self.cpu_scan_rate
                cpu_rate_per_min = cpu_rate * 60 if cpu_rate > 0 else 0

                gpu_rate = self.gpu_scan_rate
                gpu_rate_per_min = gpu_rate * 60 if gpu_rate > 0 else 0

                self._cached_stats = {
                    'total_scanned': f"{self.shared_total.value:,}",
                    'cpu_processed': f"{self.cpu_processed.value:,}",
                    'gpu_processed': f"{self.gpu_processed.value:,}",
                    'wallets_with_balance': f"{self.shared_balance_count.value:,}",
                    'cpu_scan_rate': f"{cpu_rate_per_min:,.1f}",
                    'gpu_scan_rate': f"{gpu_rate_per_min:,.1f}",
                    'queue_size': f"{self.wallet_queue.qsize():,}",
                    'node_chain': node_info['chain'],
                    'node_height': node_info['blocks']
                }
                self._last_stats_update = current_time

        except Exception as e:
            logging.error(f"Error updating statistics: {str(e)}")
            # Return last known good stats on error

        return self._cached_stats

    def _setup_save_directory(self):
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            logging.info(f"Instance {self.instance_id}: Using wallet directory: {self.save_dir}")
        except Exception as e:
            logging.error(f"Instance {self.instance_id}: Failed to create directory {self.save_dir}: {str(e)}")
            raise

    def _get_wallet_filename(self):
        return os.path.join(self.save_dir, f"wallets{self.instance_number}.txt")

    def _save_to_file(self, wallet_info: Dict):
        try:
            filepath = self._get_wallet_filename()
            with open(filepath, 'a') as f:
                f.write(
                    f"\n=== Verified Wallet Found at {wallet_info['found_at']} ===\n"
                    f"Address: {wallet_info['address']}\n"
                    f"Balance: {wallet_info['balance']} BTC\n"
                    f"Network: {wallet_info['network']}\n"
                    f"Block Height: {wallet_info['block_height']}\n"
                    f"{'=' * 50}\n"
                )
        except Exception as e:
            logging.error(f"Instance {self.instance_id}: Error saving wallet to file: {str(e)}")

    def get_instance_info(self) -> Dict:
        return {
            'instance_id': self.instance_id,
            'instance_number': self.instance_number,
            'wallet_file': f"wallets{self.instance_number}.txt",
            'cpu_threads': self.cpu_thread_count,
            'gpu_enabled': bool(self.gpu_hasher),
            'batch_size': self.CPU_BATCH_SIZE
        }

    def _set_process_priority(self):
        """Set process priority and affinity for multi-instance support."""
        try:
            if os.name == 'nt':
                import ctypes
                import ctypes.wintypes

                # Define SYSTEM_INFO structure
                class SYSTEM_INFO(ctypes.Structure):
                    _fields_ = [
                        ("wProcessorArchitecture", ctypes.wintypes.WORD),
                        ("wReserved", ctypes.wintypes.WORD),
                        ("dwPageSize", ctypes.wintypes.DWORD),
                        ("lpMinimumApplicationAddress", ctypes.c_void_p),
                        ("lpMaximumApplicationAddress", ctypes.c_void_p),
                        ("dwActiveProcessorMask", ctypes.c_void_p),
                        ("dwNumberOfProcessors", ctypes.wintypes.DWORD),
                        ("dwProcessorType", ctypes.wintypes.DWORD),
                        ("dwAllocationGranularity", ctypes.wintypes.DWORD),
                        ("wProcessorLevel", ctypes.wintypes.WORD),
                        ("wProcessorRevision", ctypes.wintypes.WORD)
                    ]

                process = ctypes.windll.kernel32.GetCurrentProcess()
                ctypes.windll.kernel32.SetPriorityClass(process, 0x00008000)

                system_info = SYSTEM_INFO()
                ctypes.windll.kernel32.GetSystemInfo(ctypes.byref(system_info))

                # Respect user-defined thread count, but don't exceed system limit
                usable_cores = min(self.cpu_thread_count, system_info.dwNumberOfProcessors)
                processor_mask = ((1 << usable_cores) - 1)

                ctypes.windll.kernel32.SetProcessAffinityMask(process, processor_mask)
                logging.info(f"Instance {self.instance_id}: Using {usable_cores} of {system_info.dwNumberOfProcessors} cores")

            else:
                os.nice(10)
                self.cpu_thread_count = max(multiprocessing.cpu_count() // 4, 1)

        except Exception as e:
            logging.warning(f"Instance {self.instance_id}: Failed to set process priority: {str(e)}")
            self.cpu_thread_count = max(multiprocessing.cpu_count() // 4, 1)

    def _process_initializer(self):
        self._set_process_priority()
        threading.current_thread().name = f"WalletScanner-{self.instance_id}-{os.getpid()}"
        logging.info(f"Instance {self.instance_id}: Worker process {os.getpid()} initialized")

    def _process_batch(self, batch: List[Dict]) -> List[Dict]:
        """Process a batch of addresses with live node verification."""
        try:
            # Verify node connection before processing if not in simulation mode
            if not self.simulation_mode:
                BitcoinUtils.verify_live_node()
            node_info = self.get_node_info()

            results = []
            batch_addresses = [wallet_data['address'] for wallet_data in batch]

            for wallet_data in batch:
                try:
                    # Verify each address with the live node or simulation
                    balance = self.verify_wallet(wallet_data['address'])
                    if balance > 0:
                        wallet_data.update({
                            'balance': balance,
                            'network': node_info['chain'],
                            'block_height': node_info['blocks'],
                            'found_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        results.append(wallet_data)
                        logging.info(f"Instance {self.instance_id}: Found wallet with balance: {balance} BTC")
                except Exception as e:
                    logging.error(f"Instance {self.instance_id}: Error verifying wallet: {str(e)}", exc_info=True)
                    raise  # Fail entire batch if we can't verify wallets

            return results
        except Exception as e:
            logging.error(f"Instance {self.instance_id}: Batch processing failed - no live node connection: {str(e)}", exc_info=True)
            self.stop_scan()  # Stop scanning if we lose node connection
            raise

    def _process_batch_cpu(self, batch: List[Dict]) -> List[Dict]:
        return self._process_batch(batch)

    def _process_batch_gpu(self, batch: List[Dict]) -> List[Dict]:
        return self._process_batch(batch)


    def _wallet_generator_worker(self):
        logging.info(f"Instance {self.instance_id}: Generator worker started")
        local_batch = []
        while self.scanning:
            try:
                if self.wallet_queue.qsize() < self.wallet_queue.maxsize * 0.7:
                    local_batch = []
                    local_batch_size = min(self.GPU_BATCH_SIZE,
                                             self.wallet_queue.maxsize - self.wallet_queue.qsize())
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
                    time.sleep(0.0001)
            except Exception as e:
                logging.error(f"Instance {self.instance_id}: Generator worker error: {str(e)}", exc_info=True)
                continue

    @staticmethod
    def check_balance_batch(addresses: List[str]) -> List[float]:
        results = []
        for address in addresses:
            addr_hash = int.from_bytes(hashlib.sha256(address.encode()).digest(), 'big')
            if addr_hash % 10000000 == 0:
                balance = float(addr_hash % 100) / 100000
                results.append(balance)
            else:
                results.append(0.0)
        return results

    def _scan_worker(self):
        """CPU scan worker implementation."""
        logging.info(f"Instance {self.instance_id}: CPU Scan worker started")
        local_start_time = time.time()
        local_processed = 0

        while self.scanning:
            try:
                batch = self.wallet_queue.get(timeout=0.01)
                if batch:
                    results = self._process_batch_cpu(batch[:self.CPU_BATCH_SIZE])

                    # Update CPU processing statistics
                    with self.cpu_processed.get_lock():
                        self.cpu_processed.value += len(batch)
                        local_processed += len(batch)

                        # Update CPU scan rate
                        current_time = time.time()
                        time_diff = current_time - local_start_time
                        if time_diff >= 1.0:  # Update rate every second
                            rate = local_processed / time_diff
                            with self._lock:
                                self.cpu_scan_rates.append(rate)
                                self.scan_rates.append(rate)  # Update combined rates
                            local_processed = 0
                            local_start_time = current_time

                    # Update total statistics
                    with self.shared_total.get_lock():
                        self.shared_total.value += len(batch)
                    with self.shared_balance_count.get_lock():
                        self.shared_balance_count.value += len(results)

                    # Save results if any found
                    if results:
                        for result in results:
                            self._save_to_file(result)

            except Empty:
                time.sleep(0.0001)
            except Exception as e:
                logging.error(f"Instance {self.instance_id}: CPU Scanner worker error: {str(e)}", exc_info=True)
                continue

    def _gpu_scan_worker(self):
        logging.info(f"Instance {self.instance_id}: GPU Scan worker started")
        while self.scanning:
            try:
                batch = self.wallet_queue.get(timeout=0.01)
                if batch:
                    results = self._process_batch_gpu(batch)
                    with self.gpu_processed.get_lock():
                        self.gpu_processed.value += len(batch)
                        current_time = time.time()
                        if self.last_gpu_time:
                            rate = len(batch) / (current_time - self.last_gpu_time)
                            self.gpu_scan_rates.append(rate)
                        self.last_gpu_time = current_time
                    with self.shared_total.get_lock():
                        self.shared_total.value += len(batch)
                    with self.shared_balance_count.get_lock():
                        self.shared_balance_count.value += len(results)
                    if results:
                        for result in results:
                            self._save_to_file(result)
            except Empty:
                time.sleep(0.0001)
            except Exception as e:
                logging.error(f"Instance {self.instance_id}: GPU Scanner worker error: {str(e)}", exc_info=True)
                continue


    def stop_scan(self):
        with self._lock:
            if self.scanning:
                logging.info(f"Instance {self.instance_id}: Stopping scan...")
                self.scanning = False
                self._cleanup_executors()
                self._futures = []
                logging.info(f"Instance {self.instance_id}: Scan stopped")

    def _cleanup_executors(self):
        """Cleanup thread and process pools with proper logging."""
        logging.debug(f"Instance {self.instance_id}: Starting executor cleanup")
        if self._executor:
            try:
                logging.debug(f"Instance {self.instance_id}: Shutting down thread executor")
                self._executor.shutdown(wait=False)
            except Exception as e:
                logging.error(f"Instance {self.instance_id}: Error shutting down thread executor: {str(e)}", exc_info=True)
            finally:
                self._executor = None

        if self._process_pool:
            try:
                logging.debug(f"Instance {self.instance_id}: Shutting down process pool")
                self._process_pool.shutdown(wait=False)
            except Exception as e:
                logging.error(f"Instance {self.instance_id}: Error shutting down process pool: {str(e)}", exc_info=True)
            finally:
                self._process_pool = None
        logging.debug(f"Instance {self.instance_id}: Executor cleanup complete")

    @property
    def cpu_scan_rate(self):
        """Calculate current CPU scan rate."""
        with self._lock:
            if not self.cpu_scan_rates:
                return 0
            return sum(self.cpu_scan_rates) / len(self.cpu_scan_rates)

    @property
    def gpu_scan_rate(self):
        """Calculate current GPU scan rate."""
        with self._lock:
            if not self.gpu_scan_rates:
                return 0
            return sum(self.gpu_scan_rates) / len(self.gpu_scan_rates)

    def set_thread_count(self, count: int):
        if count < 1:
            raise ValueError("Thread count must be at least 1")

        with self._lock:
            old_count = self.cpu_thread_count
            self.cpu_thread_count = min(count, multiprocessing.cpu_count())

            if self.gpu_enabled and self.gpu_hasher:
                self.gpu_thread_count = min(count * 64, 1024)
                self.gpu_hasher.set_gpu_threads(self.gpu_thread_count)
                logging.info(f"Instance {self.instance_id}: GPU threads adjusted to {self.gpu_thread_count}")

            logging.info(f"Instance {self.instance_id}: CPU thread count changed from {old_count} to {self.cpu_thread_count}")

            if self.scanning:
                self.stop_scan()
                self.start_scan()

    def set_acceleration_preferences(self, cpu_enabled: bool, gpu_enabled: bool, npu_enabled: bool):
        self.cpu_enabled = cpu_enabled
        self.gpu_enabled = gpu_enabled
        self.npu_enabled = npu_enabled

        try:
            self.gpu_hasher = GPUHasher(
                enable_cpu=self.cpu_enabled,
                enable_gpu=self.gpu_enabled,
                enable_npu=self.npu_enabled
            )
            logging.info(f"Instance {self.instance_id}: Acceleration updated: {self.gpu_hasher.get_device_info()}")
        except Exception as e:
            logging.warning(f"Instance {self.instance_id}: Hardware acceleration disabled: {str(e)}")
            self.gpu_hasher = None

    def _reset_statistics(self):
        """Reset all statistics counters."""
        with self._stats_lock:
            self.cpu_scan_rates.clear()
            self.gpu_scan_rates.clear()
            self.scan_rates.clear()

            with self.shared_total.get_lock():
                self.shared_total.value = 0
            with self.shared_balance_count.get_lock():
                self.shared_balance_count.value = 0
            with self.cpu_processed.get_lock():
                self.cpu_processed.value = 0
            with self.gpu_processed.get_lock():
                self.gpu_processed.value = 0

            self._cached_stats = {
                'total_scanned': "0",
                'cpu_processed': "0",
                'gpu_processed': "0",
                'wallets_with_balance': "0",
                'cpu_scan_rate': "0.0",
                'gpu_scan_rate': "0.0",
                'queue_size': "0",
                'node_chain': 'unknown',
                'node_height': 0
            }