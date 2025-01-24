# Installation Guide

## System Requirements
- Python 3.11 or later
- Git (for version control)
- Bitcoin node (optional - application will run in educational mode without it)

## Installation Steps

### 1. Install Python
Download and install Python 3.11 from [python.org](https://www.python.org/downloads/)

Important: During Python installation:
- Check "Add Python to PATH"
- Ensure "tcl/tk and IDLE" is selected (this includes tkinter)

Verify installation:
```bash
python --version
```

### 2. Clone the Repository
```bash
git clone <your-repository-url>
cd <repository-directory>
```

### 3. Install Required Packages
```bash
pip install base58check python-bitcoinrpc
```

Note: tkinter comes with Python installation and doesn't need to be installed separately via pip.

### 4. Run the Application
```bash
python main.py
```

## Configuration (Optional)

### Bitcoin Node Settings
If you have a Bitcoin node:
1. Navigate to the Node Settings tab in the application
2. Enter your node's:
   - URL (default: localhost)
   - Port (default: 8332)
   - RPC Username
   - RPC Password

The application will run in educational mode if no node is configured.

## Troubleshooting

### Common Issues

1. Module Import Errors
   ```
   ModuleNotFoundError: No module named 'base58check'
   ```
   Solution: Run `pip install base58check`

2. Bitcoin Node Connection Issues
   - Verify your node is running
   - Check your RPC credentials
   - The application will continue in educational mode

### Support
For additional help:
1. Check the application logs in `bitcoin_wallet.log`
2. Review console output for error messages
3. Ensure all dependencies are installed correctly

## Development Setup
If you want to contribute to development:
1. Clone the repository
2. Install all dependencies
3. Run the test suite: `python test_node.py`

The application uses Tkinter for the GUI, which is included with Python's standard library.