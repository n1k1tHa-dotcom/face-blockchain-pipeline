import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

load_dotenv()

SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

LOCAL_CHAIN_FILE = Path(".local_chain.json")
LOCAL_CHAIN_NAME = "local_simulated_chain"

ABI = [
    {
        "inputs": [
            {
                "internalType": "bytes32",
                "name": "contentHash",
                "type": "bytes32",
            }
        ],
        "name": "anchor",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "internalType": "bytes32",
                "name": "contentHash",
                "type": "bytes32",
            }
        ],
        "name": "verify",
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


def chain_mode() -> str:
    """'sepolia' when the real testnet is fully configured, else 'local'."""
    if SEPOLIA_RPC_URL and PRIVATE_KEY and CONTRACT_ADDRESS:
        return "sepolia"
    return "local"


def network_name() -> str:
    return "Ethereum Sepolia" if chain_mode() == "sepolia" else LOCAL_CHAIN_NAME


def create_content_hash(post_data: dict) -> str:
    stable_data = {
        "post_url": post_data.get("post_url", ""),
        "image_url": post_data.get("image_url", ""),
        "caption": post_data.get("caption", ""),
        "profile_url": post_data.get("profile_url", ""),
    }

    canonical_json = json.dumps(
        stable_data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Local simulated chain (fallback so the demo always runs end-to-end)
# ---------------------------------------------------------------------------


def _local_ledger() -> list:
    if LOCAL_CHAIN_FILE.exists():
        return json.loads(LOCAL_CHAIN_FILE.read_text(encoding="utf-8"))
    return []


def _save_local_ledger(blocks: list) -> None:
    LOCAL_CHAIN_FILE.write_text(
        json.dumps(blocks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _local_mine(content_hash: str) -> dict:
    """Append a new block to the local chain and persist it."""
    blocks = _local_ledger()
    previous_hash = blocks[-1]["block_hash"] if blocks else "0" * 64
    block_number = len(blocks) + 1
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    block_hash = hashlib.sha256(
        f"{previous_hash}|{content_hash}|{timestamp}|{block_number}".encode("utf-8")
    ).hexdigest()

    block = {
        "block_number": block_number,
        "block_hash": block_hash,
        "previous_hash": previous_hash,
        "content_hash": content_hash,
        "mined_at": timestamp,
    }

    blocks.append(block)
    _save_local_ledger(blocks)
    return block


def _local_verify(content_hash: str) -> bool:
    return any(block["content_hash"] == content_hash for block in _local_ledger())


def _anchor_local(content_hash: str) -> dict:
    if _local_verify(content_hash):
        return {
            "status": "already_anchored",
            "content_hash": content_hash,
            "network": LOCAL_CHAIN_NAME,
            "ledger_file": str(LOCAL_CHAIN_FILE),
        }

    block = _local_mine(content_hash)

    return {
        "status": "anchored",
        "content_hash": content_hash,
        "block_number": block["block_number"],
        "block_hash": block["block_hash"],
        "previous_hash": block["previous_hash"],
        "network": LOCAL_CHAIN_NAME,
        "ledger_file": str(LOCAL_CHAIN_FILE),
        "anchored_at": block["mined_at"],
    }


# ---------------------------------------------------------------------------
# Ethereum Sepolia (real testnet)
# ---------------------------------------------------------------------------


def _get_contract():
    if not SEPOLIA_RPC_URL:
        raise RuntimeError("SEPOLIA_RPC_URL is missing from .env")

    if not CONTRACT_ADDRESS:
        raise RuntimeError("CONTRACT_ADDRESS is missing from .env")

    w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))

    if not w3.is_connected():
        raise RuntimeError("Could not connect to the Sepolia RPC URL.")

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=ABI,
    )

    return w3, contract


def _anchor_sepolia(content_hash: str) -> dict:
    if not PRIVATE_KEY:
        raise RuntimeError("PRIVATE_KEY is missing from .env")

    w3, contract = _get_contract()
    account = Account.from_key(PRIVATE_KEY)

    content_hash_bytes = bytes.fromhex(content_hash)

    if contract.functions.verify(content_hash_bytes).call():
        return {
            "status": "already_anchored",
            "content_hash": content_hash,
            "contract_address": contract.address,
            "network": "Ethereum Sepolia",
        }

    transaction = contract.functions.anchor(content_hash_bytes).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address, "pending"),
            "chainId": 11155111,
            "gasPrice": w3.eth.gas_price,
        }
    )

    signed_transaction = account.sign_transaction(transaction)

    raw_transaction = getattr(
        signed_transaction,
        "raw_transaction",
        signed_transaction.rawTransaction,
    )

    tx_hash = w3.eth.send_raw_transaction(raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    if receipt.status != 1:
        raise RuntimeError("Blockchain transaction failed.")

    return {
        "status": "anchored",
        "content_hash": content_hash,
        "transaction_hash": tx_hash.hex(),
        "block_number": receipt.blockNumber,
        "contract_address": contract.address,
        "network": "Ethereum Sepolia",
        "anchored_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


# ---------------------------------------------------------------------------
# Public API used by main.py
# ---------------------------------------------------------------------------


def anchor_post(post_data: dict) -> dict:
    content_hash = create_content_hash(post_data)

    if chain_mode() == "sepolia":
        return _anchor_sepolia(content_hash)

    print("  (No Sepolia credentials in .env - using the local simulated chain.)")
    return _anchor_local(content_hash)


def verify_post(post_data: dict) -> dict:
    content_hash = create_content_hash(post_data)

    if chain_mode() == "sepolia":
        _, contract = _get_contract()
        verified = bool(
            contract.functions.verify(bytes.fromhex(content_hash)).call()
        )
        return {
            "verified": verified,
            "content_hash": content_hash,
            "contract_address": contract.address,
            "network": "Ethereum Sepolia",
        }

    return {
        "verified": _local_verify(content_hash),
        "content_hash": content_hash,
        "network": LOCAL_CHAIN_NAME,
        "ledger_file": str(LOCAL_CHAIN_FILE),
    }