import streamlit as st
import requests
import time

st.set_page_config(page_title="AURA Dashboard", layout="wide")
st.title("🔥 AURA Industrial Intelligence")

# Manual refresh button + auto-refresh using Streamlit's native rerun
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

# Auto-rerun every 2 seconds
if time.time() - st.session_state.last_refresh > 2:
    st.session_state.last_refresh = time.time()
    st.rerun()

col1, col2, col3 = st.columns(3)

try:
    # Signal API status
    signal_resp = requests.get("http://localhost:8003/status", timeout=2)
    signal_data = signal_resp.json()
    
    anomalies = signal_data.get("anomalies_detected", 0)
    latest = signal_data.get("latest_readings", {})
    
    # Anomaly banner
    if anomalies > 0:
        st.error(f"🚨 ANOMALY DETECTED — Count: {anomalies}")
    else:
        st.success("✅ All systems normal")
    
    # Metrics
    temp = latest.get("P101_TEMP", {}).get("value", 0)
    vib = latest.get("P101_VIBRATION", {}).get("value", 0)
    press = latest.get("P101_PRESSURE", {}).get("value", 0)
    
    col1.metric("Temperature", f"{temp:.1f} °C", None)
    col2.metric("Vibration", f"{vib:.2f} mm/s", None)
    col3.metric("Pressure", f"{press:.2f} bar", None)
    
    # Edge agent health
    edge_resp = requests.get("http://localhost:8002/health", timeout=2)
    edge_data = edge_resp.json()
    
    st.sidebar.metric("Tags Ingested", edge_data.get("tags_ingested", 0))
    st.sidebar.metric("Anomalies", anomalies)
    
except Exception as e:
    st.warning(f"Connection issue: {e}")
    st.info("Make sure all services are running: simulator (8001), edge-agent (8002), signal-api (8003)")

st.divider()
st.caption("AURA MVI v0.1.0 | Solo Build Week 1")