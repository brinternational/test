import hashlib
import hmac
import random
from typing import List, Tuple

class WalletGenerator:
    # BIP39 wordlist (first 20 words shown for brevity)
    BIP39_WORDS = [
        "abandon", "ability", "able", "about", "above",
        "absent", "absorb", "abstract", "absurd", "abuse",
        "access", "accident", "account", "accuse", "achieve",
        "acid", "acoustic", "acquire", "across", "act"
    ]  # Note: In real implementation, include all 2048 words
    
    @staticmethod
    def generate_entropy(bits: int = 128) -> bytes:
        """Generate random entropy for seed phrase."""
        return bytes([random.randint(0, 255) for _ in range(bits // 8)])
    
    @staticmethod
    def entropy_to_words(entropy: bytes) -> List[str]:
        """Convert entropy to BIP39 seed phrase."""
        binary = bin(int.from_bytes(entropy, 'big'))[2:].zfill(len(entropy) * 8)
        checksum = bin(int.from_bytes(
            hashlib.sha256(entropy).digest(), 'big'))[2:].zfill(256)[:len(entropy) * 8 // 32]
        
        binary_with_checksum = binary + checksum
        words = []
        
        for i in range(0, len(binary_with_checksum), 11):
            index = int(binary_with_checksum[i:i+11], 2)
            words.append(WalletGenerator.BIP39_WORDS[index])
            
        return words
    
    @staticmethod
    def generate_seed_phrase(word_count: int = 12) -> Tuple[List[str], bytes]:
        """Generate a BIP39 seed phrase with specified word count."""
        entropy_bits = (word_count * 11) - (word_count // 3)
        entropy = WalletGenerator.generate_entropy(entropy_bits)
        words = WalletGenerator.entropy_to_words(entropy)
        return words, entropy
    
    @staticmethod
    def verify_checksum(words: List[str]) -> bool:
        """Verify the checksum of a seed phrase."""
        # Implementation would verify BIP39 checksum
        # Simplified for educational purposes
        return len(words) in [12, 15, 18, 21, 24]

