"""M3 - Difficulty History.

This module analyses Bitcoin difficulty adjustment periods and shows how the
network retargets mining difficulty to keep the average block time close to
10 minutes.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from api.blockchain_client import (
    bits_to_target,
    get_block_by_height,
    get_latest_block,
    target_to_difficulty,
)

DIFFICULTY_PERIOD_BLOCKS = 2016
TARGET_BLOCK_TIME_SECONDS = 600
TARGET_PERIOD_SECONDS = DIFFICULTY_PERIOD_BLOCKS * TARGET_BLOCK_TIME_SECONDS


def _format_seconds(seconds: float) -> str:
    """Format seconds as minutes and seconds."""
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes} min {remaining_seconds} s"


def _interpret_ratio(ratio: float) -> str:
    """Explain whether blocks were faster or slower than the Bitcoin target."""
    if ratio < 0.98:
        return "Faster than target; difficulty pressure upward"
    if ratio > 1.02:
        return "Slower than target; difficulty pressure downward"
    return "Close to target"


@st.cache_data(ttl=300, show_spinner=False)
def _load_adjustment_periods(n_periods: int) -> tuple[dict, pd.DataFrame]:
    """Load recent completed Bitcoin difficulty adjustment periods.

    Each Bitcoin difficulty period is 2016 blocks. This function uses boundary
    blocks to estimate the average block time for each completed period.
    """
    latest_summary = get_latest_block()
    current_height = int(latest_summary["height"])

    latest_completed_boundary = (
        current_height // DIFFICULTY_PERIOD_BLOCKS
    ) * DIFFICULTY_PERIOD_BLOCKS

    earliest_start_height = latest_completed_boundary - (
        n_periods * DIFFICULTY_PERIOD_BLOCKS
    )

    if earliest_start_height < 0:
        raise ValueError("Not enough blockchain history for the selected period count.")

    boundary_heights = list(
        range(
            earliest_start_height,
            latest_completed_boundary + 1,
            DIFFICULTY_PERIOD_BLOCKS,
        )
    )

    boundary_blocks = {
        height: get_block_by_height(height)
        for height in boundary_heights
    }

    rows = []

    for start_height, end_height in zip(boundary_heights[:-1], boundary_heights[1:]):
        start_block = boundary_blocks[start_height]
        end_block = boundary_blocks[end_height]

        bits = int(start_block["bits"])
        target = bits_to_target(bits)
        difficulty = target_to_difficulty(target)

        start_timestamp = int(start_block["timestamp"])
        end_timestamp = int(end_block["timestamp"])

        actual_period_seconds = end_timestamp - start_timestamp
        average_block_time = actual_period_seconds / DIFFICULTY_PERIOD_BLOCKS
        ratio = average_block_time / TARGET_BLOCK_TIME_SECONDS

        rows.append(
            {
                "Period": f"{start_height:,} - {end_height:,}",
                "Start height": start_height,
                "End height": end_height,
                "Adjustment date": pd.to_datetime(
                    start_timestamp,
                    unit="s",
                    utc=True,
                ),
                "End date": pd.to_datetime(
                    end_timestamp,
                    unit="s",
                    utc=True,
                ),
                "Bits": bits,
                "Target": f"0x{target:064x}",
                "Difficulty": difficulty,
                "Actual period days": actual_period_seconds / 86400,
                "Expected period days": TARGET_PERIOD_SECONDS / 86400,
                "Average block time seconds": average_block_time,
                "Actual / target ratio": ratio,
                "Interpretation": _interpret_ratio(ratio),
            }
        )

    df = pd.DataFrame(rows)
    df["Difficulty change %"] = df["Difficulty"].pct_change() * 100

    return latest_summary, df


def _build_display_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Build a readable table for the Streamlit dashboard."""
    display_df = df.copy()

    display_df["Adjustment date"] = display_df["Adjustment date"].dt.strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    display_df["End date"] = display_df["End date"].dt.strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    display_df["Difficulty"] = display_df["Difficulty"].map(lambda value: f"{value:,.0f}")
    display_df["Difficulty change %"] = display_df["Difficulty change %"].map(
        lambda value: "N/A" if pd.isna(value) else f"{value:.2f}%"
    )
    display_df["Actual period days"] = display_df["Actual period days"].map(
        lambda value: f"{value:.2f}"
    )
    display_df["Expected period days"] = display_df["Expected period days"].map(
        lambda value: f"{value:.2f}"
    )
    display_df["Average block time seconds"] = display_df[
        "Average block time seconds"
    ].map(lambda value: f"{value:.2f}")
    display_df["Actual / target ratio"] = display_df["Actual / target ratio"].map(
        lambda value: f"{value:.3f}"
    )

    return display_df[
        [
            "Period",
            "Adjustment date",
            "End date",
            "Bits",
            "Difficulty",
            "Difficulty change %",
            "Actual period days",
            "Expected period days",
            "Average block time seconds",
            "Actual / target ratio",
            "Interpretation",
        ]
    ]


def render() -> None:
    """Render the M3 Difficulty History panel."""
    st.header("M3 - Difficulty History")

    st.write(
        "This module analyses Bitcoin difficulty adjustment periods. Bitcoin "
        "retargets mining difficulty every 2016 blocks so that the long-term "
        "average block interval stays close to 600 seconds."
    )

    n_periods = st.slider(
        "Number of completed adjustment periods to analyse",
        min_value=3,
        max_value=10,
        value=6,
        step=1,
        help=(
            "Each period contains 2016 blocks. More periods require more API calls "
            "because the dashboard needs boundary blocks for the calculations."
        ),
    )

    if st.button("Refresh M3 data", key="m3_refresh"):
        _load_adjustment_periods.clear()

    with st.spinner("Fetching Bitcoin difficulty adjustment periods..."):
        try:
            latest_summary, df = _load_adjustment_periods(n_periods)
        except Exception as exc:
            st.error(f"Error loading difficulty history: {exc}")
            st.stop()

    if df.empty:
        st.warning("No difficulty period data was returned.")
        st.stop()

    latest_period = df.iloc[-1]

    st.subheader("Difficulty adjustment overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Current chain height", f"{int(latest_summary['height']):,}")

    with col2:
        st.metric("Periods analysed", str(len(df)))

    with col3:
        st.metric(
            "Latest avg block time",
            _format_seconds(float(latest_period["Average block time seconds"])),
        )

    with col4:
        st.metric(
            "Latest actual / target ratio",
            f"{float(latest_period['Actual / target ratio']):.3f}",
        )

    st.subheader("Difficulty evolution")

    difficulty_fig = px.line(
        df,
        x="Adjustment date",
        y="Difficulty",
        markers=True,
        title="Bitcoin difficulty at recent adjustment boundaries",
        hover_data={
            "Period": True,
            "Bits": True,
            "Difficulty change %": ":.2f",
            "Average block time seconds": ":.2f",
            "Actual / target ratio": ":.3f",
        },
    )

    difficulty_fig.update_layout(
        xaxis_title="Difficulty adjustment event date",
        yaxis_title="Difficulty",
    )

    st.plotly_chart(difficulty_fig, use_container_width=True)

    st.caption(
        "Each marker represents a difficulty adjustment boundary. The difficulty "
        "shown for each period is derived from the compact bits field."
    )

    st.subheader("Actual block time compared with the 600-second target")

    ratio_fig = px.bar(
        df,
        x="Period",
        y="Actual / target ratio",
        title="Average block time ratio per difficulty period",
        hover_data={
            "Average block time seconds": ":.2f",
            "Actual period days": ":.2f",
            "Expected period days": ":.2f",
            "Interpretation": True,
        },
    )

    ratio_fig.add_hline(
        y=1,
        line_dash="dash",
        annotation_text="Target ratio = 1",
        annotation_position="top right",
    )

    ratio_fig.update_layout(
        xaxis_title="Difficulty period",
        yaxis_title="Actual average block time / 600 seconds",
    )

    st.plotly_chart(ratio_fig, use_container_width=True)

    st.info(
        "A ratio below 1 means blocks were found faster than the 10-minute target. "
        "A ratio above 1 means blocks were found more slowly. Bitcoin uses this "
        "information at retarget boundaries to adjust mining difficulty."
    )

    st.subheader("Adjustment period data")

    st.dataframe(_build_display_dataframe(df), use_container_width=True)

    with st.expander("How Bitcoin difficulty retargeting works"):
        st.write(
            "Bitcoin groups blocks into difficulty periods of 2016 blocks. Since "
            "the target interval is 600 seconds, one ideal period should last "
            "2016 × 600 seconds, which is exactly two weeks."
        )

        st.write(
            "If the previous period was completed faster than two weeks, blocks "
            "were being mined too quickly and the protocol increases the difficulty. "
            "If it took longer than two weeks, the protocol decreases the difficulty."
        )

        st.write(
            "The difficulty value is derived from the Proof of Work target. A lower "
            "target means that fewer hashes are valid, so miners must perform more "
            "hash attempts on average to find a valid block."
        )