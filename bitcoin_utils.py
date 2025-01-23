import os
from typing import Dict, Optional, Tuple
import hashlib
import hmac
from datetime import datetime, timedelta
import random
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

class BitcoinUtils:
    # Default testnet node settings (can be overridden via environment variables)
    NODE_URL = os.getenv('BITCOIN_NODE_URL', 'localhost')
    NODE_PORT = os.getenv('BITCOIN_NODE_PORT', '8332')
    RPC_USER = os.getenv('BITCOIN_RPC_USER', '')
    RPC_PASS = os.getenv('BITCOIN_RPC_PASS', '')
    _rpc_connection = None

    # Mock data for educational purposes
    MOCK_MODE = True  # Default to mock mode if node connection fails
    MOCK_BLOCKCHAIN_HEIGHT = 800000
    MOCK_NETWORK = "testnet"

    @staticmethod
    def configure_node(node_url: str, port: str, rpc_user: str, rpc_pass: str):
        """Configure Bitcoin node connection settings."""
        BitcoinUtils.NODE_URL = node_url
        BitcoinUtils.NODE_PORT = port
        BitcoinUtils.RPC_USER = rpc_user
        BitcoinUtils.RPC_PASS = rpc_pass
        BitcoinUtils._rpc_connection = None  # Reset connection to use new settings

    @staticmethod
    def get_rpc_connection() -> AuthServiceProxy:
        """Get or create RPC connection to Bitcoin node."""
        if BitcoinUtils._rpc_connection is None:
            if not all([BitcoinUtils.RPC_USER, BitcoinUtils.RPC_PASS]):
                raise ValueError("Bitcoin node credentials not configured.")

            rpc_url = f"http://{BitcoinUtils.RPC_USER}:{BitcoinUtils.RPC_PASS}@{BitcoinUtils.NODE_URL}:{BitcoinUtils.NODE_PORT}"
            BitcoinUtils._rpc_connection = AuthServiceProxy(rpc_url)

        return BitcoinUtils._rpc_connection

    @staticmethod
    def test_node_connection() -> Tuple[bool, str]:
        """Test connection to Bitcoin node, fallback to mock mode if connection fails."""
        try:
            rpc = BitcoinUtils.get_rpc_connection()
            blockchain_info = rpc.getblockchaininfo()
            BitcoinUtils.MOCK_MODE = False
            return True, f"Connected to node. Chain: {blockchain_info['chain']}, Blocks: {blockchain_info['blocks']}"
        except Exception as e:
            BitcoinUtils.MOCK_MODE = True
            return False, (
                f"Using educational simulation mode.\n"
                f"Mock Chain: {BitcoinUtils.MOCK_NETWORK}\n"
                f"Mock Blocks: {BitcoinUtils.MOCK_BLOCKCHAIN_HEIGHT}\n"
                f"(Original error: {str(e)})"
            )

    @staticmethod
    def derive_addresses(seed: bytes, path: str = "m/44'/0'/0'/0/0") -> Dict[str, str]:
        """
        Derive Bitcoin addresses from seed (mock implementation for educational purposes).
        In real implementation, this would use proper BIP32/44/84 derivation.
        """
        # Generate deterministic but mock values based on the seed
        mock_private_key = hmac.new(seed, path.encode(), hashlib.sha512).hexdigest()
        mock_public_key = hashlib.sha256(mock_private_key.encode()).hexdigest()

        # Generate different address formats for education
        legacy_address = "1" + mock_public_key[:32]  # Legacy format
        segwit_address = "3" + mock_public_key[32:64]  # SegWit format
        native_segwit = "bc1" + mock_public_key[:32]  # Native SegWit format

        # Generate mock transaction history
        days_ago = random.randint(0, 365)
        last_transaction = datetime.now() - timedelta(days=days_ago)

        # Educational balance generation (1% chance of having balance)
        balance = random.uniform(0.1, 2.0) if random.random() < 0.01 else 0.0

        return {
            "private_key": mock_private_key,
            "public_key": mock_public_key,
            "legacy_address": legacy_address,
            "segwit_address": segwit_address,
            "native_segwit": native_segwit,
            "last_transaction": last_transaction.strftime("%Y-%m-%d"),
            "balance": balance
        }

    @staticmethod
    def check_balance(address: str) -> Optional[float]:
        """Check balance of a Bitcoin address."""
        if not BitcoinUtils.MOCK_MODE:
            try:
                rpc = BitcoinUtils.get_rpc_connection()
                balance = rpc.getreceivedbyaddress(address)
                return float(balance)
            except Exception as e:
                print(f"Node error, falling back to mock mode: {str(e)}")
                BitcoinUtils.MOCK_MODE = True

        # Mock balance for educational purposes
        # Generate consistent mock balance based on address
        address_hash = int(hashlib.sha256(address.encode()).hexdigest()[:8], 16)
        mock_balance = (address_hash % 1000) / 100 if address_hash % 100 == 0 else 0
        return mock_balance

    @staticmethod
    def validate_address(address: str) -> bool:
        """Validate Bitcoin address format."""
        if not BitcoinUtils.MOCK_MODE:
            try:
                rpc = BitcoinUtils.get_rpc_connection()
                result = rpc.validateaddress(address)
                return result.get('isvalid', False)
            except:
                BitcoinUtils.MOCK_MODE = True

        # Basic format checking for educational purposes
        if not address:
            return False

        # Check different address formats
        valid_prefixes = {
            '1': 34,  # Legacy
            '3': 34,  # SegWit
            'bc1': 42  # Native SegWit
        }

        # Validate prefix and length
        for prefix, length in valid_prefixes.items():
            if address.startswith(prefix):
                return len(address) == length

        return False