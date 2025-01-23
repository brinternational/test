"""Version information for Bitcoin Wallet Education"""
from datetime import datetime

# Semantic versioning
VERSION = "0.1.1"  # Updated version for git automation feature
BUILD_TIMESTAMP = "2025-01-23 16:15:18"  # Updated whenever version.py is modified

def get_version_info():
    """Get formatted version information"""
    return {
        "version": VERSION,
        "build_date": BUILD_TIMESTAMP,
        "runtime_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }