import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

import config
from ingest_live import run_single_ingest
from knn_engine import generate_48h_forecast, load_bias_history
from fetch_imd import get_latest_imd

st.set_page_config(page_title="48-Hour IMD Forecast", page_icon="🌤️", layout="wide")

st.markdown("""
<style>
.bias-card {
    background-color: #1e1e2d;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    border-top: 4px solid #667eea;
    margin-bottom: 1rem;
}
.bias-label { font-size: 0.9rem; color: #a0aec0; text-transform: uppercase; letter-spacing: 1px; }
.bias-value { font-size: 2rem; font-weight: 800; color: #fff; margin: 0.5rem 0;}
.bias-sub { font-size: 0.8rem; color: #718096; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data Loading (Cached for 5 mins)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner="Generating 48H KNN Forecast...")
def get_dashboard_data():
    """Generates the forecast, returning the 48h df and the latest Bias error used."""
    df_48 = generate_48h_forecast()
    history = load_bias_history()
    latest_bias = history[-1]['error'] if history else 0.0
    return df_48, latest_bias

def load_live_sensor():
    """Reads immediately from disk so the sensor dot is truly live on refresh."""
    if not os.path.exists(config.LOCAL_CSV):
        return None
    df = pd.read_csv(config.LOCAL_CSV, parse_dates=['TimeStamp'])
    if df.empty:
        return None
    return df.sort_values('TimeStamp').iloc[-1]

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
def main():
    st.title("🌤️ Hyperlocal 48-Hour Forecast")
    st.markdown("*Powered by Local AWS Telemetry + Indian Meteorological Department Ground Truth*")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🔄 Force Refresh (New 5-Minute Ingest)"):
            with st.spinner("Forcing API to fetch latest sensor data..."):
                run_single_ingest()
            st.cache_data.clear()
            st.rerun()

    # Generate Data
    df_48, latest_bias = get_dashboard_data()
    sensor = load_live_sensor()
    imd = get_latest_imd()

    if df_48 is None or sensor is None:
        st.warning("🔄 Waiting for initial sensor data ingestion... The background service is currently pulling your AWS history. Please wait 10 seconds.")
        
        # Clear the failed cache memory so it tries again
        st.cache_data.clear()
        
        import time
        time.sleep(5)
        st.rerun()
        return

    now = datetime.now()
    sensor_temp = float(sensor['CurrentTemperature'])
    sensor_time = pd.to_datetime(sensor['TimeStamp']).strftime('%H:%M, %d %b') + ' (IST)'

    # ── KPIs ──
    st.markdown("### 📡 Live Telemetry Sync")
    k1, k2, k3, k4 = st.columns(4)
    
    with k1:
        st.markdown(f"""
        <div class="bias-card" style="border-top-color: #51cf66;">
            <div class="bias-label">Your AWS Sensor</div>
            <div class="bias-value" style="color:#51cf66;">{sensor_temp:.1f}°C</div>
            <div class="bias-sub">Read: {sensor_time}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with k2:
        i_temp = f"{imd['temperature']:.1f}°C" if imd and imd['temperature'] else "N/A"
        i_time = imd['timestamp_str'] + ' (IST)' if imd else "Offline"
        st.markdown(f"""
        <div class="bias-card" style="border-top-color: #ffa94d;">
            <div class="bias-label">IMD Chandigarh ({config.IMD_STATION_NAME})</div>
            <div class="bias-value" style="color:#ffa94d;">{i_temp}</div>
            <div class="bias-sub">Read: {i_time}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with k3:
        st.markdown(f"""
        <div class="bias-card" style="border-top-color: #ff6b6b;">
            <div class="bias-label">Current AI Bias Offset</div>
            <div class="bias-value" style="color:#ff6b6b;">{latest_bias:+.2f}°C</div>
            <div class="bias-sub">Exponentially Weighted Correction</div>
        </div>
        """, unsafe_allow_html=True)
        
    with k4:
        st.markdown(f"""
        <div class="bias-card" style="border-top-color: #b197fc;">
            <div class="bias-label">Forecast (Next Hour)</div>
            <div class="bias-value" style="color:#b197fc;">{df_48.iloc[0]['Corrected_Temp']:.1f}°C</div>
            <div class="bias-sub">KNN Smooth-Interpolated</div>
        </div>
        """, unsafe_allow_html=True)


    # ── CHART ──
    st.markdown("### 📈 48-Hour Temperature Curve")
    fig = go.Figure()
    
    # KNN Line
    fig.add_trace(go.Scatter(
        x=df_48['DateTime'], y=df_48['Corrected_Temp'],
        mode='lines+markers', name='KNN Forecast',
        line=dict(color='#ffd43b', width=3, shape='spline'),
        marker=dict(size=8, color='#ffd43b', line=dict(color='#1a1a2e', width=1.5)),
        fill='tozeroy', fillcolor='rgba(255,212,59,0.07)',
        hovertemplate='%{x|%H:%M}<br><b>%{y:.1f}°C</b><extra></extra>',
    ))
    
    # Live Sensor Dot
    live_time = pd.to_datetime(sensor['TimeStamp'])
    fig.add_trace(go.Scatter(
        x=[live_time], y=[sensor_temp],
        mode='markers+text',
        name='Live Sensor',
        marker=dict(size=14, color='#ff6b6b', symbol='circle', line=dict(color='white', width=2)),
        text=[f"<b>{sensor_temp:.1f}°</b>"],
        textposition='top center',
        textfont=dict(size=14, color='#ff6b6b'),
        hovertemplate=f'Station live: {sensor_temp:.1f}°C<extra></extra>',
    ))
    
    fig.update_layout(
        height=500, margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#a0aec0'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickformat='%d %b\n%H:%M'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', ticksuffix="°C"),
        hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
