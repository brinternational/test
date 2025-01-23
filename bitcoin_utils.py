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
                raise ValueError("Bitcoin node credentials not configured. Use configure_node() or set environment variables.")

            rpc_url = f"http://{BitcoinUtils.RPC_USER}:{BitcoinUtils.RPC_PASS}@{BitcoinUtils.NODE_URL}:{BitcoinUtils.NODE_PORT}"
            BitcoinUtils._rpc_connection = AuthServiceProxy(rpc_url)

        return BitcoinUtils._rpc_connection

    @staticmethod
    def test_node_connection() -> Tuple[bool, str]:
        """Test connection to Bitcoin node."""
        try:
            rpc = BitcoinUtils.get_rpc_connection()
            blockchain_info = rpc.getblockchaininfo()
            return True, f"Connected to node. Chain: {blockchain_info['chain']}, Blocks: {blockchain_info['blocks']}"
        except JSONRPCException as e:
            return False, f"RPC Error: {str(e)}"
        except Exception as e:
            return False, f"Connection Error: {str(e)}"

    @staticmethod
    def derive_addresses(seed: bytes, path: str = "m/44'/0'/0'/0/0") -> Dict[str, str]:
        """
        Mock function to derive Bitcoin addresses from seed.
        In real implementation, this would use proper BIP32/44/84 derivation.
        """
        # This is a simplified mock implementation
        # In production, use proper Bitcoin libraries
        mock_private_key = hmac.new(seed, path.encode(), hashlib.sha512).hexdigest()
        mock_public_key = hashlib.sha256(mock_private_key.encode()).hexdigest()
        mock_address = "bc1q" + mock_public_key[:32]

        # Generate a random date within the last year for educational purposes
        days_ago = random.randint(0, 365)
        last_transaction = datetime.now() - timedelta(days=days_ago)

        # Add a small chance (1%) of having a balance for demonstration
        balance = random.uniform(0.1, 2.0) if random.random() < 0.01 else 0.0

        return {
            "private_key": mock_private_key,
            "public_key": mock_public_key,
            "address": mock_address,
            "last_transaction": last_transaction.strftime("%Y-%m-%d"),
            "balance": balance
        }

    @staticmethod
    def check_balance(address: str) -> Optional[float]:
        """
        Check balance of a Bitcoin address using connected node.
        Falls back to mock data if node is not configured.
        """
        try:
            rpc = BitcoinUtils.get_rpc_connection()
            # Note: This assumes the address is in the wallet
            # For arbitrary addresses, you'd need to use a block explorer API
            balance = rpc.getreceivedbyaddress(address)
            return float(balance)
        except (JSONRPCException, ValueError) as e:
            print(f"Warning: Using mock data. Node error: {str(e)}")
            return 0.0

    @staticmethod
    def validate_address(address: str) -> bool:
        """
        Validate Bitcoin address format using the node if available,
        falls back to basic validation if node is not configured.
        """
        try:
            rpc = BitcoinUtils.get_rpc_connection()
            result = rpc.validateaddress(address)
            return result.get('isvalid', False)
        except:
            # Basic format checking as fallback
            if not address:
                return False
            valid_prefixes = ['1', '3', 'bc1']
            return any(address.startswith(prefix) for prefix in valid_prefixes)