import streamlit as st

st.set_page_config(
    page_title="wx.ai Nemotron Cost Estimator",
    page_icon="🧮",
    layout="wide"
)

st.title("IBM watsonx.ai — Nemotron 120B Cost Estimator")
st.caption("For on-demand hosted deployments · 200 accounts · Based on IBM list pricing")

st.divider()

# ── Sidebar: inputs ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Configuration")

    st.subheader("Deployment")
    gpu_options = {
        "4×A100 (min viable) — $23.2/hr": 23.2,
        "8×A100 (full throughput) — $46.4/hr": 46.4,
        "4×H100 — $58.0/hr": 58.0,
        "8×H100 (recommended) — $116.0/hr": 116.0,
        "4×H200 — $64.0/hr": 64.0,
        "8×H200 — $128.0/hr": 128.0,
    }
    gpu_label = st.selectbox("GPU configuration", list(gpu_options.keys()))
    gpu_rate = gpu_options[gpu_label]

    num_deployments = st.selectbox(
        "Number of deployment instances",
        [1, 2, 4],
        help="Multiple instances reduce queue time for concurrent users."
    )

    hours_per_day = st.slider("Hours active per day", 1, 24, 10)
    days_per_month = st.slider("Days per month", 1, 31, 22)

    st.subheader("Token usage (per account)")
    prompt_tokens = st.slider("Avg prompt tokens / query", 100, 8000, 1000, step=100)
    output_tokens = st.slider("Avg output tokens / query", 100, 4000, 500, step=100)
    queries_per_day = st.slider("Queries per account per day", 1, 200, 20)

    st.subheader("Platform plan")
    plan = st.radio(
        "Pricing plan",
        ["Essentials ($0/mo base)", "Standard ($1,050/mo)"],
        index=1,
        help="On-demand model hosting requires the Standard plan."
    )
    platform_base = 1050 if "Standard" in plan else 0

    num_accounts = st.number_input("Number of accounts", min_value=1, value=200, step=10)

# ── Calculations ─────────────────────────────────────────────────────────────
gpu_cost = gpu_rate * hours_per_day * days_per_month * num_deployments
total_tokens_M = (num_accounts * queries_per_day * (prompt_tokens + output_tokens) * days_per_month) / 1_000_000
monthly_total = gpu_cost + platform_base
annual_total = monthly_total * 12
per_account = monthly_total / num_accounts

gpu_count = 4 if gpu_rate in [23.2, 58.0, 64.0] else 8
tok_per_sec = gpu_count * 12 * num_deployments
total_toks_per_sec = (num_accounts * queries_per_day * (prompt_tokens + output_tokens)) / (hours_per_day * 3600)
utilisation_pct = min(100, round((total_toks_per_sec / tok_per_sec) * 100, 1))

# ── Summary metrics ───────────────────────────────────────────────────────────
st.subheader("Cost summary")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Monthly cost", f"${monthly_total:,.0f}")
c2.metric("Annual cost", f"${annual_total:,.0f}")
c3.metric(f"Per account / mo", f"${per_account:,.0f}", f"{num_accounts} accounts")
c4.metric("Est. GPU utilisation", f"{utilisation_pct}%", help="Based on ~12 tok/s per A100/H100 GPU")

st.divider()

# ── Cost breakdown ────────────────────────────────────────────────────────────
st.subheader("Cost breakdown")

col_left, col_right = st.columns([1, 1])

with col_left:
    import pandas as pd

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
        "ℹ️ No per-token charge applies for on-demand hosted models — you pay GPU-hours only. "
        "Token cost would apply only if IBM later adds per-token billing on top."
    )

with col_right:
    import plotly.graph_objects as go

    labels = ["GPU hosting", "Platform base"]
    values = [gpu_cost, platform_base]
    colors = ["#3266ad", "#BA7517"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker_colors=colors,
        textinfo="label+percent",
        hovertemplate="%{label}: $%{value:,.0f}<extra></extra>"
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        height=260,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Token volume ──────────────────────────────────────────────────────────────
st.subheader("Token volume")

t1, t2, t3 = st.columns(3)
t1.metric("Total tokens / month", f"{total_tokens_M:,.1f}M")
t2.metric("Tokens / account / month", f"{total_tokens_M * 1_000_000 / num_accounts:,.0f}")
t3.metric("Peak demand (tok/s)", f"{total_toks_per_sec:,.1f}", f"Capacity: {tok_per_sec} tok/s")

if utilisation_pct > 90:
    st.warning(
        f"⚠️ GPU utilisation is {utilisation_pct}% — consider adding a second deployment instance "
        "or upgrading to a higher-GPU config to avoid queuing."
    )
elif utilisation_pct < 20:
    st.info(
        f"ℹ️ GPU utilisation is only {utilisation_pct}%. You may be over-provisioned. "
        "Consider reducing to 1 instance or scaling down the GPU config."
    )
else:
    st.success(f"✅ GPU utilisation looks healthy at {utilisation_pct}%.")

st.divider()

# ── Scenario comparison ───────────────────────────────────────────────────────
st.subheader("Scenario comparison")
st.caption("Fixed scenarios vs. your current config")

scenarios = [
    {"label": "Minimal (4×A100, 8hrs, 1 instance)", "gpu": 23.2, "hrs": 8, "days": 22, "dep": 1, "base": 1050},
    {"label": "Business hours (4×A100, 10hrs, 1 instance)", "gpu": 23.2, "hrs": 10, "days": 22, "dep": 1, "base": 1050},
    {"label": "HA (8×A100, 10hrs, 2 instances)", "gpu": 46.4, "hrs": 10, "days": 22, "dep": 2, "base": 1050},
    {"label": "24/7 (8×A100, 24hrs, 2 instances)", "gpu": 46.4, "hrs": 24, "days": 30, "dep": 2, "base": 1050},
    {"label": "▶ Your config", "gpu": gpu_rate, "hrs": hours_per_day, "days": days_per_month, "dep": num_deployments, "base": platform_base},
]

rows = []
for s in scenarios:
    monthly = s["gpu"] * s["hrs"] * s["days"] * s["dep"] + s["base"]
    rows.append({
        "Scenario": s["label"],
        "Monthly ($)": f"${monthly:,.0f}",
        "Annual ($)": f"${monthly * 12:,.0f}",
        "Per account ($)": f"${monthly / num_accounts:,.0f}",
    })

df_scenarios = pd.DataFrame(rows)
st.dataframe(df_scenarios, use_container_width=True, hide_index=True)

st.divider()

# ── Notes ─────────────────────────────────────────────────────────────────────
with st.expander("Pricing assumptions & notes"):
    st.markdown("""
    - **GPU rates** are IBM list prices from [ibm.com/products/watsonx-ai/pricing](https://www.ibm.com/products/watsonx-ai/pricing) (as of April 2026).
    - **On-demand hosting** requires the **Standard plan** ($1,050/month base). Essentials does not include this feature.
    - **No per-token charge** applies for on-demand hosted models — billing is purely GPU-hours.
    - **Nemotron Super 120B** is not available as shared inference on wx.ai SaaS — it must run as an on-demand deployment.
    - **GPU utilisation** is estimated at ~12 tok/s per A100/H100 GPU under typical mixed load. Actual throughput varies with batch size, context length, and quantization.
    - Prices are indicative, may vary by country, and exclude applicable taxes. IBM may offer volume or committed-use discounts for named accounts.
    - Always verify current pricing at [ibm.com/products/watsonx-ai/pricing](https://www.ibm.com/products/watsonx-ai/pricing).
    """)
