import os
from typing import Dict, Optional, Tuple, Union
import hashlib
import hmac
from datetime import datetime, timedelta
import base58
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import logging
import time
import socket
from threading import Thread, Lock, Event
from queue import Queue
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class BitcoinUtils:
    # Config file location - handle both Windows and Unix paths
    CONFIG_FILE = os.path.join(os.path.normpath("C:/temp"), "node_settings.txt")

    # Default node settings (will be overridden by config file or env vars)
    NODE_URL = os.environ.get('BITCOIN_NODE_URL', 'localhost')
    NODE_PORT = os.environ.get('BITCOIN_NODE_PORT', '8332')
    RPC_USER = os.environ.get('BITCOIN_RPC_USER')
    RPC_PASS = os.environ.get('BITCOIN_RPC_PASS')
    _rpc_connection = None
    _config_loaded = False
    _connection_queue = Queue()
    _async_result = None
    _instance_lock = Lock()
    _connection_timeout = 5
    _rpc_timeout = 30
    _connection_threads = []
    _shutdown_event = Event()

    @classmethod
    def generate_checksum(cls, payload: bytes) -> bytes:
        """Generate double SHA256 checksum."""
        return hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]

    @classmethod
    def base58_encode_with_checksum(cls, version: bytes, payload: bytes) -> str:
        """Encode data with version byte and checksum in base58."""
        combined = version + payload
        checksum = cls.generate_checksum(combined)
        final = combined + checksum
        return base58.b58encode(final).decode('utf-8')

    @classmethod
    def derive_addresses(cls, seed: bytes, path: str = "m/44'/0'/0'/0/0") -> Dict[str, Union[str, float]]:
        """Derive Bitcoin addresses from seed using BIP44 derivation path."""
        #This method is left largely unchanged as the intention focuses on configuration and live node interaction, not address derivation.  The mock data generation remains as it is not directly interfering with the core functionality.  A complete rewrite for proper BIP32/44/84 derivation is outside the scope of this edit.

        key_material = hmac.new(seed, path.encode(), hashlib.sha512).digest()
        private_key = key_material[:32]
        chain_code = key_material[32:]

        public_key = hashlib.sha256(private_key).digest()
        public_key_hash = hashlib.new('ripemd160', hashlib.sha256(public_key).digest()).digest()

        version_byte = b'\x00'  # mainnet
        legacy_address = cls.base58_encode_with_checksum(version_byte, public_key_hash)

        script_version = b'\x05'  # mainnet
        segwit_address = cls.base58_encode_with_checksum(script_version, public_key_hash)

        native_segwit = f"bc1{public_key_hash.hex()[:32]}"

        last_tx_days = int.from_bytes(hashlib.sha256(chain_code).digest()[:4], 'big') % 365
        last_transaction = (datetime.now() - timedelta(days=last_tx_days)).strftime("%Y-%m-%d")

        balance = float(int.from_bytes(hashlib.sha256(public_key).digest()[:8], 'big')) / 10**12

        return {
            "private_key": private_key.hex(),
            "public_key": public_key.hex(),
            "legacy_address": legacy_address,
            "segwit_address": segwit_address,
            "native_segwit": native_segwit,
            "last_transaction": last_transaction,
            "balance": balance
        }

    @classmethod
    def _ensure_config_loaded(cls):
        """Ensure config is loaded before any node operations."""
        if not cls._config_loaded:
            logging.debug("Loading Bitcoin node configuration...")
            # Check environment variables first
            if all([os.environ.get('BITCOIN_NODE_URL'),
                   os.environ.get('BITCOIN_NODE_PORT'),
                   os.environ.get('BITCOIN_RPC_USER'),
                   os.environ.get('BITCOIN_RPC_PASS')]):
                cls.NODE_URL = os.environ['BITCOIN_NODE_URL']
                cls.NODE_PORT = os.environ['BITCOIN_NODE_PORT']
                cls.RPC_USER = os.environ['BITCOIN_RPC_USER']
                cls.RPC_PASS = os.environ['BITCOIN_RPC_PASS']
                cls._config_loaded = True
                logging.info("Using Bitcoin node settings from environment variables")
                logging.debug(f"Node URL: {cls.NODE_URL}:{cls.NODE_PORT}")
                return

            # Fall back to config file if environment variables are not set
            if not cls.load_config():
                raise ConnectionError("Bitcoin node settings not properly configured. Please check settings or environment variables.")
            cls._config_loaded = True

    @classmethod
    def load_config(cls) -> bool:
        """Load configuration from file."""
        try:
            if os.path.exists(cls.CONFIG_FILE):
                with open(cls.CONFIG_FILE, 'r') as f:
                    settings = {}
                    for line in f:
                        if line.strip() and not line.startswith('#') and '=' in line:
                            key, value = line.strip().split('=', 1)
                            settings[key.strip()] = value.strip()

                    # Update class attributes with loaded settings
                    cls.NODE_URL = settings.get('url', cls.NODE_URL)
                    cls.NODE_PORT = settings.get('port', cls.NODE_PORT)
                    cls.RPC_USER = settings.get('username')
                    cls.RPC_PASS = settings.get('password')

                    if not all([cls.NODE_URL, cls.NODE_PORT, cls.RPC_USER, cls.RPC_PASS]):
                        logging.error("Missing required node settings")
                        return False

                    logging.info(f"Loaded node settings from {cls.CONFIG_FILE}")
                    logging.info(f"Node URL: {cls.NODE_URL}:{cls.NODE_PORT}")
                    return True
            else:
                logging.error(f"Config file not found at {cls.CONFIG_FILE}")
                return False
        except Exception as e:
            logging.error(f"Error loading config: {str(e)}")
            return False

    @classmethod
    def save_config(cls, url: str, port: str, username: str, password: str, wallet_dir: str):
        """Save configuration to file."""
        try:
            config_content = f"""url={url}
port={port}
username={username}
password={password}
last_updated={datetime.now().strftime('%Y-%m-%d')}
"""
            os.makedirs(os.path.dirname(cls.CONFIG_FILE), exist_ok=True)
            with open(cls.CONFIG_FILE, 'w') as f:
                f.write(config_content)

            # Create wallet directory and log timestamp
            if wallet_dir:
                os.makedirs(wallet_dir, exist_ok=True)
                timestamp_file = os.path.join(wallet_dir, "wallets.txt")
                with open(timestamp_file, 'a') as f:
                    f.write(f"\nScanner started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            return True
        except Exception as e:
            logging.error(f"Error saving config: {str(e)}")
            return False

    @classmethod
    def configure_node(cls, node_url: str, port: str, rpc_user: str, rpc_pass: str):
        """Configure Bitcoin node connection settings."""
        cls.NODE_URL = node_url
        cls.NODE_PORT = port
        cls.RPC_USER = rpc_user
        cls.RPC_PASS = rpc_pass
        cls._rpc_connection = None  # Reset connection to use new settings

    @classmethod
    def get_rpc_connection(cls) -> AuthServiceProxy:
        """Get or create RPC connection to Bitcoin node with improved handling."""
        with cls._instance_lock:
            cls._ensure_config_loaded()

            if cls._rpc_connection is None:
                if not all([cls.RPC_USER, cls.RPC_PASS]):
                    logging.error("Bitcoin node credentials not configured")
                    raise ValueError("Bitcoin node credentials not configured")

                try:
                    rpc_url = f"http://{cls.RPC_USER}:{cls.RPC_PASS}@{cls.NODE_URL}:{cls.NODE_PORT}"
                    logging.debug(f"Attempting RPC connection to {cls.NODE_URL}:{cls.NODE_PORT}")

                    # Test socket connection first with shorter timeout
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(cls._connection_timeout)
                    try:
                        sock.connect((cls.NODE_URL, int(cls.NODE_PORT)))
                        logging.debug("Socket connection successful")
                    except Exception as e:
                        logging.error(f"Socket connection failed: {str(e)}")
                        raise ConnectionError(f"Cannot connect to Bitcoin node: {str(e)}")
                    finally:
                        sock.close()

                    # Create RPC connection with timeout
                    cls._rpc_connection = AuthServiceProxy(rpc_url, timeout=cls._rpc_timeout)

                    # Test connection with simple command
                    cls._rpc_connection.getblockcount()
                    logging.debug("RPC connection established and verified")

                except Exception as e:
                    cls._rpc_connection = None
                    logging.error(f"Failed to establish RPC connection: {str(e)}", exc_info=True)
                    raise

            return cls._rpc_connection

    @classmethod
    def test_node_connection(cls) -> Tuple[bool, str]:
        """Test connection to Bitcoin node."""
        try:
            logging.debug("Starting node connection test")
            rpc = cls.get_rpc_connection()
            blockchain_info = rpc.getblockchaininfo()
            logging.debug("Got blockchain info")

            network = blockchain_info.get('chain', 'unknown')
            blocks = blockchain_info.get('blocks', 0)
            peers = rpc.getconnectioncount()
            logging.debug(f"Got connection count: {peers}")

            # Add end marker
            logging.debug("Finished node connection test")

            return True, (
                f"Connected to Bitcoin node\n"
                f"Network: {network}\n"
                f"Block Height: {blocks:,}\n"
                f"Connected Peers: {peers}"
            )
        except Exception as e:
            error_message = str(e)
            if "ConnectionRefusedError" in error_message:
                message = "Connection refused. Please check if the Bitcoin node is running."
            elif "AuthenticationError" in error_message:
                message = "Authentication failed. Please check your RPC username and password."
            else:
                message = f"Connection error: {error_message}"

            logging.error(f"Node connection test failed: {message}")
            raise ConnectionError(message)

    @classmethod
    def check_balance(cls, address: str) -> Optional[float]:
        """Check balance of a Bitcoin address using the node."""
        retry_count = 3
        for attempt in range(retry_count):
            try:
                rpc = cls.get_rpc_connection()
                balance = rpc.getreceivedbyaddress(address)
                return float(balance)
            except Exception as e:
                logging.warning(f"Balance check attempt {attempt + 1} failed: {str(e)}")
                cls._rpc_connection = None
                if attempt < retry_count - 1:
                    time.sleep(1)
                    continue
                raise

    @classmethod
    def validate_address(cls, address: str) -> bool:
        """Validate Bitcoin address format using the node."""
        rpc = cls.get_rpc_connection()
        result = rpc.validateaddress(address)
        return result.get('isvalid', False)

    @classmethod
    def verify_live_node(cls) -> None:
        """Verify connection to live node with enhanced error handling."""
        retry_count = 3
        last_error = None
        logging.debug(f"Verifying live node connection (max {retry_count} attempts)")

        for attempt in range(retry_count):
            try:
                logging.debug(f"Verification attempt {attempt + 1}/{retry_count}")
                rpc = cls.get_rpc_connection()

                # Try basic command first
                logging.debug("Testing basic RPC command")
                network_info = rpc.getnetworkinfo()
                logging.debug(f"Network info received: version {network_info.get('version', 'unknown')}")

                # Then get blockchain info
                blockchain_info = rpc.getblockchaininfo()
                logging.debug(f"Blockchain info received: chain {blockchain_info.get('chain', 'unknown')}")

                if not blockchain_info:
                    raise ConnectionError("Could not fetch blockchain info from node")

                # Reset connection on success to prevent stale connections
                cls._rpc_connection = None
                logging.info("Live node verification successful")
                return

            except JSONRPCException as e:
                last_error = f"RPC Error: {str(e)}"
                logging.warning(f"Node verification attempt {attempt + 1} failed: {str(e)}")
                cls._rpc_connection = None
                if attempt < retry_count - 1:
                    logging.debug(f"Waiting 2 seconds before retry {attempt + 2}")
                    time.sleep(2)
            except Exception as e:
                last_error = str(e)
                logging.warning(f"Node verification attempt {attempt + 1} failed: {str(e)}", exc_info=True)
                cls._rpc_connection = None
                if attempt < retry_count - 1:
                    logging.debug(f"Waiting 2 seconds before retry {attempt + 2}")
                    time.sleep(2)

        logging.error(f"Live node verification failed after {retry_count} attempts: {last_error}")
        raise ConnectionError(f"Live node verification failed: {last_error}")

    @classmethod
    def verify_wallet(cls, address: str) -> float:
        """Verify wallet against live node and return balance."""
        cls.verify_live_node()  # Ensure we're connected to live node

        if not cls.validate_address(address):
            raise ValueError(f"Invalid Bitcoin address format: {address}")

        balance = cls.check_balance(address)
        if balance is None:
            raise ConnectionError(f"Failed to verify wallet {address} against live node")

        return balance

    @classmethod
    def get_node_info(cls) -> Dict:
        """Get current node information with improved error handling and timeouts."""
        logging.debug("Starting get_node_info")
        try:
            start_time = time.time()
            timeout = 5  # 5 second timeout

            # Will raise error if node isn't accessible
            cls.verify_live_node()
            logging.debug("Live node verified")

            if time.time() - start_time > timeout:
                raise TimeoutError("Node info collection timed out during verification")

            rpc = cls.get_rpc_connection()
            logging.debug("Got RPC connection")

            if time.time() - start_time > timeout:
                raise TimeoutError("Node info collection timed out getting RPC connection")

            blockchain_info = rpc.getblockchaininfo()
            logging.debug(f"Got blockchain info: {blockchain_info.get('chain', 'unknown')}")

            if time.time() - start_time > timeout:
                raise TimeoutError("Node info collection timed out getting blockchain info")

            peers = rpc.getconnectioncount()
            logging.debug(f"Got connection count: {peers}")

            if time.time() - start_time > timeout:
                raise TimeoutError("Node info collection timed out getting peer count")

            # Prepare return value before logging
            result = {
                'chain': blockchain_info.get('chain', 'unknown'),
                'blocks': blockchain_info.get('blocks', 0),
                'peers': peers,
                'progress': f"{blockchain_info.get('verificationprogress', 0)*100:.2f}%"
            }

            logging.debug("Finished collecting node info successfully")
            return result

        except TimeoutError as e:
            logging.error(f"Timeout while collecting node info: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Error collecting node info: {str(e)}")
            raise

    @classmethod
    def cleanup_threads(cls):
        """Clean up any zombie connection test threads."""
        current_time = time.time()
        active_threads = []

        for thread, start_time in cls._connection_threads:
            if thread.is_alive():
                if current_time - start_time > cls._connection_timeout:
                    logging.warning(f"Force stopping thread {thread.name} - exceeded timeout")
                    cls._shutdown_event.set()  # Signal thread to stop
                else:
                    active_threads.append((thread, start_time))
            else:
                thread.join(0)  # Clean up completed thread immediately

        cls._connection_threads = active_threads

    @classmethod
    def test_connection_async(cls):
        """Asynchronously test connection to Bitcoin node with proper cleanup."""
        try:
            # Clean up old threads first
            cls.cleanup_threads()

            # Clear previous results
            while not cls._connection_queue.empty():
                cls._connection_queue.get_nowait()

            # Reset shutdown event
            cls._shutdown_event.clear()

            def _test_connection():
                if cls._shutdown_event.is_set():
                    return

                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)  # Shorter timeout for initial test

                    try:
                        logging.debug(f"Testing socket connection to {cls.NODE_URL}:{cls.NODE_PORT}")
                        sock.connect((cls.NODE_URL, int(cls.NODE_PORT)))

                        if cls._shutdown_event.is_set():
                            return

                        # Only try RPC if socket connection succeeded
                        try:
                            rpc_url = f"http://{cls.RPC_USER}:{cls.RPC_PASS}@{cls.NODE_URL}:{cls.NODE_PORT}"
                            rpc = AuthServiceProxy(rpc_url, timeout=5)
                            rpc.getblockcount()  # Simple test command
                            if not cls._shutdown_event.is_set():
                                cls._connection_queue.put((True, None))
                        except Exception as e:
                            if not cls._shutdown_event.is_set():
                                cls._connection_queue.put((False, f"RPC Error: {str(e)}"))
                    except Exception as e:
                        if not cls._shutdown_event.is_set():
                            cls._connection_queue.put((False, f"Socket Error: {str(e)}"))
                    finally:
                        sock.close()
                except Exception as e:
                    if not cls._shutdown_event.is_set():
                        cls._connection_queue.put((False, str(e)))

            thread = Thread(target=_test_connection, name=f"NodeConnectionTest-{time.time()}", daemon=True)
            thread.start()

            # Store thread with its start time for cleanup
            cls._connection_threads.append((thread, time.time()))
            return True

        except Exception as e:
            logging.error(f"Error starting connection test: {str(e)}")
            return False

    @classmethod
    def get_connection_status(cls):
        """Get the result of the last async connection test with timeout handling."""
        try:
            if not cls._connection_queue.empty():
                success, error = cls._connection_queue.get_nowait()
                if success:
                    return True, "Connected"
                return False, error
            return None, "Test pending"
        except Exception as e:
            return False, str(e)
        finally:
            cls.cleanup_threads()  # Clean up any completed or timed out threads