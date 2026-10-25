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

@st.cache_data(ttl=30)
def get_btc_data():
    """Holt aktuelle BTC-Daten"""
    try:
        df = yf.download("BTC-USD", period="14d", interval="1h", progress=False)
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

def get_signal(row, has_position: bool):
    """
    Aggressivere Logik:
    - Wenn noch keine Position: leichter kaufen
    - Wenn Position offen: leichter verkaufen
    """
    if pd.isna(row["RSI"]) or pd.isna(row["SMA10"]):
        return "HOLD"
    
    rsi = float(row["RSI"])
    close = float(row["Close"])
    sma10 = float(row["SMA10"])
    
    if not has_position:
        # Noch kein BTC → möglichst schnell eine Position eröffnen
        if rsi < 55 or close > sma10:
            return "BUY"
        return "HOLD"
    else:
        # Position ist offen → eher verkaufen
        if rsi > 52 or close < sma10:
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

def do_trade(signal, price):
    """Führt einen Trade aus und speichert ihn"""
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    if signal == "BUY" and st.session_state.cash > 50 and st.session_state.btc < 0.0001:
        # 50% des Kapitals einsetzen
        amount = st.session_state.cash * 0.50
        btc_amount = amount / price
        
        st.session_state.btc += btc_amount
        st.session_state.cash -= amount
        
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
        return True
    
    return False

# ==================== Haupt-App ====================

def main():
    init_state()
    
    st.title("₿ BTC Auto Trader")
    st.caption("Nur Simulation · Kein echtes Geld")
    
    # ---------- Startbildschirm ----------
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
            st.session_state.started = True
            st.rerun()
        
        st.info("Nach dem Start entscheidet das Programm selbst, wann es kauft und verkauft.")
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
    
    has_position = st.session_state.btc > 0.0001
    signal = get_signal(latest, has_position)
    
    # Automatisch traden
    traded = do_trade(signal, price)
    
    # Nach dem Trade Status neu berechnen
    has_position = st.session_state.btc > 0.0001
    btc_value = st.session_state.btc * price
    total = st.session_state.cash + btc_value
    pnl = total - st.session_state.initial
    pnl_pct = (pnl / st.session_state.initial * 100) if st.session_state.initial > 0 else 0
    
    # Status
    col1, col2, col3 = st.columns(3)
    col1.metric("Aktueller Stand", f"${total:,.2f}", f"{pnl_pct:+.2f}%")
    col2.metric("BTC-Preis", f"${price:,.2f}")
    col3.metric("Aktuelles Signal", signal)
    
    # Klare Erklärung, warum gerade nichts passiert
    if signal == "SELL" and not has_position:
        st.warning("Signal ist **SELL**, aber es ist noch keine Position offen. Das Programm wartet auf ein **KAUF**-Signal.")
    elif signal == "BUY" and has_position:
        st.info("Signal ist **BUY**, aber es ist bereits eine Position offen.")
    elif signal == "HOLD":
        st.info("Aktuell kein klares Signal → HOLD")
    elif traded:
        st.success(f"Trade gerade ausgeführt: **{signal}**")
    
    st.divider()
    
    # Trades anzeigen
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
        st.info("Noch keine Trades ausgeführt.")
    
    st.divider()
    
    if st.button("Trading stoppen & zurücksetzen", use_container_width=True):
        st.session_state.started = False
        st.session_state.trades = []
        st.rerun()
    
    # Alle 30 Sekunden neu prüfen
    time.sleep(30)
    st.rerun()

if __name__ == "__main__":
    main()
