"""Version information for Bitcoin Wallet Education"""
from datetime import datetime

# Semantic versioning
VERSION = "0.2.0"  # Major update with aggressive multiprocessing optimizations
BUILD_TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Updated whenever version.py is modified

def get_version_info():
    """Get formatted version information"""
    return {
        "version": VERSION,
        "build_date": BUILD_TIMESTAMP,
        "runtime_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }