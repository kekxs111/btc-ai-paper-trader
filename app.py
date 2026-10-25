import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import ta
import time

st.set_page_config(
    page_title="BTC Auto Trader",
    page_icon="₿",
    layout="centered"
)

# ==================== Daten & Strategie ====================

@st.cache_data(ttl=45)
def get_btc_data():
    """Holt aktuelle BTC-Daten"""
    try:
        df = yf.download("BTC-USD", period="30d", interval="1h", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        return df
    except Exception:
        return pd.DataFrame()

def add_indicators(df):
    df = df.copy()
    df["SMA10"] = ta.trend.sma_indicator(df["Close"], window=10)
    df["SMA20"] = ta.trend.sma_indicator(df["Close"], window=20)
    df["RSI"] = ta.momentum.rsi(df["Close"], window=14)
    return df

def get_signal(row):
    """Aggressivere regelbasierte Entscheidung – häufigere Signale"""
    if pd.isna(row["RSI"]) or pd.isna(row["SMA10"]) or pd.isna(row["SMA20"]):
        return "HOLD"
    
    rsi = row["RSI"]
    close = row["Close"]
    sma10 = row["SMA10"]
    sma20 = row["SMA20"]
    
    # KAUF: häufiger – RSI unter 48 oder Kurs über SMA10 bei leichtem Aufwärtstrend
    if rsi < 48 and close > sma10:
        return "BUY"
    
    # VERKAUF: häufiger – RSI über 55 oder Kurs unter SMA10
    if rsi > 55 or close < sma10:
        return "SELL"
    
    return "HOLD"

# ==================== Session State ====================

def init_state():
    if "started" not in st.session_state:
        st.session_state.started = False
    if "cash" not in st.session_state:
        st.session_state.cash = 0.0
    if "btc" not in st.session_state:
        st.session_state.btc = 0.0
    if "initial" not in st.session_state:
        st.session_state.initial = 0.0
    if "trades" not in st.session_state:
        st.session_state.trades = []
    if "last_price" not in st.session_state:
        st.session_state.last_price = 0.0
    if "last_action" not in st.session_state:
        st.session_state.last_action = None

def do_trade(signal, price):
    """Führt einen Trade aus und speichert ihn"""
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    # Verhindert doppelte Käufe hintereinander ohne Verkauf
    if signal == "BUY" and st.session_state.cash > 50 and st.session_state.last_action != "BUY":
        # 40% des aktuellen Cash einsetzen (etwas aggressiver)
        amount = st.session_state.cash * 0.40
        btc_amount = amount / price
        
        st.session_state.btc += btc_amount
        st.session_state.cash -= amount
        st.session_state.last_action = "BUY"
        
        st.session_state.trades.append({
            "Zeit": timestamp,
            "Aktion": "KAUF",
            "Preis": round(price, 2),
            "BTC": round(btc_amount, 6),
            "Wert USD": round(amount, 2)
        })
        return True
    
    elif signal == "SELL" and st.session_state.btc > 0.0001:
        value = st.session_state.btc * price
        
        st.session_state.trades.append({
            "Zeit": timestamp,
            "Aktion": "VERKAUF",
            "Preis": round(price, 2),
            "BTC": round(st.session_state.btc, 6),
            "Wert USD": round(value, 2)
        })
        
        st.session_state.cash += value
        st.session_state.btc = 0.0
        st.session_state.last_action = "SELL"
        return True
    
    return False

# ==================== Haupt-App ====================

def main():
    init_state()
    
    st.title("₿ BTC Auto Trader")
    st.caption("Nur Simulation · Kein echtes Geld · Häufigere Signale")
    
    # ---------- Startbildschirm: Nur Kapital einstellen ----------
    if not st.session_state.started:
        st.markdown("### Wie viel Geld soll eingesetzt werden?")
        
        capital = st.number_input(
            "Startkapital in USD",
            min_value=100,
            max_value=1000000,
            value=1000,
            step=100,
            label_visibility="collapsed"
        )
        
        st.write("")
        if st.button("Trading starten", type="primary", use_container_width=True):
            st.session_state.cash = float(capital)
            st.session_state.btc = 0.0
            st.session_state.initial = float(capital)
            st.session_state.trades = []
            st.session_state.last_action = None
            st.session_state.started = True
            st.rerun()
        
        st.info("Nach dem Start entscheidet das Programm selbst, wann es kauft und verkauft. Du siehst nur die ausgeführten Trades.")
        return
    
    # ---------- Trading läuft ----------
    
    df = get_btc_data()
    if df.empty:
        st.error("Kursdaten konnten nicht geladen werden. Bitte Seite neu laden.")
        return
    
    df = add_indicators(df)
    latest = df.iloc[-1]
    price = float(latest["Close"])
    st.session_state.last_price = price
    
    signal = get_signal(latest)
    
    # Automatisch traden
    traded = do_trade(signal, price)
    
    # Aktuellen Stand berechnen
    btc_value = st.session_state.btc * price
    total = st.session_state.cash + btc_value
    pnl = total - st.session_state.initial
    pnl_pct = (pnl / st.session_state.initial * 100) if st.session_state.initial > 0 else 0
    
    # Kurzer Status oben
    col1, col2, col3 = st.columns(3)
    col1.metric("Aktueller Stand", f"${total:,.2f}", f"{pnl_pct:+.2f}%")
    col2.metric("BTC-Preis", f"${price:,.2f}")
    col3.metric("Aktuelles Signal", signal)
    
    st.divider()
    
    # ---------- Nur die Trades anzeigen ----------
    st.subheader("Ausgeführte Trades")
    
    if st.session_state.trades:
        trades_df = pd.DataFrame(st.session_state.trades)
        trades_df = trades_df.iloc[::-1].reset_index(drop=True)
        
        st.dataframe(
            trades_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Zeit": "Zeit",
                "Aktion": "Aktion",
                "Preis": st.column_config.NumberColumn("Preis", format="$%.2f"),
                "BTC": st.column_config.NumberColumn("BTC", format="%.6f"),
                "Wert USD": st.column_config.NumberColumn("Wert", format="$%.2f")
            }
        )
        
        st.caption(f"Anzahl Trades: {len(st.session_state.trades)}")
    else:
        st.info("Noch keine Trades. Das Programm wartet auf ein Signal...")
    
    st.divider()
    
    if st.button("Trading stoppen & zurücksetzen", use_container_width=True):
        st.session_state.started = False
        st.session_state.trades = []
        st.session_state.last_action = None
        st.rerun()
    
    # Alle 40 Sekunden neu prüfen
    time.sleep(40)
    st.rerun()

if __name__ == "__main__":
    main()
