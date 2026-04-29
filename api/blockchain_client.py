"""
Blockchain API client.

Provides helper functions to fetch blockchain data from public APIs.
"""

import requests

BASE_URL = "https://blockchain.info"
BLOCKSTREAM_API_URL = "https://blockstream.info/api"

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
def get_recent_blocks(n_blocks: int = 10) -> list[dict]:
    """Return the latest n_blocks with full block details.

    The function starts from the latest block and follows the prev_block
    field backwards through the blockchain.
    """
    if n_blocks < 2:
        raise ValueError("n_blocks must be at least 2 to calculate block intervals.")

    latest_summary = get_latest_block()
    current_block = get_block(latest_summary["hash"])

    blocks = [current_block]

    while len(blocks) < n_blocks:
        previous_hash = current_block.get("prev_block")

        if not previous_hash:
            break

        current_block = get_block(previous_hash)
        blocks.append(current_block)

    return blocks


def bits_to_target(bits: int) -> int:
    """Convert the compact Bitcoin bits field into a full target integer.

    In Bitcoin, the bits field stores the Proof of Work target in compact form.
    A valid block hash must be numerically lower than this target.
    """
    exponent = bits >> 24
    coefficient = bits & 0xFFFFFF

    return coefficient * 2 ** (8 * (exponent - 3))


def target_to_leading_zero_bits(target: int) -> int:
    """Estimate the minimum number of leading zero bits implied by a target."""
    if target <= 0:
        return 256

    return max(0, 256 - target.bit_length())


def count_leading_zero_bits(block_hash: str) -> int:
    """Count the number of leading zero bits in a 256-bit block hash."""
    binary_hash = bin(int(block_hash, 16))[2:].zfill(256)
    return len(binary_hash) - len(binary_hash.lstrip("0"))


def calculate_block_intervals(blocks: list[dict]) -> list[int]:
    """Calculate time differences in seconds between consecutive blocks.

    The blocks are expected in descending order: latest block first.
    """
    intervals = []

    for index in range(len(blocks) - 1):
        current_time = blocks[index]["time"]
        previous_time = blocks[index + 1]["time"]
        intervals.append(current_time - previous_time)

    return intervals


def estimate_hash_rate(difficulty: float, average_block_time: float) -> float:
    """Estimate network hash rate in hashes per second.

    The estimate uses the Bitcoin relation:
    hash_rate ≈ difficulty * 2^32 / average_block_time
    """
    if average_block_time <= 0:
        raise ValueError("average_block_time must be greater than zero.")

    return difficulty * 2**32 / average_block_time
def target_to_difficulty(target: int) -> float:
    """Convert a Proof of Work target into Bitcoin difficulty.

    Bitcoin difficulty is defined relative to the maximum target used at
    difficulty 1, encoded by the compact bits value 0x1d00ffff.
    """
    if target <= 0:
        raise ValueError("target must be greater than zero.")

    max_target = bits_to_target(0x1D00FFFF)
    return max_target / target


def get_block_hash_by_height(height: int) -> str:
    """Return the block hash for a given Bitcoin block height."""
    response = requests.get(
        f"{BLOCKSTREAM_API_URL}/block-height/{height}",
        timeout=10,
    )
    response.raise_for_status()
    return response.text.strip()


def get_blockstream_block(block_hash: str) -> dict:
    """Return block metadata from the Blockstream API."""
    response = requests.get(
        f"{BLOCKSTREAM_API_URL}/block/{block_hash}",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_block_by_height(height: int) -> dict:
    """Return block metadata for a given Bitcoin block height."""
    block_hash = get_block_hash_by_height(height)
    return get_blockstream_block(block_hash)

def get_recent_block_metadata(n_blocks: int = 50) -> list[dict]:
    """Return metadata for the latest n_blocks using the Blockstream API.

    This function is lighter than get_recent_blocks because it does not download
    the full transaction list for every block. It is useful for statistical
    analysis of timestamps, block heights, nonce, bits and transaction counts.
    """
    if n_blocks < 2:
        raise ValueError("n_blocks must be at least 2.")

    latest_summary = get_latest_block()
    latest_height = int(latest_summary["height"])

    blocks = []

    for height in range(latest_height, latest_height - n_blocks, -1):
        blocks.append(get_block_by_height(height))

    return blocks

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