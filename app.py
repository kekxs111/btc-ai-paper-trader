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

def get_signal_and_size(row, cash, btc, price):
    """
    Entscheidet Signal + angemessene Positionsgröße.
    Gibt zurück: (signal, size_usd, size_btc)
    """
    if pd.isna(row["RSI"]) or pd.isna(row["SMA10"]):
        return "HOLD", 0.0, 0.0
    
    rsi = float(row["RSI"])
    close = float(row["Close"])
    sma10 = float(row["SMA10"])
    has_position = btc > 0.0001
    portfolio_value = cash + (btc * price)
    
    # ----- KAUF-Logik -----
    if rsi < 58 and close > sma10 * 0.998:
        # Je niedriger der RSI, desto größer die Position (aber begrenzt)
        if rsi < 35:
            risk_pct = 0.22          # stark überverkauft → mehr einsetzen
        elif rsi < 45:
            risk_pct = 0.15
        else:
            risk_pct = 0.10          # nur leichtes Signal → kleiner
        
        # Maximal 25% des Gesamtportfolios pro Einzeltrade
        max_trade = portfolio_value * 0.25
        size_usd = min(cash * risk_pct, max_trade, cash * 0.95)
        
        if size_usd > 30:  # Mindestgröße
            size_btc = size_usd / price
            return "BUY", size_usd, size_btc
    
    # ----- VERKAUF-Logik -----
    if has_position and (rsi > 52 or close < sma10):
        # Je höher der RSI / je schwächer der Kurs, desto mehr verkaufen
        if rsi > 70 or close < sma10 * 0.99:
            sell_pct = 1.0           # alles verkaufen
        elif rsi > 60:
            sell_pct = 0.60
        else:
            sell_pct = 0.35          # nur Teilverkauf
        
        size_btc = btc * sell_pct
        size_usd = size_btc * price
        
        if size_btc > 0.00005:
            return "SELL", size_usd, size_btc
    
    return "HOLD", 0.0, 0.0

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

def do_trade(signal, size_usd, size_btc, price):
    """Führt den Trade mit der vom Programm bestimmten Größe aus"""
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    if signal == "BUY" and size_usd > 30 and st.session_state.cash >= size_usd:
        st.session_state.btc += size_btc
        st.session_state.cash -= size_usd
        
        st.session_state.trades.append({
            "Zeit": timestamp,
            "Aktion": "KAUF",
            "Preis": round(price, 2),
            "BTC": round(size_btc, 6),
            "Wert USD": round(size_usd, 2)
        })
        return True
    
    elif signal == "SELL" and size_btc > 0.00005 and st.session_state.btc >= size_btc:
        st.session_state.btc -= size_btc
        st.session_state.cash += size_usd
        
        # Aufräumen bei sehr kleinen Resten
        if st.session_state.btc < 0.00005:
            st.session_state.cash += st.session_state.btc * price
            st.session_state.btc = 0.0
        
        st.session_state.trades.append({
            "Zeit": timestamp,
            "Aktion": "VERKAUF",
            "Preis": round(price, 2),
            "BTC": round(size_btc, 6),
            "Wert USD": round(size_usd, 2)
        })
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
        
        st.info("Das Programm entscheidet selbst, wann und mit wie viel Geld es kauft oder verkauft. Mehrere Trades sind möglich.")
        return
    
    # ---------- Trading läuft ----------
    
    df = get_btc_data()
    if df.empty:
        st.error("Kursdaten konnten nicht geladen werden. Bitte Seite neu laden.")
        return
    
    df = add_indicators(df)
    latest = df.iloc[-1]
    price = float(latest["Close"])
    
    signal, size_usd, size_btc = get_signal_and_size(
        latest, 
        st.session_state.cash, 
        st.session_state.btc, 
        price
    )
    
    # Trade ausführen
    traded = do_trade(signal, size_usd, size_btc, price)
    
    # Aktuellen Stand berechnen
    btc_value = st.session_state.btc * price
    total = st.session_state.cash + btc_value
    pnl = total - st.session_state.initial
    pnl_pct = (pnl / st.session_state.initial * 100) if st.session_state.initial > 0 else 0
    
    # Status
    col1, col2, col3 = st.columns(3)
    col1.metric("Aktueller Stand", f"${total:,.2f}", f"{pnl_pct:+.2f}%")
    col2.metric("BTC-Preis", f"${price:,.2f}")
    col3.metric("Aktuelles Signal", signal)
    
    # Zusätzliche Info
    col_a, col_b = st.columns(2)
    col_a.write(f"Cash: **${st.session_state.cash:,.2f}**")
    col_b.write(f"BTC Bestand: **{st.session_state.btc:.6f}**")
    
    if traded:
        st.success(f"Trade ausgeführt: **{signal}** über ${size_usd:,.2f}")
    elif signal == "HOLD":
        st.info("Aktuell kein klares Signal → HOLD")
    else:
        st.caption(f"Signal erkannt, aber Bedingungen für Ausführung nicht erfüllt (z. B. zu wenig Cash oder Position).")
    
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
    
    time.sleep(30)
    st.rerun()

if __name__ == "__main__":
    main()
