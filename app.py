import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# Import della strategia
from strategy import generate_signal

# ============================
# CONFIGURAZIONE STREAMLIT
# ============================

st.set_page_config(page_title="XAUUSD Swing Signals", layout="wide")
st.title("📈 XAUUSD Swing Trading Signals (Breakout + OTE + MACD)")

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
INTERVAL = "1h"

url = (
    f"https://api.twelvedata.com/time_series?"
    f"symbol={SYMBOL}&interval={INTERVAL}&outputsize=300&apikey={API_KEY}"
)

response = requests.get(url).json()

if "values" not in response:
    st.error("Errore nel recupero dati da TwelveData.")
    st.stop()

df = pd.DataFrame(response["values"])
df = df.rename(columns={"datetime": "time"})
df = df.astype({"open": float, "high": float, "low": float, "close": float})
df = df.sort_values("time")

# ============================
# CALCOLO SEGNALE
# ============================

signal = generate_signal(df, equity, risk_pct)

st.subheader("Segnale attuale")
st.write(signal)

# ============================
# GRAFICO CANDLESTICK
# ============================

fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df["time"],
    open=df["open"],
    high=df["high"],
    low=df["low"],
    close=df["close"]
))

fig.update_layout(
    height=600,
    xaxis_rangeslider_visible=False,
    title="XAUUSD - Grafico H1"
)

st.plotly_chart(fig, use_container_width=True)
