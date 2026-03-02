import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# Import dalla strategia
from strategy import (
    generate_signal,
    swing_levels,
    fib_levels,
    detect_fvg
)

# ============================
# CONFIGURAZIONE STREAMLIT
# ============================

st.set_page_config(page_title="XAUUSD Swing Signals", layout="wide")
st.title("📈 XAUUSD Swing Trading Signals (ICT: Breakout + OTE + FVG + Trend H4)")

# ============================
# INPUT UTENTE
# ============================

equity = st.number_input("Equity (USD)", value=10000)
risk_pct = st.number_input("Rischio per trade (%)", value=1)

# ============================
# API TWELVEDATA
# ============================

API_KEY = "b8f12bd961754eb6a3d999eb41936afd"
SYMBOL = "XAU/USD"

# ============================
# DATI H1
# ============================

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

# ============================
# DATI H4 PER TREND FILTER
# ============================

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

st.markdown(f"### 📌 Trend H4: **{trend_h4}**")

# ============================
# CALCOLO SEGNALE H1
# ============================

signal = generate_signal(df, equity, risk_pct)

# ============================
# FILTRO TREND H4
# ============================

if signal["signal"] == "BUY" and trend_h4 != "BULL":
    signal = {"signal": "NO TRADE", "reason": "Trend H4 non rialzista"}

if signal["signal"] == "SELL" and trend_h4 != "BEAR":
    signal = {"signal": "NO TRADE", "reason": "Trend H4 non ribassista"}

st.subheader("Segnale attuale")
st.write(signal)

# ============================
# SUPPORTO / RESISTENZA
# ============================

df_sw = swing_levels(df.copy(), lookback=10)
ref = df_sw.iloc[-2]

resistenza = ref["swing_high"]
supporto = ref["swing_low"]

# ============================
# ZONA OTE
# ============================

impulse_high = df.iloc[-2]["high"]
impulse_low = df.iloc[-2]["low"]
fib = fib_levels(impulse_high, impulse_low)

ote_low = fib["0.5"]
ote_high = fib["0.618"]

# ============================
# FVG
# ============================

fvgs = detect_fvg(df)

# ============================
# GRAFICO COMPLETO
# ============================

fig = go.Figure()

# Candele
fig.add_trace(go.Candlestick(
    x=df["time"],
    open=df["open"],
    high=df["high"],
    low=df["low"],
    close=df["close"],
    name="XAUUSD H1"
))

# Resistenza
fig.add_trace(go.Scatter(
    x=[df["time"].iloc[0], df["time"].iloc[-1]],
    y=[resistenza, resistenza],
    mode="lines",
    line=dict(color="red", width=2, dash="dash"),
    name="Resistenza"
))

# Supporto
fig.add_trace(go.Scatter(
    x=[df["time"].iloc[0], df["time"].iloc[-1]],
    y=[supporto, supporto],
    mode="lines",
    line=dict(color="green", width=2, dash="dash"),
    name="Supporto"
))

# Zona OTE
fig.add_shape(
    type="rect",
    x0=df["time"].iloc[-80],
    x1=df["time"].iloc[-1],
    y0=ote_low,
    y1=ote_high,
    fillcolor="rgba(255, 215, 0, 0.15)",
    line=dict(color="gold", width=1),
)

# FVG
for fvg in fvgs:
    fig.add_shape(
        type="rect",
        x0=df["time"].iloc[fvg["index"]-2],
        x1=df["time"].iloc[fvg["index"]],
        y0=fvg["start"],
        y1=fvg["end"],
        fillcolor="rgba(0,150,255,0.15)" if fvg["type"] == "BULL" else "rgba(255,0,0,0.15)",
        line=dict(width=0),
    )

# ============================
# ENTRY / SL / TP (pallini)
# ============================

if signal["signal"] in ["BUY", "SELL"]:
    entry = signal["entry"]
    sl = signal["sl"]
    tp = signal["tp"]

    # Entry = pallino nero
    fig.add_trace(go.Scatter(
        x=[df["time"].iloc[-1]],
        y=[entry],
        mode="markers",
        marker=dict(color="black", size=12),
        name="Entry"
    ))

    # SL = pallino rosso
    fig.add_trace(go.Scatter(
        x=[df["time"].iloc[-1]],
        y=[sl],
        mode="markers",
        marker=dict(color="red", size=12),
        name="Stop Loss"
    ))

    # TP = pallino verde
    fig.add_trace(go.Scatter(
        x=[df["time"].iloc[-1]],
        y=[tp],
        mode="markers",
        marker=dict(color="green", size=12),
        name="Take Profit"
    ))

fig.update_layout(
    height=750,
    xaxis_rangeslider_visible=False,
    title="XAUUSD - ICT Strategy (Breakout + OTE + FVG + Trend H4)"
)

st.plotly_chart(fig, use_container_width=True)

# Info extra
st.markdown(f"**Resistenza:** {resistenza:.2f}")
st.markdown(f"**Supporto:** {supporto:.2f}")
st.markdown(f"**OTE 0.5–0.618:** {ote_low:.2f} → {ote_high:.2f}")
