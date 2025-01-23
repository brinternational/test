from bitcoin_utils import BitcoinUtils
import sys

def test_bitcoin_node():
    print("Testing Bitcoin node connection...")
    try:
        rpc = BitcoinUtils.get_rpc_connection()
        blockchain_info = rpc.getblockchaininfo()

        # Check sync status
        if blockchain_info.get('initialblockdownload', True):
            print("Node is still syncing:")
            print(f"Current Height: {blockchain_info.get('blocks', 0)}")
            print(f"Headers: {blockchain_info.get('headers', 0)}")
            print(f"Verification Progress: {blockchain_info.get('verificationprogress', 0)*100:.2f}%")
            return True, "Node is operational but still syncing"

        success, message = BitcoinUtils.test_node_connection()
        print(f"Connection test result: {'Success' if success else 'Failed'}")
        print(f"Message: {message}")
        return success
    except Exception as e:
        print(f"Error testing node connection: {str(e)}", file=sys.stderr)
        print("Falling back to educational simulation mode")
        print(f"Mock Chain: {BitcoinUtils.MOCK_NETWORK}")
        print(f"Mock Blocks: {BitcoinUtils.MOCK_BLOCKCHAIN_HEIGHT}")
        return False

if __name__ == "__main__":
    test_bitcoin_node()