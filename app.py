import os
from pathlib import Path

import streamlit as st

from agent import run_agent


# =========================================================
# Page configuration
# =========================================================
st.set_page_config(
    page_title="CryptoShield",
    page_icon="🛡️",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


# =========================================================
# Optional OpenAI API key from Streamlit Secrets
# =========================================================
# In Streamlit Community Cloud:
# App settings -> Secrets
# OPENAI_API_KEY = "..."
try:
    if "OPENAI_API_KEY" in st.secrets and st.secrets["OPENAI_API_KEY"]:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass


# =========================================================
# Small helpers
# =========================================================
def format_money(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def risk_message(level):
    level = str(level or "").lower()

    if level == "critical":
        st.error("🚨 Critical risk case")
    elif level == "high":
        st.error("⚠️ High risk case")
    elif level == "medium":
        st.warning("⚠️ Medium risk case")
    elif level == "low":
        st.success("✅ Low risk case")
    else:
        st.info("Risk level unavailable")


# =========================================================
# Header
# =========================================================
st.title("🛡️ CryptoShield")
st.subheader("AI-Assisted Crypto AML Investigation")

st.caption(
    "Deterministic transaction analysis, sanctions screening, "
    "risk scoring, and evidence-grounded investigation summaries."
)


# =========================================================
# Sidebar controls
# =========================================================
with st.sidebar:
    st.header("Investigation Settings")

    case_id = st.selectbox(
        "Select case",
        ["CASE001", "CASE002", "CASE003"],
    )

    max_hops = st.slider(
        "Transaction network depth",
        min_value=1,
        max_value=5,
        value=3,
        help="Maximum number of wallet-to-wallet hops to trace.",
    )

    use_llm = st.checkbox(
        "Use AI summary",
        value=False,
        help=(
            "If enabled, CryptoShield will use the OpenAI API when an "
            "OPENAI_API_KEY is configured. Otherwise it will safely fall "
            "back to the deterministic summary."
        ),
    )

    investigate = st.button(
        "🔍 Investigate Case",
        type="primary",
        use_container_width=True,
    )


# =========================================================
# Initial page
# =========================================================
if not investigate:
    st.info(
        "Select a case from the sidebar and click **Investigate Case** to begin."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 1. Investigate")
        st.write(
            "Load the alert, transaction history, customer profile, "
            "wallet metadata, and connected transaction network."
        )

    with col2:
        st.markdown("### 2. Score Risk")
        st.write(
            "Apply deterministic rules for sanctions exposure, suspicious "
            "patterns, wallet risk, and customer-behaviour mismatch."
        )

    with col3:
        st.markdown("### 3. Human Review")
        st.write(
            "Present a concise investigation summary and recommended next "
            "action while keeping the final compliance decision with a human."
        )

    st.stop()


# =========================================================
# Run investigation
# =========================================================
with st.spinner(f"Investigating {case_id}..."):
    result = run_agent(
        case_id,
        data_dir=DATA_DIR,
        max_hops=max_hops,
        use_llm=use_llm,
    )


# =========================================================
# Error handling
# =========================================================
if result.get("status") != "success":
    st.error("Investigation failed")

    error = result.get("error")
    if isinstance(error, dict):
        st.write(error.get("message") or error)
    else:
        st.write(error or "Unknown error")

    warnings = result.get("warnings") or []
    if warnings:
        with st.expander("Warnings"):
            for warning in warnings:
                st.write(f"- {warning}")

    st.stop()


# =========================================================
# Extract result sections
# =========================================================
risk = result.get("risk") or {}
alert = result.get("alert") or {}
findings = result.get("findings") or {}
generation = result.get("generation") or {}

history = findings.get("transaction_history") or {}
network = findings.get("network") or {}
patterns = findings.get("patterns") or {}
sanctions = findings.get("sanctions") or {}
behavior = findings.get("behavior") or {}
customer_profile = findings.get("customer_profile") or {}
wallet_risk = findings.get("wallet_risk") or {}

score = risk.get("score", 0)
risk_level = risk.get("risk_level", "Unknown")


# =========================================================
# Investigation overview
# =========================================================
st.divider()
st.header(f"Investigation Result — {case_id}")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Risk Score", f"{score}/100")

with col2:
    st.metric("Risk Level", risk_level)

with col3:
    if sanctions.get("direct_match"):
        sanctions_status = "Direct Match"
    elif sanctions.get("indirect_match"):
        sanctions_status = "Indirect Exposure"
    else:
        sanctions_status = "No Match"

    st.metric("Sanctions", sanctions_status)

with col4:
    mode = generation.get("mode") or "Unknown"
    st.metric("Summary Mode", mode)

risk_message(risk_level)


# =========================================================
# Investigation summary
# =========================================================
st.subheader("🤖 Investigation Summary")
st.write(result.get("summary") or "No summary available.")

reasoning = result.get("reasoning") or []
if reasoning:
    st.markdown("#### Evidence-Based Reasoning")
    for item in reasoning:
        st.markdown(f"- {item}")


# =========================================================
# Recommended action
# =========================================================
st.subheader("👤 Recommended Human Action")
st.info(
    result.get("recommended_next_action")
    or "No recommended action available."
)

st.caption(
    "CryptoShield supports investigation and triage. "
    "The final compliance decision remains with a human reviewer."
)


# =========================================================
# Warnings
# =========================================================
warnings = result.get("warnings") or []
if warnings:
    with st.expander("⚠️ Investigation Warnings"):
        for warning in warnings:
            st.write(f"- {warning}")


# =========================================================
# Detailed tabs
# =========================================================
st.divider()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "🚨 Alert",
        "💳 Transactions",
        "🔗 Network",
        "⚠️ Risk Evidence",
        "👤 Customer",
        "🧾 Raw JSON",
    ]
)


# -------------------------
# Alert tab
# -------------------------
with tab1:
    st.subheader("Original Alert")

    if alert:
        a1, a2, a3 = st.columns(3)

        with a1:
            st.write("**Transaction ID**")
            st.write(alert.get("transaction_id", "N/A"))

            st.write("**Customer ID**")
            st.write(alert.get("customer_id", "N/A"))

        with a2:
            st.write("**Chain**")
            st.write(alert.get("chain", "N/A"))

            st.write("**Asset**")
            st.write(alert.get("asset", "N/A"))

        with a3:
            st.write("**Amount**")
            st.write(alert.get("amount", "N/A"))

            st.write("**Timestamp**")
            st.write(alert.get("timestamp", "N/A"))

        st.write("**Alert Reason**")
        st.write(alert.get("alert_reason", "N/A"))

        with st.expander("Full alert record"):
            st.json(alert)
    else:
        st.info("No alert data available.")


# -------------------------
# Transactions tab
# -------------------------
with tab2:
    st.subheader("Transaction History")

    t1, t2, t3 = st.columns(3)

    with t1:
        st.metric(
            "Transactions",
            history.get("transaction_count", 0),
        )

    with t2:
        st.metric(
            "Incoming USD",
            format_money(history.get("total_incoming_usd")),
        )

    with t3:
        st.metric(
            "Outgoing USD",
            format_money(history.get("total_outgoing_usd")),
        )

    transactions = history.get("transactions") or []

    if transactions:
        st.dataframe(
            transactions,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No transaction records available.")


# -------------------------
# Network tab
# -------------------------
with tab3:
    st.subheader("Transaction Network")

    n1, n2, n3 = st.columns(3)

    with n1:
        st.metric(
            "Connected Wallets",
            len(network.get("connected_wallets") or []),
        )

    with n2:
        st.metric(
            "Maximum Hop Depth",
            network.get("max_depth_reached", 0),
        )

    with n3:
        st.metric(
            "Edges",
            len(network.get("edges") or []),
        )

    nodes = network.get("nodes") or []
    edges = network.get("edges") or []

    st.markdown("#### Wallet Nodes")
    if nodes:
        st.dataframe(
            nodes,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No wallet nodes available.")

    st.markdown("#### Transaction Edges")
    if edges:
        st.dataframe(
            edges,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No transaction edges available.")


# -------------------------
# Risk Evidence tab
# -------------------------
with tab4:
    st.subheader("Risk Score Components")

    components = risk.get("components") or []

    if components:
        st.dataframe(
            components,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No weighted risk indicators were detected.")

    r1, r2 = st.columns(2)

    with r1:
        st.markdown("#### Detected Patterns")
        st.json(patterns)

    with r2:
        st.markdown("#### Sanctions Analysis")
        st.json(sanctions)

    st.markdown("#### Highest-Risk Wallet")
    st.json(wallet_risk)


# -------------------------
# Customer tab
# -------------------------
with tab5:
    st.subheader("Customer Profile")
    st.json(customer_profile)

    st.subheader("Customer Behaviour Analysis")

    if behavior:
        b1, b2, b3 = st.columns(3)

        with b1:
            st.metric(
                "Current Amount",
                format_money(behavior.get("current_amount_usd")),
            )

        with b2:
            st.metric(
                "Typical Maximum",
                format_money(behavior.get("typical_max_usd")),
            )

        with b3:
            st.metric(
                "Mismatch Severity",
                behavior.get("severity", "Unknown"),
            )

        st.write(
            behavior.get("reason")
            or "No customer-behaviour explanation available."
        )

        with st.expander("Full behaviour result"):
            st.json(behavior)
    else:
        st.info("No customer behaviour result available.")


# -------------------------
# Raw JSON tab
# -------------------------
with tab6:
    st.subheader("Complete Agent Result")
    st.json(result)
