"""M4 - AI Component.

This module implements an anomaly detector for abnormal Bitcoin block
inter-arrival times using an exponential distribution baseline.
"""

import math

import pandas as pd
import plotly.express as px
import streamlit as st

from api.blockchain_client import get_recent_block_metadata

TARGET_BLOCK_TIME_SECONDS = 600


def _format_seconds(seconds: float) -> str:
    """Format seconds as minutes and seconds."""
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes} min {remaining_seconds} s"


def _format_probability(value: float) -> str:
    """Format a probability value in a readable way."""
    if value < 0.001:
        return f"{value:.2e}"
    return f"{value:.4f}"


def _fit_exponential_rate(intervals: pd.Series) -> float:
    """Fit an exponential distribution rate using maximum likelihood.

    For an exponential distribution, the maximum likelihood estimate is:
    lambda = 1 / sample_mean
    """
    mean_interval = float(intervals.mean())

    if mean_interval <= 0:
        raise ValueError("Mean interval must be greater than zero.")

    return 1 / mean_interval


def _calculate_thresholds(rate: float, alpha: float) -> tuple[float, float]:
    """Calculate lower and upper anomaly thresholds for a two-tail test.

    Very short intervals are anomalous if P(X <= x) < alpha / 2.
    Very long intervals are anomalous if P(X >= x) < alpha / 2.
    """
    lower_threshold = -math.log(1 - alpha / 2) / rate
    upper_threshold = -math.log(alpha / 2) / rate

    return lower_threshold, upper_threshold


def _build_interval_dataframe(blocks: list[dict]) -> pd.DataFrame:
    """Build a dataframe with inter-arrival times between consecutive blocks."""
    sorted_blocks = sorted(blocks, key=lambda block: int(block["height"]))

    rows = []

    for previous_block, current_block in zip(sorted_blocks[:-1], sorted_blocks[1:]):
        previous_timestamp = int(previous_block["timestamp"])
        current_timestamp = int(current_block["timestamp"])
        interval_seconds = current_timestamp - previous_timestamp

        rows.append(
            {
                "From height": int(previous_block["height"]),
                "To height": int(current_block["height"]),
                "Block hash": current_block["id"],
                "Timestamp UTC": pd.to_datetime(
                    current_timestamp,
                    unit="s",
                    utc=True,
                ),
                "Interval seconds": interval_seconds,
                "Interval minutes": interval_seconds / 60,
                "Transaction count": int(current_block.get("tx_count", 0)),
                "Difficulty": float(current_block.get("difficulty", 0)),
                "Nonce": int(current_block.get("nonce", 0)),
                "Bits": int(current_block.get("bits", 0)),
                "Valid timestamp": interval_seconds > 0,
            }
        )

    return pd.DataFrame(rows)


def _score_intervals(df: pd.DataFrame, rate: float, alpha: float) -> pd.DataFrame:
    """Score intervals using an exponential anomaly detector."""
    scored_df = df.copy()
    lower_threshold, upper_threshold = _calculate_thresholds(rate, alpha)

    tail_probabilities = []
    anomaly_scores = []
    anomaly_labels = []
    anomaly_reasons = []

    for _, row in scored_df.iterrows():
        interval = float(row["Interval seconds"])

        if interval <= 0:
            tail_probabilities.append(0.0)
            anomaly_scores.append(12.0)
            anomaly_labels.append(True)
            anomaly_reasons.append("Non-positive timestamp interval")
            continue

        lower_tail_probability = 1 - math.exp(-rate * interval)
        upper_tail_probability = math.exp(-rate * interval)

        tail_probability = min(lower_tail_probability, upper_tail_probability)
        anomaly_score = -math.log10(max(tail_probability, 1e-12))

        is_anomaly = tail_probability < alpha / 2

        if interval < lower_threshold:
            reason = "Very fast block"
        elif interval > upper_threshold:
            reason = "Very slow block"
        else:
            reason = "Normal interval"

        tail_probabilities.append(tail_probability)
        anomaly_scores.append(anomaly_score)
        anomaly_labels.append(is_anomaly)
        anomaly_reasons.append(reason)

    scored_df["Tail probability"] = tail_probabilities
    scored_df["Anomaly score"] = anomaly_scores
    scored_df["Anomaly"] = anomaly_labels
    scored_df["Reason"] = anomaly_reasons

    return scored_df


def _negative_log_likelihood(intervals: pd.Series, rate: float) -> float:
    """Calculate average negative log-likelihood for exponential data."""
    values = [float(value) for value in intervals if float(value) > 0]

    if not values:
        return float("nan")

    log_likelihoods = [math.log(rate) - rate * value for value in values]
    return -sum(log_likelihoods) / len(log_likelihoods)


@st.cache_data(ttl=300, show_spinner=False)
def _load_ai_blocks(n_blocks: int) -> list[dict]:
    """Load recent block metadata for the anomaly detector."""
    return get_recent_block_metadata(n_blocks)


def _build_anomaly_display_table(scored_df: pd.DataFrame) -> pd.DataFrame:
    """Create a readable table for detected anomalies."""
    anomalies = scored_df[scored_df["Anomaly"]].copy()

    if anomalies.empty:
        return anomalies

    anomalies["Timestamp UTC"] = anomalies["Timestamp UTC"].dt.strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
    anomalies["Interval seconds"] = anomalies["Interval seconds"].map(
        lambda value: f"{value:.0f}"
    )
    anomalies["Interval minutes"] = anomalies["Interval minutes"].map(
        lambda value: f"{value:.2f}"
    )
    anomalies["Tail probability"] = anomalies["Tail probability"].map(
        _format_probability
    )
    anomalies["Anomaly score"] = anomalies["Anomaly score"].map(
        lambda value: f"{value:.2f}"
    )

    return anomalies[
        [
            "From height",
            "To height",
            "Timestamp UTC",
            "Interval seconds",
            "Interval minutes",
            "Tail probability",
            "Anomaly score",
            "Reason",
            "Block hash",
        ]
    ]


def render() -> None:
    """Render the M4 AI Component panel."""
    st.header("M4 - AI Component")

    st.write(
        "This module implements an anomaly detector for Bitcoin block "
        "inter-arrival times. The model uses an exponential distribution as the "
        "baseline because Proof of Work mining can be interpreted as a random "
        "search process where block discoveries occur independently over time."
    )

    st.subheader("Model configuration")

    col1, col2 = st.columns(2)

    with col1:
        n_blocks = st.slider(
            "Number of recent blocks",
            min_value=30,
            max_value=120,
            value=60,
            step=10,
            help=(
                "The model uses recent block timestamps to calculate inter-arrival "
                "times. More blocks give more statistical context but require more "
                "API calls."
            ),
        )

    with col2:
        alpha = st.select_slider(
            "Anomaly sensitivity",
            options=[0.01, 0.02, 0.05, 0.10],
            value=0.05,
            format_func=lambda value: f"alpha = {value}",
            help=(
                "Lower alpha means stricter anomaly detection. With alpha = 0.05, "
                "roughly 5% of observations are expected to fall outside the normal "
                "range under the model."
            ),
        )

    if st.button("Refresh M4 data", key="m4_refresh"):
        _load_ai_blocks.clear()

    with st.spinner("Loading recent Bitcoin blocks for AI analysis..."):
        try:
            blocks = _load_ai_blocks(n_blocks)
            intervals_df = _build_interval_dataframe(blocks)
        except Exception as exc:
            st.error(f"Error loading AI data: {exc}")
            st.stop()

    if intervals_df.empty:
        st.warning("No interval data was returned.")
        st.stop()

    valid_intervals_df = intervals_df[intervals_df["Valid timestamp"]].reset_index(
        drop=True
    )

    if len(valid_intervals_df) < 10:
        st.warning(
            "Not enough valid timestamp intervals to train and evaluate the model."
        )
        st.stop()

    train_size = int(len(valid_intervals_df) * 0.7)
    train_size = max(5, min(train_size, len(valid_intervals_df) - 1))

    train_df = valid_intervals_df.iloc[:train_size]
    test_df = valid_intervals_df.iloc[train_size:]

    rate = _fit_exponential_rate(train_df["Interval seconds"])
    fitted_mean = 1 / rate

    lower_threshold, upper_threshold = _calculate_thresholds(rate, alpha)
    scored_df = _score_intervals(intervals_df, rate, alpha)

    valid_scored_df = scored_df[scored_df["Valid timestamp"]].reset_index(drop=True)
    test_scored_df = valid_scored_df.iloc[train_size:]
    timestamp_irregularities_df = scored_df[~scored_df["Valid timestamp"]]

    test_anomaly_count = int(test_scored_df["Anomaly"].sum())
    test_anomaly_rate = test_anomaly_count / len(test_scored_df)

    average_nll = _negative_log_likelihood(
        test_scored_df["Interval seconds"],
        rate,
    )

    st.subheader("AI model overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Blocks analysed", f"{len(blocks):,}")

    with col2:
        st.metric("Training mean interval", _format_seconds(fitted_mean))

    with col3:
        st.metric("Test anomaly rate", f"{test_anomaly_rate * 100:.2f}%")

    with col4:
        st.metric("Avg. test NLL", f"{average_nll:.2f}")

    st.write("**Detected normal range under the exponential model**")

    range_col1, range_col2, range_col3 = st.columns(3)

    with range_col1:
        st.metric("Very fast threshold", _format_seconds(lower_threshold))

    with range_col2:
        st.metric("Expected Bitcoin target", _format_seconds(TARGET_BLOCK_TIME_SECONDS))

    with range_col3:
        st.metric("Very slow threshold", _format_seconds(upper_threshold))

    st.info(
        "The model is trained on the oldest 70% of the selected recent intervals "
        "and evaluated on the newest 30%. This keeps the evaluation separate from "
        "the data used to fit the exponential baseline."
    )
    if not timestamp_irregularities_df.empty:
        st.warning(
        "Some block timestamp intervals are non-positive. These cases are shown "
        "as timestamp irregularities, but they are excluded from the exponential "
        "model evaluation because miner-provided timestamps are not guaranteed to "
        "be strictly increasing."
    )


    st.subheader("Block interval anomaly chart")

    chart_df = scored_df.copy()
    chart_df["Anomaly label"] = chart_df["Anomaly"].map(
        {True: "Anomaly", False: "Normal"}
    )

    interval_fig = px.scatter(
        chart_df,
        x="To height",
        y="Interval seconds",
        color="Anomaly label",
        hover_data={
            "From height": True,
            "To height": True,
            "Interval minutes": ":.2f",
            "Tail probability": ":.4f",
            "Anomaly score": ":.2f",
            "Reason": True,
            "Block hash": True,
        },
        title="Detected anomalies in Bitcoin block inter-arrival times",
    )

    interval_fig.add_hline(
        y=TARGET_BLOCK_TIME_SECONDS,
        line_dash="dash",
        annotation_text="Bitcoin target: 600 seconds",
        annotation_position="top right",
    )

    interval_fig.add_hline(
        y=lower_threshold,
        line_dash="dot",
        annotation_text="Fast anomaly threshold",
        annotation_position="bottom right",
    )

    interval_fig.add_hline(
        y=upper_threshold,
        line_dash="dot",
        annotation_text="Slow anomaly threshold",
        annotation_position="top right",
    )

    interval_fig.update_layout(
        xaxis_title="Block height",
        yaxis_title="Seconds since previous block",
    )

    st.plotly_chart(interval_fig, use_container_width=True)

    st.subheader("Interval distribution")

    histogram_fig = px.histogram(
        valid_scored_df,
        x="Interval seconds",
        nbins=20,
        title="Observed block interval distribution",
    )

    histogram_fig.add_vline(
        x=TARGET_BLOCK_TIME_SECONDS,
        line_dash="dash",
        annotation_text="600-second Bitcoin target",
        annotation_position="top right",
    )

    histogram_fig.add_vline(
        x=lower_threshold,
        line_dash="dot",
        annotation_text="Fast threshold",
        annotation_position="top left",
    )

    histogram_fig.add_vline(
        x=upper_threshold,
        line_dash="dot",
        annotation_text="Slow threshold",
        annotation_position="top right",
    )

    histogram_fig.update_layout(
        xaxis_title="Seconds between blocks",
        yaxis_title="Number of intervals",
    )

    st.plotly_chart(histogram_fig, use_container_width=True)

    st.subheader("Detected anomalies")

    anomaly_table = _build_anomaly_display_table(scored_df)

    if anomaly_table.empty:
        st.success("No anomalous block intervals detected with the current threshold.")
    else:
        st.dataframe(anomaly_table, use_container_width=True)

    st.subheader("Model evaluation")

    evaluation_df = pd.DataFrame(
        [
            {
                "Metric": "Training intervals",
                "Value": len(train_df),
                "Meaning": "Intervals used to fit the exponential baseline.",
            },
            {
                "Metric": "Test intervals",
                "Value": len(test_df),
                "Meaning": "Intervals used to evaluate the detector.",
            },
            {
                "Metric": "Expected anomaly rate",
                "Value": f"{alpha * 100:.2f}%",
                "Meaning": "Configured probability mass outside the normal region.",
            },
            {
                "Metric": "Observed test anomaly rate",
                "Value": f"{test_anomaly_rate * 100:.2f}%",
                "Meaning": "Fraction of test intervals flagged as anomalous.",
            },
            {
                "Metric": "Average test negative log-likelihood",
                "Value": f"{average_nll:.2f}",
                "Meaning": "Lower values indicate that the exponential model fits the test data better.",
            },
        ]
    )

    st.dataframe(evaluation_df, use_container_width=True)

    with st.expander("Why this is a suitable AI approach"):
        st.write(
            "This module implements an unsupervised anomaly detector. It does not "
            "need labelled examples of attacks or abnormal mining behaviour. Instead, "
            "it learns a statistical baseline from recent real Bitcoin block times "
            "and identifies intervals that are unlikely under that model."
        )

        st.write(
            "The exponential distribution is appropriate as a first baseline because "
            "Bitcoin mining is based on repeated independent hash attempts. If the "
            "global network hash rate is approximately stable, the waiting time "
            "between successful blocks can be modelled as exponentially distributed."
        )

    with st.expander("Limitations"):
        st.write(
            "This detector identifies statistically unusual intervals, not proven "
            "attacks. A very fast or very slow block can happen naturally due to the "
            "randomness of Proof of Work."
        )

        st.write(
            "The model also uses block timestamps, which are provided by miners and "
            "are not a perfect wall-clock measurement. For this reason, the output "
            "should be interpreted as analytical evidence rather than a definitive "
            "security conclusion."
        )