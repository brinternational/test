import time
from typing import Dict, List
from datetime import datetime
import random
import os
import subprocess

BUILD_TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Added BUILD_TIMESTAMP

class WalletScanner:
    def __init__(self):
        self.total_scanned = 0
        self.wallets_with_balance = []
        self.start_time = None
        self.scanning = False

    def start_scan(self):
        """Start or resume scanning."""
        self.start_time = time.time()
        self.scanning = True

    def stop_scan(self):
        """Stop scanning."""
        self.scanning = False

    def git_commit_changes(self, message: str):
        """Commit changes to git repository"""
        try:
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', message], check=True)
            return True, "Changes committed to git successfully"
        except subprocess.CalledProcessError as e:
            return False, f"Git commit failed: {str(e)}"

    def add_wallet(self, wallet_info: Dict):
        """Add a wallet to the scan results."""
        self.total_scanned += 1
        if wallet_info.get('balance', 0) > 0:
            self.wallets_with_balance.append(wallet_info)
            self._save_to_file(wallet_info)

    def get_scan_rate(self) -> float:
        """Calculate wallets scanned per minute."""
        if not self.start_time or not self.scanning:
            return 0.0
        elapsed_minutes = (time.time() - self.start_time) / 60
        return self.total_scanned / elapsed_minutes if elapsed_minutes > 0 else 0

    def get_statistics(self) -> Dict:
        """Get current scanning statistics."""
        return {
            'total_scanned': self.total_scanned,
            'wallets_with_balance': len(self.wallets_with_balance),
            'scan_rate': round(self.get_scan_rate(), 2)
        }

    def _save_to_file(self, wallet_info: Dict):
        """Save wallet with balance to file."""
        try:
            # Ensure C:\temp directory exists
            os.makedirs(r"C:\temp", exist_ok=True)

            # Save to C:\temp\wallets.txt with today's date
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(r"C:\temp\wallets.txt", 'a') as f:
                f.write(f"\n=== Wallet Found at {timestamp} (Created on {BUILD_TIMESTAMP}) ===\n")
                f.write(f"Address: {wallet_info['address']}\n")
                f.write(f"Balance: {wallet_info['balance']} BTC\n")
                f.write(f"Last Transaction: {wallet_info['last_transaction']}\n")
                f.write("="*40 + "\n")

            # Commit changes to git
            success, git_message = self.git_commit_changes(
                f"Add new wallet at {timestamp}"
            )

            if not success:
                print(f"Warning: {git_message}")

        except Exception as e:
            print(f"Error saving wallet: {str(e)}")