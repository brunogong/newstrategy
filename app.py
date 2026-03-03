import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

from strategy import (
    generate_signal,
    swing_levels,
    fib_levels,
    detect_fvg
)

# ============================
# CONFIGURAZIONE UI
# ============================

st.set_page_config(
    page_title="XAUUSD ICT Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tema scuro + sidebar chiara
st.markdown("""
    <style>
        .main { background-color: #0E1117; }
        .stApp { background-color: #0E1117; }

        h1, h2, h3, h4, h5, h6, p, div, span {
            color: #E0E0E0 !important;
        }

        section[data-testid="stSidebar"] {
            background-color: #F5F5F5 !important;
            border-right: 2px solid #D0D0D0;
        }

        section[data-testid="stSidebar"] * {
            color: black !important;
        }

        .sidebar-card {
            background-color: white;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #D9D9D9;
            margin-bottom: 18px;
            box-shadow: 0px 2px 4px rgba(0,0,0,0.08);
        }

        .sidebar-title {
            font-size: 20px;
            font-weight: 700;
            color: black !important;
            margin-bottom: 10px;
        }

        .metric-card {
            padding: 18px;
            border-radius: 10px;
            background-color: #161A23;
            border: 1px solid #2A2F3A;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# ============================
# SIDEBAR
# ============================

with st.sidebar:
    st.markdown("<div class='sidebar-card'>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-title'>⚙️ Parametri Strategia</div>", unsafe_allow_html=True)

    strategy_mode = st.selectbox(
        "Modalità strategia",
        ["Swing Trading ICT", "Scalping ICT"]
    )

    equity = st.number_input("Equity (USD)", value=10000)
    risk_pct = st.number_input("Rischio per trade (%)", value=1)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-card'>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-title'>📘 Info Strategia</div>", unsafe_allow_html=True)
    st.markdown("Metodo: ICT Breakout / OTE / FVG")
    st.markdown("Timeframe: H1 + H4 Trend Filter")
    st.markdown("</div>", unsafe_allow_html=True)

# ============================
# TITOLO
# ============================

st.markdown("<h1 style='text-align:center;'>📈 XAUUSD ICT Trading Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ============================
# API TWELVEDATA
# ============================

API_KEY = "b8f12bd961754eb6a3d999eb41936afd"
SYMBOL = "XAU/USD"

# H1 DATA
url_h1 = (
    f"https://api.twelvedata.com/time_series?"
    f"symbol={SYMBOL}&interval=1h&outputsize=300&apikey={API_KEY}"
)

response_h1 = requests.get(url_h1).json()

if "values" not in response_h1:
    st.error("Errore nel recupero dati H1 da TwelveData.")
    st.stop()

df = pd.DataFrame(response_h1["values"])
df = df.rename(columns={"datetime": "time"})
df = df.astype({"open": float, "high": float, "low": float, "close": float})
df = df.sort_values("time")

# H4 DATA
url_h4 = (
    f"https://api.twelvedata.com/time_series?"
    f"symbol={SYMBOL}&interval=4h&outputsize=300&apikey={API_KEY}"
)

response_h4 = requests.get(url_h4).json()

if "values" not in response_h4:
    st.error("Errore nel recupero dati H4 da TwelveData.")
    st.stop()

df_h4 = pd.DataFrame(response_h4["values"])
df_h4 = df_h4.rename(columns={"datetime": "time"})
df_h4 = df_h4.astype({"open": float, "high": float, "low": float, "close": float})
df_h4 = df_h4.sort_values("time")

df_h4["ma50"] = df_h4["close"].rolling(50).mean()
df_h4["ma200"] = df_h4["close"].rolling(200).mean()

last_h4 = df_h4.iloc[-1]

if last_h4["ma50"] > last_h4["ma200"]:
    trend_h4 = "BULL"
elif last_h4["ma50"] < last_h4["ma200"]:
    trend_h4 = "BEAR"
else:
    trend_h4 = "NEUTRAL"

# ============================
# METRICHE
# ============================

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.subheader("📊 Trend H4")
    color = "green" if trend_h4 == "BULL" else "red" if trend_h4 == "BEAR" else "gray"
    st.markdown(f"<h2 style='color:{color};'>{trend_h4}</h2>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

signal = generate_signal(df, equity, risk_pct, strategy_mode, trend_h4)

with col2:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.subheader("🎯 Segnale")
    sig_color = "green" if signal["signal"] == "BUY" else "red" if signal["signal"] == "SELL" else "gray"
    st.markdown(f"<h2 style='color:{sig_color};'>{signal['signal']}</h2>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.subheader("💰 Lotti")
    lots = signal.get("lot_size", 0)
    st.markdown(f"<h2>{lots:.2f}</h2>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ============================
# SUPPORTO / RESISTENZA / OTE / FVG
# ============================

df_sw = swing_levels(df.copy(), lookback=10)
ref = df_sw.iloc[-2]

resistenza = ref["swing_high"]
supporto = ref["swing_low"]

impulse_high = df.iloc[-2]["high"]
impulse_low = df.iloc[-2]["low"]
fib = fib_levels(impulse_high, impulse_low)

ote_low = fib["0.5"]
ote_high = fib["0.618"]

fvgs = detect_fvg(df)

# ============================
# GRAFICO PROFESSIONALE
# ============================

fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df["time"],
    open=df["open"],
    high=df["high"],
    low=df["low"],
    close=df["close"],
    name="XAUUSD H1"
))

fig.add_hline(y=resistenza, line_color="red", line_dash="dash", opacity=0.6)
fig.add_hline(y=supporto, line_color="green", line_dash="dash", opacity=0.6)

fig.add_shape(
    type="rect",
    x0=df["time"].iloc[-80],
    x1=df["time"].iloc[-1],
    y0=ote_low,
    y1=ote_high,
    fillcolor="rgba(255, 215, 0, 0.15)",
    line=dict(color="gold", width=1),
)

for fvg in fvgs:
    fig.add_shape(
        type="rect",
        x0=df["time"].iloc[fvg["index"]-2],
        x1=df["time"].iloc[fvg["index"]],
        y0=min(fvg["start"], fvg["end"]),
        y1=max(fvg["start"], fvg["end"]),
        fillcolor="rgba(0,150,255,0.15)" if fvg["type"] == "BULL" else "rgba(255,0,0,0.15)",
        line=dict(width=0),
    )

if signal["signal"] in ["BUY", "SELL"]:
    entry = signal["entry"]
    sl = signal["sl"]
    tp = signal["tp"]

    fig.add_trace(go.Scatter(
        x=[df["time"].iloc[-1]],
        y=[entry],
        mode="markers",
        marker=dict(color="black", size=14),
        name="Entry"
    ))

    fig.add_trace(go.Scatter(
        x=[df["time"].iloc[-1]],
        y=[sl],
        mode="markers",
        marker=dict(color="red", size=14),
        name="Stop Loss"
    ))

    fig.add_trace(go.Scatter(
        x=[df["time"].iloc[-1]],
        y=[tp],
        mode="markers",
        marker=dict(color="green", size=14),
        name="Take Profit"
    ))

fig.update_layout(
    height=800,
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    title="📉 XAUUSD - ICT Market Structure"
)

st.plotly_chart(fig, use_container_width=True)
