import multiprocessing
from multiprocessing import Queue, Value, Array
import threading
import logging
from typing import Dict, Optional
from datetime import datetime
from wallet_scanner import WalletScanner

class ProcessPool:
    def __init__(self, max_processes: int = 4):
        self.max_processes = max_processes
        self.processes: Dict[str, Dict] = {}
        self.stats_queues: Dict[str, Queue] = {}
        self.control_queues: Dict[str, Queue] = {}
        self._lock = threading.Lock()

        # Shared memory for process statistics
        self.total_scanned = Value('i', 0)
        self.total_found = Value('i', 0)

    def start_process(self, process_id: str) -> bool:
        """Start a new wallet scanning process."""
        with self._lock:
            if len(self.processes) >= self.max_processes:
                return False

            if process_id in self.processes:
                return False

            try:
                # Create communication queues
                stats_queue = Queue()
                control_queue = Queue()

                # Create and start process
                process = multiprocessing.Process(
                    target=self._run_scanner,
                    args=(process_id, stats_queue, control_queue)
                )
                process.start()

                # Store process information
                self.processes[process_id] = {
                    'process': process,
                    'start_time': datetime.now(),
                    'status': 'running'
                }
                self.stats_queues[process_id] = stats_queue
                self.control_queues[process_id] = control_queue

                logging.info(f"Started process {process_id}")
                return True

            except Exception as e:
                logging.error(f"Failed to start process {process_id}: {str(e)}")
                return False

    def stop_process(self, process_id: str) -> bool:
        """Stop a specific process."""
        with self._lock:
            if process_id not in self.processes:
                return False

            try:
                # Send stop signal
                self.control_queues[process_id].put('STOP')

                # Wait for process to terminate
                process = self.processes[process_id]['process']
                process.join(timeout=5)

                if process.is_alive():
                    process.terminate()

                # Clean up
                del self.processes[process_id]
                del self.stats_queues[process_id]
                del self.control_queues[process_id]

                logging.info(f"Stopped process {process_id}")
                return True

            except Exception as e:
                logging.error(f"Failed to stop process {process_id}: {str(e)}")
                return False

    def get_process_stats(self, process_id: str) -> Optional[Dict]:
        """Get current statistics for a process."""
        if process_id not in self.processes:
            return None

        try:
            # Get latest stats without blocking
            stats = None
            while not self.stats_queues[process_id].empty():
                stats = self.stats_queues[process_id].get_nowait()

            if not stats:
                return {
                    'status': self.processes[process_id]['status'],
                    'start_time': self.processes[process_id]['start_time'].strftime("%Y-%m-%d %H:%M:%S"),
                    'total_scanned': 0,
                    'wallets_found': 0,
                    'scan_rate': 0
                }

            return stats

        except Exception as e:
            logging.error(f"Error getting stats for process {process_id}: {str(e)}")
            return None

    def _run_scanner(self, process_id: str, stats_queue: Queue, control_queue: Queue):
        """Run the wallet scanner in a separate process."""
        try:
            scanner = WalletScanner()
            scanner.start_scan()

            while True:
                # Check for control commands
                try:
                    if not control_queue.empty():
                        cmd = control_queue.get_nowait()
                        if cmd == 'STOP':
                            break
                except:
                    pass

                # Update statistics
                stats = scanner.get_statistics()
                stats['status'] = 'running'
                stats_queue.put(stats)

                # Small sleep to prevent CPU overload
                import time
                time.sleep(0.1)

        except Exception as e:
            logging.error(f"Scanner process {process_id} error: {str(e)}")
        finally:
            try:
                if 'scanner' in locals():
                    scanner.stop_scan()
            except Exception as inner_e:
                logging.error(f"Error stopping scanner in process {process_id}: {str(inner_e)}")

            # Send final status update
            stats_queue.put({
                'status': 'stopped',
                'error': str(e) if 'e' in locals() else None
            })