"""Deploy contracts/FacePostAnchor.sol to the Ethereum Sepolia testnet.

Usage:
    1. Set SEPOLIA_RPC_URL and PRIVATE_KEY in your .env file.
    2. Make sure the deployer wallet has a little Sepolia test ETH
       (free faucets: sepoliafaucet.com, alchemy.com/faucets/ethereum-sepolia).
    3. Run:  python deploy_contract.py
    4. Copy the printed CONTRACT_ADDRESS into your .env file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from solcx import compile_source, get_installed_solc_versions, install_solc
from web3 import Web3

load_dotenv()

SOLC_VERSION = "0.8.20"
SEPOLIA_CHAIN_ID = 11155111
CONTRACT_PATH = Path(__file__).parent / "contracts" / "FacePostAnchor.sol.txt"


def main() -> None:
    rpc_url = os.getenv("SEPOLIA_RPC_URL")
    private_key = os.getenv("PRIVATE_KEY")

    if not rpc_url or not private_key:
        raise SystemExit(
            "Set SEPOLIA_RPC_URL and PRIVATE_KEY in .env first (see .env.example)."
        )

    if SOLC_VERSION not in (get_installed_solc_versions() or []):
        print(f"Installing solc {SOLC_VERSION} (one-time download)...")
        install_solc(SOLC_VERSION)

    print(f"Compiling {CONTRACT_PATH.name}...")
    source = CONTRACT_PATH.read_text(encoding="utf-8")
    compiled = compile_source(
        source,
        output_values=["abi", "bin"],
        solc_version=SOLC_VERSION,
    )
    contract_interface = compiled["<stdin>:FacePostAnchor"]

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise SystemExit("Could not connect to the Sepolia RPC URL.")

    account = Account.from_key(private_key)
    balance = w3.eth.get_balance(account.address)
    print(f"Deployer: {account.address}  balance: {w3.from_wei(balance, 'ether')} ETH")

    if balance == 0:
        raise SystemExit(
            "Deployer wallet has no Sepolia test ETH. Fund it from a faucet first."
        )

    contract_factory = w3.eth.contract(
        abi=contract_interface["abi"],
        bytecode=contract_interface["bin"],
    )

    transaction = contract_factory.constructor().build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address, "pending"),
            "chainId": SEPOLIA_CHAIN_ID,
            "gasPrice": w3.eth.gas_price,
        }
    )

    signed = account.sign_transaction(transaction)
    raw_transaction = getattr(signed, "raw_transaction", signed.rawTransaction)

    tx_hash = w3.eth.send_raw_transaction(raw_transaction)
    print(f"Deployment transaction: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    if receipt.status != 1:
        raise SystemExit("Deployment transaction failed.")

    print("\n=============================================================")
    print(f"CONTRACT ADDRESS: {receipt.contractAddress}")
    print("=============================================================")
    print("\nAdd this line to your .env file:")
    print(f"CONTRACT_ADDRESS={receipt.contractAddress}")


if __name__ == "__main__":
    main()