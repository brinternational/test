# Bitcoin Wallet Educational Application

An educational desktop application for teaching Bitcoin wallet concepts.

## Local Setup Instructions

### Prerequisites
1. Python 3.10 or higher
2. Tkinter (usually comes with Python installation)
3. pip (Python package manager)

### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/brinternational/test.git
cd test
```

2. Install required packages:
```bash
pip install python-bitcoinrpc
```

3. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Update the values in `.env` with your Bitcoin node credentials (optional - the app works in educational mode without a node)

### Running the Application

Run the main application:
```bash
python main.py
```

## Features

- Interactive Bitcoin wallet generation
- SHA256 hash visualization
- Educational content about Bitcoin wallets
- Mock blockchain scanning capabilities
- Bitcoin node integration (optional)

## Development Mode

The application runs in educational/simulation mode by default if no Bitcoin node is connected. This provides a safe environment for learning about Bitcoin wallets and transactions.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
