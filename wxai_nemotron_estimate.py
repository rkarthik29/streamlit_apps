import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="wx.ai Deployment Cost Estimator",
    page_icon="🧮",
    layout="wide"
)

st.title("IBM watsonx.ai — On-Demand Deployment Cost Estimator")
st.caption("Estimate GPU hosting costs for any on-demand model · Based on IBM list pricing")

st.divider()

# ── Sidebar: inputs ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Configuration")

    st.subheader("Deployment")
    gpu_options = {
        "4×A100 — $23.2/hr": 23.2,
        "8×A100 — $46.4/hr": 46.4,
        "4×H100 — $58.0/hr": 58.0,
        "8×H100 — $116.0/hr": 116.0,
        "4×H200 — $64.0/hr": 64.0,
        "8×H200 — $128.0/hr": 128.0,
        "1×L40S — $4.43/hr": 4.43,
        "2×L40S — $8.86/hr": 8.86,
        "1×A100 — $5.8/hr": 5.8,
        "2×A100 — $11.6/hr": 11.6,
        "1×H100 — $14.5/hr": 14.5,
        "2×H100 — $29.0/hr": 29.0,
        "1×H200 — $16.0/hr": 16.0,
        "2×H200 — $32.0/hr": 32.0,
    }
    gpu_label = st.selectbox("GPU configuration", list(gpu_options.keys()))
    gpu_rate = gpu_options[gpu_label]

    num_deployments = st.selectbox(
        "Number of instances",
        [1, 2, 4, 8],
        help="Run multiple instances for high availability or throughput."
    )

    hours_per_day = st.slider("Hours active per day", 1, 24, 10)
    days_per_month = st.slider("Days per month", 1, 31, 22)

    st.subheader("Token throughput")
    prompt_tokens = st.slider("Avg prompt tokens / query", 100, 8000, 1000, step=100)
    output_tokens = st.slider("Avg output tokens / query", 100, 4000, 500, step=100)
    queries_per_hour = st.slider("Estimated queries / hour", 1, 5000, 100, step=10)

    st.subheader("Platform plan")
    plan = st.radio(
        "Pricing plan",
        ["Essentials ($0/mo base)", "Standard ($1,050/mo)"],
        index=1,
        help="On-demand model hosting requires the Standard plan."
    )
    platform_base = 1050 if "Standard" in plan else 0

# ── Calculations ─────────────────────────────────────────────────────────────
gpu_cost = gpu_rate * hours_per_day * days_per_month * num_deployments
monthly_total = gpu_cost + platform_base
annual_total = monthly_total * 12

total_tokens_per_query = prompt_tokens + output_tokens
total_toks_per_sec = (queries_per_hour * total_tokens_per_query) / 3600
gpu_count_map = {4.43: 1, 8.86: 2, 5.8: 1, 11.6: 2, 23.2: 4, 46.4: 8,
                 14.5: 1, 29.0: 2, 58.0: 4, 116.0: 8,
                 16.0: 1, 32.0: 2, 64.0: 4, 128.0: 8}
gpu_count = gpu_count_map.get(gpu_rate, 4)
tok_per_sec_capacity = gpu_count * 12 * num_deployments
utilisation_pct = min(100, round((total_toks_per_sec / tok_per_sec_capacity) * 100, 1))

total_tokens_M_month = (queries_per_hour * hours_per_day * days_per_month * total_tokens_per_query) / 1_000_000

# ── Summary metrics ───────────────────────────────────────────────────────────
st.subheader("Cost summary")

c1, c2, c3 = st.columns(3)
c1.metric("Monthly cost", f"${monthly_total:,.0f}")
c2.metric("Annual cost", f"${annual_total:,.0f}")
c3.metric("Est. GPU utilisation", f"{utilisation_pct}%")

st.divider()

# ── Cost breakdown ────────────────────────────────────────────────────────────
st.subheader("Cost breakdown")

col_left, col_right = st.columns([1, 1])

with col_left:
    breakdown = pd.DataFrame({
        "Component": ["GPU hosting", "Platform base", "Total monthly", "Total annual"],
        "Cost (USD)": [
            f"${gpu_cost:,.0f}",
            f"${platform_base:,.0f}",
            f"${monthly_total:,.0f}",
            f"${annual_total:,.0f}",
        ]
    })
    st.dataframe(breakdown, use_container_width=True, hide_index=True)
    st.caption(
        "ℹ️ No per-token charge for on-demand hosted models — billing is GPU-hours only."
    )

with col_right:
    fig = go.Figure(go.Pie(
        labels=["GPU hosting", "Platform base"],
        values=[gpu_cost, platform_base],
        hole=0.5,
        marker_colors=["#3266ad", "#BA7517"],
        textinfo="label+percent",
        hovertemplate="%{label}: $%{value:,.0f}<extra></extra>"
    ))
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=260, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Throughput ────────────────────────────────────────────────────────────────
st.subheader("Throughput & utilisation")

t1, t2, t3 = st.columns(3)
t1.metric("Tokens / month", f"{total_tokens_M_month:,.1f}M")
t2.metric("Peak demand", f"{total_toks_per_sec:,.1f} tok/s", f"Capacity: {tok_per_sec_capacity} tok/s")
t3.metric("GPU utilisation", f"{utilisation_pct}%")

if utilisation_pct > 90:
    st.warning(
        f"⚠️ Utilisation at {utilisation_pct}% — consider more instances or a larger GPU config to avoid queuing."
    )
elif utilisation_pct < 20:
    st.info(
        f"ℹ️ Utilisation at only {utilisation_pct}%. You may be over-provisioned — consider scaling down."
    )
else:
    st.success(f"✅ Utilisation looks healthy at {utilisation_pct}%.")

st.divider()

# ── Scenario comparison ───────────────────────────────────────────────────────
st.subheader("Scenario comparison")
st.caption("Common reference configs vs. your current settings")

scenarios = [
    {"label": "Small model, business hours (1×L40S, 10hrs)", "gpu": 4.43, "hrs": 10, "days": 22, "dep": 1, "base": 1050},
    {"label": "Mid model, business hours (2×A100, 10hrs)", "gpu": 11.6, "hrs": 10, "days": 22, "dep": 1, "base": 1050},
    {"label": "Large model, business hours (4×A100, 10hrs)", "gpu": 23.2, "hrs": 10, "days": 22, "dep": 1, "base": 1050},
    {"label": "Large model, HA (8×A100, 10hrs, 2 instances)", "gpu": 46.4, "hrs": 10, "days": 22, "dep": 2, "base": 1050},
    {"label": "Large model, 24/7 (8×H100, 24hrs, 2 instances)", "gpu": 116.0, "hrs": 24, "days": 30, "dep": 2, "base": 1050},
    {"label": "▶ Your config", "gpu": gpu_rate, "hrs": hours_per_day, "days": days_per_month, "dep": num_deployments, "base": platform_base},
]

rows = []
for s in scenarios:
    m = s["gpu"] * s["hrs"] * s["days"] * s["dep"] + s["base"]
    rows.append({
        "Scenario": s["label"],
        "Monthly ($)": f"${m:,.0f}",
        "Annual ($)": f"${m * 12:,.0f}",
    })

st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.divider()

# ── Notes ─────────────────────────────────────────────────────────────────────
with st.expander("Pricing assumptions & notes"):
    st.markdown("""
    - **GPU rates** are IBM list prices from [ibm.com/products/watsonx-ai/pricing](https://www.ibm.com/products/watsonx-ai/pricing) (as of April 2026).
    - **On-demand hosting** requires the **Standard plan** ($1,050/month base). Essentials does not include this feature.
    - **No per-token charge** applies for on-demand hosted models — billing is purely GPU-hours.
    - **GPU utilisation** is estimated at ~12 tok/s per GPU under typical mixed load. Actual throughput varies with model size, batch size, context length, and quantization.
    - Prices are indicative, may vary by country, and exclude applicable taxes. IBM may offer volume or committed-use discounts.
    - Always verify current pricing at [ibm.com/products/watsonx-ai/pricing](https://www.ibm.com/products/watsonx-ai/pricing).
    """)
