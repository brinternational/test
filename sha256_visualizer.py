import tkinter as tk
from tkinter import ttk
import hashlib
from typing import List

class SHA256Visualizer:
    @staticmethod
    def get_padding_visualization(message: str) -> List[str]:
        """Visualize the SHA256 padding process."""
        # Convert message to binary
        message_bin = ''.join(format(ord(c), '08b') for c in message)
        message_length = len(message_bin)
        
        # Calculate padding
        k = (448 - (message_length + 1)) % 512
        if k < 0:
            k += 512
            
        # Create visualization steps
        steps = [
            f"1. Original message ({message_length} bits):",
            message_bin,
            "2. Add '1' bit:",
            message_bin + "1",
            f"3. Add {k} zero bits for padding:",
            message_bin + "1" + "0" * k,
            "4. Add original length as 64-bit number:",
            message_bin + "1" + "0" * k + format(message_length, '064b')
        ]
        
        return steps
    
    @staticmethod
    def visualize_compression(message: str) -> List[str]:
        """Visualize the SHA256 compression function steps."""
        # Initial hash values (first 8 prime numbers' square roots' fractional parts)
        h0 = 0x6a09e667
        h1 = 0xbb67ae85
        h2 = 0x3c6ef372
        h3 = 0xa54ff53a
        h4 = 0x510e527f
        h5 = 0x9b05688c
        h6 = 0x1f83d9ab
        h7 = 0x5be0cd19
        
        # Create visualization steps
        steps = [
            "Initial hash values:",
            f"h0: {format(h0, '08x')}",
            f"h1: {format(h1, '08x')}",
            f"h2: {format(h2, '08x')}",
            f"h3: {format(h3, '08x')}",
            f"h4: {format(h4, '08x')}",
            f"h5: {format(h5, '08x')}",
            f"h6: {format(h6, '08x')}",
            f"h7: {format(h7, '08x')}",
            "",
            "Final hash:",
            hashlib.sha256(message.encode()).hexdigest()
        ]
        
        return steps
