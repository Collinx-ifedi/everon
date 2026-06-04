# app.py

import os
import json
import streamlit as st
import pandas as pd
from datetime import datetime

# Enforce enterprise page configuration layout boundaries immediately
st.set_page_config(
    page_title="Everon Asset Intelligence Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------------------
# Local File Storage Infrastructure Paths
# -------------------------------------------------------------------------
DATA_DIR = "data"
STATE_FILE = os.path.join(DATA_DIR, "market_intelligence.json")
LOG_FILE = os.path.join(DATA_DIR, "agent_logs.json")

# -------------------------------------------------------------------------
# Dynamic Data Ingestion Workers
# -------------------------------------------------------------------------
def load_market_intelligence() -> dict:
    """Reads and parses the preserved atomic market state file safely."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def load_agent_logs() -> list:
    """Reads and parses telemetry logging events backwards for real-time monitoring."""
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            parsed_logs = []
            for line in lines:
                if line.strip():
                    parsed_logs.append(json.loads(line.strip()))
            # Reverse to display the freshest telemetry packets at the top
            return parsed_logs[::-1]
    except Exception:
        return []

# -------------------------------------------------------------------------
# Application User Interface Render Frame
# -------------------------------------------------------------------------
def render_dashboard():
    # Application Branding Title
    st.title("⚡ Everon Multi-Service Intelligence Hub")
    st.caption("Autonomous Sequential 10-Coin Scan Ecosystem & Dual-Model Strategic Router")
    st.markdown("---")

    # Ingest runtime file snapshots
    market_data = load_market_intelligence()
    system_logs = load_agent_logs()

    # --- TOP METRIC BANNER ROW ---
    total_tracked = len(market_data)
    indecisive_count = sum(1 for asset in market_data.values() if asset.get("decision_status") == "INDECISIVE")
    isolated_count = sum(1 for asset in market_data.values() if asset.get("directional_bias") == "ERROR_ISOLATED")
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Tracked Core Index Assets", f"{total_tracked} / 10")
    with col_m2:
        st.metric("Active Indecision Exceptions", indecisive_count, delta="- Warning Flag" if indecisive_count > 0 else "Nominal", delta_color="inverse")
    with col_m3:
        st.metric("Gracefully Isolated Tokens", isolated_count, delta="- Intercept Trapped" if isolated_count > 0 else "Stable", delta_color="inverse")
    with col_m4:
        st.metric("Daemon Loop Sleep State", "120s Ticking", help="Non-blocking sequential execution timing window.")

    st.markdown("### 📊 Market Intelligence Matrix")

    if not market_data:
        st.info("No synthesized market state data identified. Ensure main.py or scheduler.py daemon is currently running.")
        return

    # --- ASSET INTELLIGENCE CARDS ---
    # Group assets dynamically into columns to optimize screenspace usage
    for token, data in market_data.items():
        bias = data.get("directional_bias", "NEUTRAL")
        status = data.get("decision_status", "CONVERGENT")
        confidence = data.get("confidence_score", 0.50)
        narrative = data.get("gemini_narrative", "No processing text generated.")
        telemetry = data.get("indecision_telemetry")

        # Design custom operational alert wrappers matching asset health profiles
        if bias == "ERROR_ISOLATED":
            box_type = "error"
            title_suffix = "🛑 [PIPELINE TIMEOUT / ISOLATED]"
        elif status == "INDECISIVE":
            box_type = "warning"
            title_suffix = "⚠️ [DIVERGENT TREND INDECISION]"
        else:
            box_type = "info"
            title_suffix = f" | {bias} (Confidence: {confidence:.2f})"

        with st.container():
            st.markdown(f"#### **Asset Segment: {token}** {title_suffix}")
            
            # Sub-layout grid split
            col_left, col_right = st.columns([2, 3])
            
            with col_left:
                st.markdown("**Qualitative Synthesized Outlook (Gemini Pro):**")
                st.write(narrative)
                
            with col_right:
                # Render clear exception reporting components requested by the architecture parameters
                if status == "INDECISIVE" and telemetry:
                    st.markdown("**🚨 Engine Indecision Telemetry:**")
                    st.error(telemetry.get("warning", "Divergence Identified."))
                    st.markdown("**Underlying Validation Reasons:**")
                    for reason in telemetry.get("reasons", []):
                        st.markdown(f"- *{reason}*")
                    st.markdown("**Actionable Strategic Allocation Advice:**")
                    st.info(telemetry.get("strategic_advice", "Maintain basic structures."))
                    
                elif bias == "ERROR_ISOLATED" and telemetry:
                    st.markdown("**🛡️ Intercept Sequence Isolation Details:**")
                    st.warning("Tool endpoint returned a connection exception or timeout. Processing insulated safely.")
                    st.markdown("**Stack Details:**")
                    st.code(telemetry.get("reasons", ["Unknown network error"])[0], language="python")
                    st.markdown("**Recovery Policy Advice:**")
                    st.markdown(f"👉 *{telemetry.get('strategic_advice')}*")
                    
                else:
                    st.success("🟢 Convergence Profile Stable. Operational weights executing within optimal historical bounds.")
                    
            st.markdown("---")

    # --- REAL-TIME TELEMETRY LOG BLOCK ---
    st.markdown("### 📜 Real-Time Agent Stream Telemetry")
    if system_logs:
        # Convert to a data frame layout structure for crisp clean presentation tables
        log_df = pd.DataFrame(system_logs)
        # Select and order required columns if they exist
        cols = [c for c in ["timestamp", "level", "message"] if c in log_df.columns]
        st.dataframe(log_df[cols], use_container_width=True, height=250)
    else:
        st.text("No log frames found in local agent data files.")

# -------------------------------------------------------------------------
# Application Core Launch Entry Override
# -------------------------------------------------------------------------
if __name__ == "__main__":
    render_dashboard()