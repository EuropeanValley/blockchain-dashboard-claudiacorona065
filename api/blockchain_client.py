"""
Blockchain API client.

Provides helper functions to fetch blockchain data from public APIs.
"""

import requests

BASE_URL = "https://blockchain.info"


def get_latest_block() -> dict:
    """Return the latest block summary."""
    response = requests.get(f"{BASE_URL}/latestblock", timeout=10)
    response.raise_for_status()
    return response.json()


def get_block(block_hash: str) -> dict:
    """Return full details for a block identified by *block_hash*."""
    response = requests.get(
        f"{BASE_URL}/rawblock/{block_hash}", timeout=10
    )
    response.raise_for_status()
    return response.json()


def get_difficulty_history(n_points: int = 100) -> list[dict]:
    """Return the last *n_points* difficulty values as a list of dicts."""
    response = requests.get(
        f"{BASE_URL}/charts/difficulty",
        params={"timespan": "1year", "format": "json", "sampled": "true"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("values", [])[-n_points:]


if __name__ == "__main__":
    latest = get_latest_block()
    block = get_block(latest["hash"])

    # The block hash usually starts with leading zeros, which reflects the Proof of Work condition.
    # The bits field encodes the mining target threshold: a smaller target means higher difficulty.
    print("Block height:", block["height"])
    print("Hash:", block["hash"])
    print("Difficulty:", block["difficulty"])
    print("Nonce:", block["nonce"])
    print("Number of transactions:", len(block["tx"]))
    print("Bits:", block["bits"])
