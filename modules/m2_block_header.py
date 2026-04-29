"""M2 - Block Header Analyzer.

This module reconstructs the 80-byte Bitcoin block header and verifies
Proof of Work locally using double SHA-256.
"""

import hashlib
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from api.blockchain_client import (
    bits_to_target,
    count_leading_zero_bits,
    get_block,
    get_latest_block,
)


def _uint32_to_little_endian_bytes(value: int) -> bytes:
    """Convert a 32-bit unsigned integer to 4 little-endian bytes."""
    return (int(value) & 0xFFFFFFFF).to_bytes(4, byteorder="little")


def _reverse_hex_bytes(hex_value: str) -> bytes:
    """Reverse a hexadecimal string byte by byte.

    Bitcoin block explorers display hashes in big-endian human-readable form,
    but the block header stores previous block hash and Merkle root in little-endian.
    """
    return bytes.fromhex(hex_value)[::-1]


def _format_timestamp(timestamp: int) -> str:
    """Format a Unix timestamp as a readable UTC date."""
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def build_block_header(block: dict) -> bytes:
    """Reconstruct the serialized 80-byte Bitcoin block header.

    Header structure:
    - version: 4 bytes, little-endian
    - previous block hash: 32 bytes, internal byte order
    - Merkle root: 32 bytes, internal byte order
    - timestamp: 4 bytes, little-endian
    - bits: 4 bytes, little-endian
    - nonce: 4 bytes, little-endian
    """
    version = _uint32_to_little_endian_bytes(block["ver"])
    previous_block = _reverse_hex_bytes(block["prev_block"])
    merkle_root = _reverse_hex_bytes(block["mrkl_root"])
    timestamp = _uint32_to_little_endian_bytes(block["time"])
    bits = _uint32_to_little_endian_bytes(block["bits"])
    nonce = _uint32_to_little_endian_bytes(block["nonce"])

    return version + previous_block + merkle_root + timestamp + bits + nonce


def double_sha256(data: bytes) -> bytes:
    """Return SHA256(SHA256(data))."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def calculate_block_hash_from_header(header: bytes) -> str:
    """Calculate the human-readable Bitcoin block hash from a serialized header.

    The raw SHA-256 digest is reversed for the standard block explorer display.
    """
    return double_sha256(header)[::-1].hex()


def _build_header_fields_dataframe(block: dict) -> pd.DataFrame:
    """Create a table showing the six fields of the Bitcoin block header."""
    return pd.DataFrame(
        [
            {
                "Field": "Version",
                "Size": "4 bytes",
                "Human-readable value": block["ver"],
                "Serialized header value": _uint32_to_little_endian_bytes(
                    block["ver"]
                ).hex(),
            },
            {
                "Field": "Previous block hash",
                "Size": "32 bytes",
                "Human-readable value": block["prev_block"],
                "Serialized header value": _reverse_hex_bytes(
                    block["prev_block"]
                ).hex(),
            },
            {
                "Field": "Merkle root",
                "Size": "32 bytes",
                "Human-readable value": block["mrkl_root"],
                "Serialized header value": _reverse_hex_bytes(
                    block["mrkl_root"]
                ).hex(),
            },
            {
                "Field": "Timestamp",
                "Size": "4 bytes",
                "Human-readable value": f"{block['time']} ({_format_timestamp(block['time'])})",
                "Serialized header value": _uint32_to_little_endian_bytes(
                    block["time"]
                ).hex(),
            },
            {
                "Field": "Bits",
                "Size": "4 bytes",
                "Human-readable value": block["bits"],
                "Serialized header value": _uint32_to_little_endian_bytes(
                    block["bits"]
                ).hex(),
            },
            {
                "Field": "Nonce",
                "Size": "4 bytes",
                "Human-readable value": block["nonce"],
                "Serialized header value": _uint32_to_little_endian_bytes(
                    block["nonce"]
                ).hex(),
            },
        ]
    )


@st.cache_data(ttl=60, show_spinner=False)
def _load_latest_block_details() -> dict:
    """Load full details for the latest Bitcoin block."""
    latest = get_latest_block()
    return get_block(latest["hash"])


@st.cache_data(ttl=60, show_spinner=False)
def _load_block_details(block_hash: str) -> dict:
    """Load full details for a specific block hash."""
    return get_block(block_hash)


def render() -> None:
    """Render the M2 Block Header Analyzer panel."""
    st.header("M2 - Block Header Analyzer")

    st.write(
        "This module reconstructs the 80-byte Bitcoin block header and verifies "
        "the Proof of Work locally using Python's hashlib implementation of "
        "double SHA-256."
    )

    mode = st.radio(
        "Choose block source",
        ["Latest Bitcoin block", "Custom block hash"],
        horizontal=True,
        key="m2_mode",
    )

    block = None

    if mode == "Latest Bitcoin block":
        if st.button("Refresh latest block", key="m2_refresh_latest"):
            _load_latest_block_details.clear()

        with st.spinner("Fetching latest block details..."):
            try:
                block = _load_latest_block_details()
            except Exception as exc:
                st.error(f"Error fetching latest block: {exc}")
                st.stop()

    else:
        block_hash = st.text_input(
            "Block hash",
            placeholder="Enter a Bitcoin block hash",
            key="m2_custom_hash",
        )

        if not block_hash:
            st.info("Enter a block hash to analyse a specific block.")
            st.stop()

        if st.button("Analyze custom block", key="m2_analyze_custom"):
            with st.spinner("Fetching block details..."):
                try:
                    block = _load_block_details(block_hash.strip())
                except Exception as exc:
                    st.error(f"Error fetching block: {exc}")
                    st.stop()
        else:
            st.info("Click Analyze custom block to run the verification.")
            st.stop()

    header = build_block_header(block)
    header_hex = header.hex()

    calculated_hash = calculate_block_hash_from_header(header)
    api_hash = block["hash"].lower()
    hash_matches_api = calculated_hash == api_hash

    bits = int(block["bits"])
    target = bits_to_target(bits)
    target_hex = f"{target:064x}"

    calculated_hash_as_integer = int(calculated_hash, 16)
    proof_of_work_valid = calculated_hash_as_integer <= target

    leading_zero_bits = count_leading_zero_bits(calculated_hash)

    st.subheader("Block overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Block height", f"{block['height']:,}")

    with col2:
        st.metric("Version", str(block["ver"]))

    with col3:
        st.metric("Nonce", f"{block['nonce']:,}")

    with col4:
        st.metric("Bits", str(bits))

    st.write("**API block hash**")
    st.code(api_hash, language="text")

    st.write("**Calculated block hash from reconstructed header**")
    st.code(calculated_hash, language="text")

    st.subheader("80-byte block header structure")

    st.dataframe(_build_header_fields_dataframe(block), use_container_width=True)

    st.write("**Serialized 80-byte header in hexadecimal**")
    st.code(header_hex, language="text")
    st.caption(
        f"Header length: {len(header)} bytes = {len(header_hex)} hexadecimal characters."
    )

    st.subheader("Local Proof of Work verification")

    verification_df = pd.DataFrame(
        [
            {
                "Check": "Header length is 80 bytes",
                "Value": f"{len(header)} bytes",
                "Status": "PASS" if len(header) == 80 else "FAIL",
            },
            {
                "Check": "Double SHA-256 hash matches API hash",
                "Value": str(hash_matches_api),
                "Status": "PASS" if hash_matches_api else "FAIL",
            },
            {
                "Check": "Calculated hash is below or equal to target",
                "Value": str(proof_of_work_valid),
                "Status": "PASS" if proof_of_work_valid else "FAIL",
            },
            {
                "Check": "Leading zero bits in calculated hash",
                "Value": leading_zero_bits,
                "Status": "INFO",
            },
        ]
    )

    st.dataframe(verification_df, use_container_width=True)

    if hash_matches_api and proof_of_work_valid:
        st.success("Proof of Work verified locally.")
    else:
        st.error("Proof of Work verification failed. Check byte order and header fields.")

    st.write("**Target threshold derived from bits**")
    st.code(f"0x{target_hex}", language="text")

    st.write("**Calculated hash as integer**")
    st.code(str(calculated_hash_as_integer), language="text")

    st.write("**Target as integer**")
    st.code(str(target), language="text")

    st.write("**Leading zero bits**")
    st.progress(leading_zero_bits / 256)
    st.caption(f"The calculated block hash has {leading_zero_bits} leading zero bits.")

    with st.expander("Why byte order matters"):
        st.write(
            "Bitcoin block explorers usually display hashes in a human-readable "
            "big-endian hexadecimal format. However, inside the serialized block "
            "header, the previous block hash and the Merkle root are stored in "
            "internal byte order, so their bytes must be reversed before hashing."
        )

        st.write(
            "The final SHA256(SHA256(header)) digest is also reversed when shown "
            "as the standard Bitcoin block hash. If this reversal is not handled "
            "correctly, the calculated hash will not match the API hash."
        )

    with st.expander("Cryptographic interpretation"):
        st.write(
            "The bits field is a compact encoding of the Proof of Work target. "
            "A valid Bitcoin block must produce a double SHA-256 hash whose numeric "
            "value is less than or equal to that target."
        )

        st.write(
            "The smaller the target, the harder it is to find a valid hash. "
            "This is why high-difficulty Bitcoin blocks usually have hashes with "
            "many leading zero bits."
        )