from typing import Dict, Optional
import hashlib
import hmac
from datetime import datetime, timedelta
import random

class BitcoinUtils:
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
        Mock function to check balance of a Bitcoin address.
        In real implementation, this would connect to a Bitcoin node.
        """
        # This is a mock implementation
        # In production, connect to actual Bitcoin node
        return 0.0

    @staticmethod
    def validate_address(address: str) -> bool:
        """
        Validate Bitcoin address format.
        Basic validation for educational purposes.
        """
        if not address:
            return False

        # Basic format checking
        valid_prefixes = ['1', '3', 'bc1']
        return any(address.startswith(prefix) for prefix in valid_prefixes)