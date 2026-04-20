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


def get_current_difficulty() -> float:
    """Return the current Bitcoin network difficulty."""
    response = requests.get(f"{BASE_URL}/q/getdifficulty", timeout=10)
    response.raise_for_status()
    return float(response.text)


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
    # First, request the latest block summary from the API.
    latest = get_latest_block()

    # Then, use the latest block hash to request the full block data.
    block = get_block(latest["hash"])

    # The block hash starts with many leading zeros.
    # This is a visible effect of Bitcoin Proof of Work:
    # miners must find a hash that is lower than the target threshold.

    # The bits field is the compact representation of that target.
    # In general, a smaller target means higher difficulty,
    # so mining a valid block becomes harder.

    # The nonce is one of the values miners change repeatedly
    # while searching for a valid block hash.

    print("Block height:", block["height"])
    print("Hash:", block["hash"])
    print("Difficulty:", get_current_difficulty())
    print("Nonce:", block["nonce"])
    print("Number of transactions:", len(block["tx"]))
    print("Bits:", block["bits"])