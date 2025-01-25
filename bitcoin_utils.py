import os
from typing import Dict, Optional, Tuple, Union
import hashlib
import hmac
from datetime import datetime, timedelta
import random
import base58
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

class BitcoinUtils:
    # Config file location
    CONFIG_FILE = r"C:\temp\node_settings.txt"

    # Default node settings
    NODE_URL = 'localhost'
    NODE_PORT = '8332'
    RPC_USER = 'your_rpc_username'
    RPC_PASS = 'your_rpc_password'
    _rpc_connection = None

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
        """
        Derive Bitcoin addresses from seed using BIP44 derivation path.
        For educational purposes, we're generating deterministic but mock addresses.
        In production, this would use proper BIP32/44/84 derivation.
        """
        # Generate deterministic keys based on the seed and path
        key_material = hmac.new(seed, path.encode(), hashlib.sha512).digest()
        private_key = key_material[:32]
        chain_code = key_material[32:]

        # Generate mock public key (in real implementation, this would use secp256k1)
        public_key = hashlib.sha256(private_key).digest()

        # Generate different address formats
        public_key_hash = hashlib.new('ripemd160', hashlib.sha256(public_key).digest()).digest()

        # P2PKH address (Legacy)
        version_byte = b'\x00'  # mainnet
        legacy_address = cls.base58_encode_with_checksum(version_byte, public_key_hash)

        # P2SH address (SegWit)
        script_version = b'\x05'  # mainnet
        segwit_address = cls.base58_encode_with_checksum(script_version, public_key_hash)

        # Native SegWit (mock bech32 implementation)
        native_segwit = f"bc1{public_key_hash.hex()[:32]}"

        # Generate mock transaction history (deterministic based on chain_code)
        last_tx_days = int.from_bytes(hashlib.sha256(chain_code).digest()[:4], 'big') % 365
        last_transaction = (datetime.now() - timedelta(days=last_tx_days)).strftime("%Y-%m-%d")

        # Educational balance generation (deterministic based on address)
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
    def test_node_connection(cls) -> Tuple[bool, str]:
        """Test connection to Bitcoin node."""
        try:
            rpc = cls.get_rpc_connection()
            blockchain_info = rpc.getblockchaininfo()

            network = blockchain_info.get('chain', 'unknown')
            blocks = blockchain_info.get('blocks', 0)
            peers = rpc.getconnectioncount()

            return True, (
                f"Successfully connected to Bitcoin node\n"
                f"Network: {network}\n"
                f"Block Height: {blocks:,}\n"
                f"Connected Peers: {peers}"
            )
        except Exception as e:
            if "ConnectionRefusedError" in str(e):
                message = "Connection refused. Please check if the Bitcoin node is running."
            elif "AuthenticationError" in str(e):
                message = "Authentication failed. Please check your RPC username and password."
            else:
                message = f"Connection error: {str(e)}"

            return False, f"Error: {message}"

    @classmethod
    def save_config(cls, url: str, port: str, username: str, password: str, wallet_dir: str):
        """Save configuration to file."""
        try:
            config_content = f"""# Bitcoin Node Configuration
# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
url={url}
port={port}
username={username}
password={password}
wallet_dir={wallet_dir}
"""
            os.makedirs(os.path.dirname(cls.CONFIG_FILE), exist_ok=True)
            with open(cls.CONFIG_FILE, 'w') as f:
                f.write(config_content)

            # Create wallet directory with timestamp
            os.makedirs(wallet_dir, exist_ok=True)
            timestamp_file = os.path.join(wallet_dir, "wallets.txt")
            with open(timestamp_file, 'a') as f:
                f.write(f"\nScanner started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            return True
        except Exception as e:
            print(f"Error saving config: {str(e)}")
            return False

    @classmethod
    def load_config(cls):
        """Load configuration from file."""
        try:
            if os.path.exists(cls.CONFIG_FILE):
                with open(cls.CONFIG_FILE, 'r') as f:
                    settings = {}
                    for line in f:
                        if line.startswith('#') or '=' not in line:
                            continue
                        key, value = line.strip().split('=', 1)
                        settings[key] = value

                    # Update class attributes with loaded settings
                    cls.NODE_URL = settings.get('url', cls.NODE_URL)
                    cls.NODE_PORT = settings.get('port', cls.NODE_PORT)
                    cls.RPC_USER = settings.get('username', cls.RPC_USER)
                    cls.RPC_PASS = settings.get('password', cls.RPC_PASS)

                    return True
        except Exception as e:
            print(f"Error loading config: {str(e)}")
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
        """Get or create RPC connection to Bitcoin node."""
        if cls._rpc_connection is None:
            cls.load_config()

            if not all([cls.RPC_USER, cls.RPC_PASS]):
                raise ValueError("Bitcoin node credentials not configured.")

            rpc_url = f"http://{cls.RPC_USER}:{cls.RPC_PASS}@{cls.NODE_URL}:{cls.NODE_PORT}"
            cls._rpc_connection = AuthServiceProxy(rpc_url)

        return cls._rpc_connection

    @classmethod
    def check_balance(cls, address: str) -> Optional[float]:
        """Check balance of a Bitcoin address."""
        try:
            rpc = cls.get_rpc_connection()
            balance = rpc.getreceivedbyaddress(address)
            return float(balance)
        except Exception as e:
            print(f"Error checking balance: {str(e)}")
            return None

    @classmethod
    def validate_address(cls, address: str) -> bool:
        """Validate Bitcoin address format."""
        try:
            rpc = cls.get_rpc_connection()
            result = rpc.validateaddress(address)
            return result.get('isvalid', False)
        except Exception as e:
            print(f"Error validating address: {str(e)}")
            return False