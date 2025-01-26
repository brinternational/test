import multiprocessing
from multiprocessing import Queue, Value, Array
import threading
import logging
from typing import Dict, Optional
from datetime import datetime
from queue import Empty
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

        # Add event for safe termination
        self._stopping = threading.Event()

    def start_process(self, process_id: str) -> bool:
        """Start a new wallet scanning process."""
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
            with self._lock:
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
        if process_id not in self.processes:
            return False

        try:
            # Set stopping flag
            self._stopping.set()

            # Send stop signal
            try:
                self.control_queues[process_id].put_nowait('STOP')
            except Exception:
                pass  # Queue might be full or closed

            # Wait for process to terminate
            process = self.processes[process_id]['process']
            process.join(timeout=2)  # Reduced timeout

            if process.is_alive():
                process.terminate()
                process.join(timeout=1)

            if process.is_alive():
                process.kill()  # Force kill if still alive

            # Clean up
            with self._lock:
                if process_id in self.processes:
                    del self.processes[process_id]
                if process_id in self.stats_queues:
                    del self.stats_queues[process_id]
                if process_id in self.control_queues:
                    del self.control_queues[process_id]

            logging.info(f"Stopped process {process_id}")
            return True

        except Exception as e:
            logging.error(f"Failed to stop process {process_id}: {str(e)}")
            return False
        finally:
            self._stopping.clear()

    def get_process_stats(self, process_id: str) -> Optional[Dict]:
        """Get current statistics for a process."""
        if process_id not in self.processes:
            return None

        try:
            # Get latest stats without blocking
            stats = None
            try:
                while True:
                    stats = self.stats_queues[process_id].get_nowait()
            except Empty:
                pass  # Queue is empty, use last stats received

            if not stats:
                with self._lock:
                    if process_id in self.processes:
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
        scanner = None
        try:
            scanner = WalletScanner()
            scanner.start_scan()

            while not self._stopping.is_set():
                # Check for control commands
                try:
                    if not control_queue.empty():
                        cmd = control_queue.get_nowait()
                        if cmd == 'STOP':
                            break
                except Empty:
                    pass

                # Update statistics
                try:
                    stats = scanner.get_statistics()
                    stats['status'] = 'running'
                    stats_queue.put_nowait(stats)
                except Exception as stats_error:
                    logging.error(f"Error updating stats: {stats_error}")

                # Small sleep to prevent CPU overload
                from time import sleep
                sleep(0.1)

        except Exception as e:
            logging.error(f"Scanner process {process_id} error: {str(e)}")
        finally:
            try:
                if scanner:
                    scanner.stop_scan()
            except Exception as inner_e:
                logging.error(f"Error stopping scanner in process {process_id}: {str(inner_e)}")

            # Send final status update
            try:
                stats_queue.put_nowait({
                    'status': 'stopped',
                    'error': str(e) if 'e' in locals() else None
                })
            except Exception:
                pass  # Queue might be closed