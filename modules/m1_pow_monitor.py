"""M1 - Proof of Work Monitor.

This module displays live Bitcoin mining data and connects it with the
cryptographic theory behind Proof of Work.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from api.blockchain_client import (
    bits_to_target,
    calculate_block_intervals,
    count_leading_zero_bits,
    estimate_hash_rate,
    get_current_difficulty,
    get_recent_blocks,
    target_to_leading_zero_bits,
)

TARGET_BLOCK_TIME_SECONDS = 600


def _format_hash_rate(hash_rate: float) -> str:
    """Format hash rate using common Bitcoin network units."""
    if hash_rate >= 1e18:
        return f"{hash_rate / 1e18:,.2f} EH/s"
    if hash_rate >= 1e15:
        return f"{hash_rate / 1e15:,.2f} PH/s"
    if hash_rate >= 1e12:
        return f"{hash_rate / 1e12:,.2f} TH/s"
    return f"{hash_rate:,.0f} H/s"


def _format_seconds(seconds: float) -> str:
    """Format seconds as minutes and seconds."""
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes} min {remaining_seconds} s"


@st.cache_data(ttl=60, show_spinner=False)
def _load_pow_data(n_blocks: int) -> tuple[list[dict], float]:
    """Load recent block data and current difficulty.

    The cache avoids calling the public API too many times while still keeping
    the dashboard close to real time.
    """
    blocks = get_recent_blocks(n_blocks)
    difficulty = get_current_difficulty()
    return blocks, difficulty


def _build_blocks_dataframe(blocks: list[dict]) -> pd.DataFrame:
    """Create a clean table with the most relevant fields from recent blocks."""
    rows = []

    for block in blocks:
        rows.append(
            {
                "Height": block.get("height"),
                "Time UTC": pd.to_datetime(block.get("time"), unit="s", utc=True),
                "Hash": block.get("hash"),
                "Nonce": block.get("nonce"),
                "Bits": block.get("bits"),
                "Transactions": len(block.get("tx", [])),
            }
        )

    return pd.DataFrame(rows)


def _build_intervals_dataframe(blocks: list[dict], intervals: list[int]) -> pd.DataFrame:
    """Create a table with time intervals between consecutive blocks."""
    rows = []

    for index, interval in enumerate(intervals):
        rows.append(
            {
                "From height": blocks[index + 1].get("height"),
                "To height": blocks[index].get("height"),
                "Interval seconds": interval,
                "Interval minutes": interval / 60,
            }
        )

    return pd.DataFrame(rows)


def render() -> None:
    """Render the M1 Proof of Work Monitor panel."""
    st.header("M1 - Proof of Work Monitor")

    st.write(
        "This module monitors live Bitcoin mining data and connects it with "
        "the Proof of Work concepts studied in cryptography: difficulty, target, "
        "leading zeros, nonce and block time."
    )

    n_blocks = st.slider(
        "Number of recent blocks to analyse",
        min_value=5,
        max_value=20,
        value=10,
        step=1,
        help="More blocks provide more context, but require more API calls.",
    )

    if st.button("Refresh M1 data", key="m1_refresh"):
        _load_pow_data.clear()

    with st.spinner("Fetching recent Bitcoin blocks..."):
        try:
            blocks, difficulty = _load_pow_data(n_blocks)
        except Exception as exc:
            st.error(f"Error fetching Proof of Work data: {exc}")
            st.stop()

    if len(blocks) < 2:
        st.warning("Not enough block data was returned to calculate intervals.")
        st.stop()

    latest_block = blocks[0]
    block_hash = latest_block["hash"]
    bits = int(latest_block["bits"])

    target = bits_to_target(bits)
    expected_zero_bits = target_to_leading_zero_bits(target)
    observed_zero_bits = count_leading_zero_bits(block_hash)

    intervals = calculate_block_intervals(blocks)
    average_block_time = sum(intervals) / len(intervals)
    estimated_hash_rate = estimate_hash_rate(difficulty, average_block_time)

    st.subheader("Live mining overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Latest block height", f"{latest_block['height']:,}")

    with col2:
        st.metric("Current difficulty", f"{difficulty:,.0f}")

    with col3:
        st.metric("Average block time", _format_seconds(average_block_time))

    with col4:
        st.metric("Estimated hash rate", _format_hash_rate(estimated_hash_rate))

    st.subheader("Latest block Proof of Work data")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Nonce", f"{latest_block['nonce']:,}")

    with col2:
        st.metric("Transactions", f"{len(latest_block.get('tx', [])):,}")

    with col3:
        st.metric("Bits", str(bits))

    st.write("**Latest block hash**")
    st.code(block_hash, language="text")

    st.write("**Target threshold derived from bits**")
    st.code(f"0x{target:064x}", language="text")

    st.write("**Leading zero bits in the latest block hash**")
    st.progress(observed_zero_bits / 256)
    st.caption(
        f"Observed leading zero bits: {observed_zero_bits}/256. "
        f"Approximate minimum implied by target: {expected_zero_bits}/256."
    )

    st.info(
        "In Bitcoin Proof of Work, miners repeatedly change values such as the "
        "nonce until the double SHA-256 hash of the block header is numerically "
        "lower than the target. The target is encoded compactly in the bits field. "
        "A smaller target means higher difficulty."
    )

    st.subheader("Time between recent blocks")

    intervals_df = _build_intervals_dataframe(blocks, intervals)

    fig = px.histogram(
        intervals_df,
        x="Interval seconds",
        nbins=min(10, len(intervals)),
        title="Distribution of time between recent Bitcoin blocks",
    )

    fig.add_vline(
        x=TARGET_BLOCK_TIME_SECONDS,
        line_dash="dash",
        annotation_text="Bitcoin target: 600 seconds",
        annotation_position="top right",
    )

    fig.update_layout(
        xaxis_title="Seconds between blocks",
        yaxis_title="Number of intervals",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Bitcoin block discovery is commonly modelled as a random process. "
        "If mining attempts are independent and the network hash rate is stable, "
        "the time between blocks is expected to follow an exponential distribution "
        "with an average close to 600 seconds."
    )

    st.subheader("Recent block data")

    blocks_df = _build_blocks_dataframe(blocks)
    st.dataframe(blocks_df, use_container_width=True)