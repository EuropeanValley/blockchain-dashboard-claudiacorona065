"""M6 - Security Score.

Optional module that estimates a lower-bound energy cost for a 51% attack
and visualises how confirmation depth reduces double-spend attack probability.
"""

import math

import pandas as pd
import plotly.express as px
import streamlit as st

from api.blockchain_client import (
    get_current_difficulty,
    get_recent_block_metadata,
)

TARGET_BLOCK_TIME_SECONDS = 600


def _format_hash_rate(hash_rate: float) -> str:
    """Format hash rate using Bitcoin mining units."""
    if hash_rate >= 1e18:
        return f"{hash_rate / 1e18:,.2f} EH/s"
    if hash_rate >= 1e15:
        return f"{hash_rate / 1e15:,.2f} PH/s"
    if hash_rate >= 1e12:
        return f"{hash_rate / 1e12:,.2f} TH/s"
    return f"{hash_rate:,.0f} H/s"


def _format_usd(value: float) -> str:
    """Format a monetary value in USD."""
    return f"${value:,.2f}"


def _calculate_intervals(blocks: list[dict]) -> list[int]:
    """Calculate block inter-arrival times from block metadata."""
    sorted_blocks = sorted(blocks, key=lambda block: int(block["height"]))
    intervals = []

    for previous_block, current_block in zip(sorted_blocks[:-1], sorted_blocks[1:]):
        interval = int(current_block["timestamp"]) - int(previous_block["timestamp"])

        if interval > 0:
            intervals.append(interval)

    return intervals


def _estimate_network_hash_rate(difficulty: float, average_block_time: float) -> float:
    """Estimate Bitcoin network hash rate in hashes per second.

    Formula:
    hash_rate ≈ difficulty * 2^32 / average_block_time
    """
    if average_block_time <= 0:
        raise ValueError("average_block_time must be positive.")

    return difficulty * 2**32 / average_block_time


def _attacker_hash_rate_for_share(network_hash_rate: float, attacker_share: float) -> float:
    """Estimate attacker hash rate needed for a target share after joining the network.

    If H is the honest network hash rate and A is the attacker hash rate:

        attacker_share = A / (H + A)

    Therefore:

        A = attacker_share / (1 - attacker_share) * H
    """
    if not 0 < attacker_share < 1:
        raise ValueError("attacker_share must be between 0 and 1.")

    return attacker_share / (1 - attacker_share) * network_hash_rate


def _energy_cost_per_hour(
    hash_rate_hs: float,
    efficiency_j_per_th: float,
    electricity_usd_per_kwh: float,
) -> tuple[float, float]:
    """Estimate power usage and electricity cost per hour.

    efficiency_j_per_th means joules required per tera-hash.
    Since J/s = W, converting H/s to TH/s gives estimated watts.
    """
    hash_rate_ths = hash_rate_hs / 1e12
    power_watts = hash_rate_ths * efficiency_j_per_th
    cost_per_hour = (power_watts / 1000) * electricity_usd_per_kwh

    return power_watts, cost_per_hour


def _nakamoto_attack_probability(confirmations: int, attacker_share: float) -> float:
    """Approximate double-spend success probability from Nakamoto's analysis.

    This implements the probability that an attacker with hash power q can catch
    up after z confirmations, using the Poisson approximation described in the
    Bitcoin whitepaper.
    """
    q = attacker_share
    p = 1 - q

    if q <= 0:
        return 0.0

    if q >= p:
        return 1.0

    z = confirmations
    lambda_value = z * (q / p)

    cumulative_probability = 0.0

    for k in range(z + 1):
        poisson_probability = (
            math.exp(-lambda_value) * lambda_value**k / math.factorial(k)
        )
        catch_up_probability = 1 - (q / p) ** (z - k)
        cumulative_probability += poisson_probability * catch_up_probability

    return max(0.0, min(1.0, 1 - cumulative_probability))


@st.cache_data(ttl=300, show_spinner=False)
def _load_security_data(n_blocks: int) -> tuple[list[dict], float]:
    """Load recent blocks and current difficulty for the security score."""
    blocks = get_recent_block_metadata(n_blocks)
    difficulty = get_current_difficulty()
    return blocks, difficulty


def render() -> None:
    """Render the M6 Security Score panel."""
    st.header("M6 - Security Score")

    st.write(
        "This optional module estimates a lower-bound energy cost for a 51% attack "
        "on Bitcoin and visualises how confirmation depth reduces double-spend "
        "attack probability."
    )

    st.warning(
        "This is an educational estimate, not a real attack budget. It only models "
        "electricity cost from live hash rate data and configurable assumptions. "
        "It excludes ASIC acquisition, availability, cooling, facilities, pool "
        "coordination, market impact and operational risk."
    )

    st.subheader("Assumptions")

    col1, col2, col3 = st.columns(3)

    with col1:
        n_blocks = st.slider(
            "Recent blocks for hash rate estimate",
            min_value=20,
            max_value=60,
            value=30,
            step=10,
            help="More blocks give a smoother estimate but require more API calls and may take longer to load.",
        )

    with col2:
        efficiency_j_per_th = st.number_input(
            "Mining efficiency (J/TH)",
            min_value=5.0,
            max_value=100.0,
            value=20.0,
            step=1.0,
            help="Lower values represent more efficient mining hardware.",
        )

    with col3:
        electricity_usd_per_kwh = st.number_input(
            "Electricity price (USD/kWh)",
            min_value=0.01,
            max_value=1.00,
            value=0.06,
            step=0.01,
            help="Energy price assumption used for the lower-bound cost estimate.",
        )

    attacker_share = st.slider(
        "Attacker share after joining the network",
        min_value=0.10,
        max_value=0.60,
        value=0.51,
        step=0.01,
        help=(
            "For a 51% attack, the attacker must contribute enough hash rate so "
            "their share of the combined attacker + honest network exceeds 50%."
        ),
    )

    if st.button("Refresh M6 data", key="m6_refresh"):
        _load_security_data.clear()

    with st.spinner("Loading live Bitcoin security data..."):
        try:
            blocks, difficulty = _load_security_data(n_blocks)
            intervals = _calculate_intervals(blocks)
        except Exception as exc:
            st.error(f"Error loading security data: {exc}")
            st.stop()

    if not intervals:
        st.warning("Not enough valid block interval data to estimate hash rate.")
        st.stop()

    average_block_time = sum(intervals) / len(intervals)
    network_hash_rate = _estimate_network_hash_rate(difficulty, average_block_time)

    attacker_hash_rate = _attacker_hash_rate_for_share(
        network_hash_rate,
        attacker_share,
    )

    network_power_watts, network_energy_cost_per_hour = _energy_cost_per_hour(
        network_hash_rate,
        efficiency_j_per_th,
        electricity_usd_per_kwh,
    )

    attacker_power_watts, attacker_energy_cost_per_hour = _energy_cost_per_hour(
        attacker_hash_rate,
        efficiency_j_per_th,
        electricity_usd_per_kwh,
    )

    st.subheader("Live security overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Estimated network hash rate", _format_hash_rate(network_hash_rate))

    with col2:
        st.metric("Attacker hash rate needed", _format_hash_rate(attacker_hash_rate))

    with col3:
        st.metric("Attacker power estimate", f"{attacker_power_watts / 1e9:,.2f} GW")

    with col4:
        st.metric("Energy cost per hour", _format_usd(attacker_energy_cost_per_hour))

    st.caption(
        f"Average observed block time used for hash rate estimate: "
        f"{average_block_time:.2f} seconds. Current difficulty: {difficulty:,.0f}."
    )

    st.subheader("Energy cost comparison")

    cost_df = pd.DataFrame(
        [
            {
                "Scenario": "Current Bitcoin network",
                "Hash rate": network_hash_rate,
                "Power GW": network_power_watts / 1e9,
                "Energy cost USD/hour": network_energy_cost_per_hour,
            },
            {
                "Scenario": f"Attacker at {attacker_share:.0%} share",
                "Hash rate": attacker_hash_rate,
                "Power GW": attacker_power_watts / 1e9,
                "Energy cost USD/hour": attacker_energy_cost_per_hour,
            },
        ]
    )

    cost_fig = px.bar(
        cost_df,
        x="Scenario",
        y="Energy cost USD/hour",
        hover_data={
            "Hash rate": ":.3e",
            "Power GW": ":.2f",
            "Energy cost USD/hour": ":,.2f",
        },
        title="Estimated lower-bound electricity cost per hour",
    )

    cost_fig.update_layout(
        xaxis_title="Scenario",
        yaxis_title="USD per hour",
    )

    st.plotly_chart(cost_fig, use_container_width=True)

    st.subheader("Confirmation depth and attack probability")

    max_confirmations = st.slider(
        "Maximum confirmations to display",
        min_value=3,
        max_value=30,
        value=12,
        step=1,
    )

    q_values = [0.10, 0.20, 0.30, 0.40, 0.49]
    probability_rows = []

    for q in q_values:
        for confirmations in range(1, max_confirmations + 1):
            probability_rows.append(
                {
                    "Confirmations": confirmations,
                    "Attacker share": f"{q:.0%}",
                    "Attack probability": _nakamoto_attack_probability(
                        confirmations,
                        q,
                    ),
                }
            )

    probability_df = pd.DataFrame(probability_rows)

    probability_fig = px.line(
        probability_df,
        x="Confirmations",
        y="Attack probability",
        color="Attacker share",
        markers=True,
        title="Double-spend catch-up probability by confirmation depth",
    )

    probability_fig.update_layout(
        xaxis_title="Confirmations",
        yaxis_title="Estimated attack success probability",
        yaxis_tickformat=".2%",
    )

    st.plotly_chart(probability_fig, use_container_width=True)

    st.info(
        "The chart shows why waiting for more confirmations increases security: "
        "when the attacker has less hash power than the honest network, the "
        "probability of catching up drops as confirmations increase."
    )

    st.subheader("Security interpretation")

    interpretation_df = pd.DataFrame(
        [
            {
                "Item": "51% attack condition",
                "Interpretation": (
                    "The attacker must control more hash power than the honest "
                    "network after joining the system."
                ),
            },
            {
                "Item": "Cost estimate",
                "Interpretation": (
                    "The displayed cost is an energy-only lower bound, not a full "
                    "economic attack cost."
                ),
            },
            {
                "Item": "Confirmations",
                "Interpretation": (
                    "More confirmations make double-spend attacks increasingly "
                    "unlikely when the attacker has less than 50% hash power."
                ),
            },
            {
                "Item": "Main limitation",
                "Interpretation": (
                    "The model ignores hardware supply, capital expenditure, cooling, "
                    "mining pool dynamics and real-world detection."
                ),
            },
        ]
    )

    st.dataframe(interpretation_df, use_container_width=True)