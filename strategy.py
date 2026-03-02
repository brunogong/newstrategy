import pandas as pd
import numpy as np

# ============================
# SWING LEVELS
# ============================

def swing_levels(df, lookback=10):
    df["swing_high"] = df["high"].rolling(lookback).max()
    df["swing_low"] = df["low"].rolling(lookback).min()
    return df

# ============================
# FIBONACCI LEVELS
# ============================

def fib_levels(high, low):
    return {
        "0.5": low + (high - low) * 0.5,
        "0.618": low + (high - low) * 0.618,
        "1.272": high + (high - low) * 1.272,
        "1.618": high + (high - low) * 1.618,
    }

# ============================
# MACD
# ============================

def macd(df, fast=12, slow=26, signal=9):
    df["ema_fast"] = df["close"].ewm(span=fast).mean()
    df["ema_slow"] = df["close"].ewm(span=slow).mean()
    df["macd"] = df["ema_fast"] - df["ema_slow"]
    df["signal"] = df["macd"].ewm(span=signal).mean()
    return df

# ============================
# BREAKOUT
# ============================

def detect_breakout(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["close"] > prev["swing_high"]:
        return "BREAKOUT_UP"

    if last["close"] < prev["swing_low"]:
        return "BREAKOUT_DOWN"

    return None

# ============================
# PULLBACK OTE
# ============================

def detect_pullback(df, breakout_type):
    last = df.iloc[-1]
    impulse_high = df.iloc[-2]["high"]
    impulse_low = df.iloc[-2]["low"]
    fib = fib_levels(impulse_high, impulse_low)

    if breakout_type == "BREAKOUT_UP":
        if fib["0.5"] <= last["close"] <= fib["0.618"]:
            return "PULLBACK_OK"

    if breakout_type == "BREAKOUT_DOWN":
        if fib["0.618"] <= last["close"] <= fib["0.5"]:
            return "PULLBACK_OK"

    return None

# ============================
# MOMENTUM (MACD)
# ============================

def detect_momentum(df, breakout_type):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if breakout_type == "BREAKOUT_UP":
        if prev["macd"] < prev["signal"] and last["macd"] > last["signal"]:
            return "MACD_BULL"

    if breakout_type == "BREAKOUT_DOWN":
        if prev["macd"] > prev["signal"] and last["macd"] < last["signal"]:
            return "MACD_BEAR"

    return None

# ============================
# FVG (FAIR VALUE GAPS)
# ============================

def detect_fvg(df):
    fvg_list = []

    for i in range(2, len(df)):
        c1 = df.iloc[i-2]
        c3 = df.iloc[i]

        # FVG rialzista
        if c3["low"] > c1["high"]:
            fvg_list.append({
                "type": "BULL",
                "start": c1["high"],
                "end": c3["low"],
                "index": i
            })

        # FVG ribassista
        if c3["high"] < c1["low"]:
            fvg_list.append({
                "type": "BEAR",
                "start": c1["low"],
                "end": c3["high"],
                "index": i
            })

    return fvg_list


def fvg_filter(df, breakout_type):
    fvgs = detect_fvg(df)
    last_close = df.iloc[-1]["close"]

    for fvg in fvgs:
        if breakout_type == "BREAKOUT_UP" and fvg["type"] == "BULL":
            if fvg["start"] <= last_close <= fvg["end"]:
                return True

        if breakout_type == "BREAKOUT_DOWN" and fvg["type"] == "BEAR":
            if fvg["end"] <= last_close <= fvg["start"]:
                return True

    return False

# ============================
# POSITION SIZE (XAUUSD)
# ============================

def position_size(equity, risk_pct, entry, sl):
    risk_amount = equity * (risk_pct / 100)

    pip_value = 0.01  # XAUUSD: 1 pip = 0.01
    distance_pips = abs(entry - sl) / pip_value

    lot_size = risk_amount / distance_pips  # 1 lotto = 1 USD/pip

    return lot_size, risk_amount

# ============================
# GENERAZIONE SEGNALE COMPLETO ICT
# ============================

def generate_signal(df, equity=10000, risk_pct=1):
    df = swing_levels(df)
    df = macd(df)

    breakout = detect_breakout(df)
    if breakout is None:
        return {"signal": "NO TRADE", "reason": "Nessun breakout rilevato"}

    pullback = detect_pullback(df, breakout)
    if pullback is None:
        return {"signal": "WAIT", "reason": "Breakout ma nessun pullback OTE"}

    momentum = detect_momentum(df, breakout)
    if momentum is None:
        return {"signal": "WAIT", "reason": "Pullback ok ma MACD non conferma"}

    if not fvg_filter(df, breakout):
        return {"signal": "WAIT", "reason": "Pullback non dentro un FVG"}

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if breakout == "BREAKOUT_UP":
        sl = prev["swing_low"]
        fib = fib_levels(prev["high"], prev["low"])
        tp = fib["1.618"]
        lot_size, risk_amount = position_size(equity, risk_pct, last["close"], sl)

        return {
            "signal": "BUY",
            "entry": last["close"],
            "sl": sl,
            "tp": tp,
            "lot_size": lot_size,
            "risk_usd": risk_amount
        }

    if breakout == "BREAKOUT_DOWN":
        sl = prev["swing_high"]
        fib = fib_levels(prev["high"], prev["low"])
        tp = fib["1.618"]
        lot_size, risk_amount = position_size(equity, risk_pct, last["close"], sl)

        return {
            "signal": "SELL",
            "entry": last["close"],
            "sl": sl,
            "tp": tp,
            "lot_size": lot_size,
            "risk_usd": risk_amount
        }
