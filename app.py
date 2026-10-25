import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import ta
import time

# Seitenkonfiguration
st.set_page_config(
    page_title="BTC AI Paper Trader",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS für etwas schöneres Design
st.markdown("""
<style>
    .main-header {font-size: 2.2rem; font-weight: 700; color: #F7931A;}
    .metric-card {background-color: #1E1E1E; padding: 1rem; border-radius: 10px;}
    .warning-box {background-color: #3D1F00; border-left: 5px solid #F7931A; padding: 1rem; margin-bottom: 1rem;}
</style>
""", unsafe_allow_html=True)

# ==================== Hilfsfunktionen ====================

@st.cache_data(ttl=60)
def get_btc_data(period="60d", interval="1h"):
    """Holt BTC-USD Daten von Yahoo Finance"""
    try:
        df = yf.download("BTC-USD", period=period, interval=interval, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        return df
    except Exception as e:
        st.error(f"Fehler beim Laden der Kursdaten: {e}")
        return pd.DataFrame()

def add_indicators(df):
    """Fügt technische Indikatoren hinzu"""
    if df.empty:
        return df
    df = df.copy()
    df["SMA20"] = ta.trend.sma_indicator(df["Close"], window=20)
    df["SMA50"] = ta.trend.sma_indicator(df["Close"], window=50)
    df["RSI"] = ta.momentum.rsi(df["Close"], window=14)
    df["EMA12"] = ta.trend.ema_indicator(df["Close"], window=12)
    df["EMA26"] = ta.trend.ema_indicator(df["Close"], window=26)
    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["Signal"] = ta.trend.sma_indicator(df["MACD"], window=9)
    return df

def generate_signal(row, rsi_buy=35, rsi_sell=65):
    """Einfache regelbasierte 'KI'-Entscheidung"""
    if pd.isna(row["RSI"]) or pd.isna(row["SMA20"]) or pd.isna(row["SMA50"]):
        return "HOLD"
    
    # Buy-Bedingungen: Überverkauft + Aufwärtstrend
    if (row["RSI"] < rsi_buy and 
        row["Close"] > row["SMA20"] and 
        row["SMA20"] > row["SMA50"]):
        return "BUY"
    
    # Sell-Bedingungen: Überkauft oder Trendbruch
    if row["RSI"] > rsi_sell or row["Close"] < row["SMA20"]:
        return "SELL"
    
    return "HOLD"

def initialize_session_state():
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = {
            "cash": 10000.0,
            "btc": 0.0,
            "initial_capital": 10000.0,
            "trades": [],
            "last_signal": "HOLD",
            "last_price": 0.0,
            "running": False
        }

def execute_trade(signal, price, risk_pct):
    """Führt einen Paper-Trade aus"""
    port = st.session_state.portfolio
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if signal == "BUY" and port["cash"] > 50:
        # Wie viel Kapital einsetzen?
        invest_amount = port["cash"] * (risk_pct / 100.0)
        btc_to_buy = invest_amount / price
        
        if btc_to_buy > 0:
            port["btc"] += btc_to_buy
            port["cash"] -= invest_amount
            port["trades"].append({
                "time": timestamp,
                "type": "BUY",
                "price": price,
                "amount_btc": btc_to_buy,
                "value_usd": invest_amount,
                "signal": signal
            })
            return True
    
    elif signal == "SELL" and port["btc"] > 0.0001:
        # Alles verkaufen (einfache Strategie)
        sell_value = port["btc"] * price
        port["trades"].append({
            "time": timestamp,
            "type": "SELL",
            "price": price,
            "amount_btc": port["btc"],
            "value_usd": sell_value,
            "signal": signal
        })
        port["cash"] += sell_value
        port["btc"] = 0.0
        return True
    
    return False

# ==================== Haupt-App ====================

def main():
    initialize_session_state()
    
    st.markdown('<p class="main-header">₿ BTC AI Paper Trader</p>', unsafe_allow_html=True)
    
    # Warnung
    st.markdown("""
    <div class="warning-box">
        <strong>⚠️ WICHTIG:</strong> Dies ist eine reine Simulation mit Spielgeld. 
        Es wird kein echtes Bitcoin gehandelt. Keine Gewinn-Garantie. 
        Trading birgt das Risiko des Totalverlusts.
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar – Einstellungen
    with st.sidebar:
        st.header("⚙️ Einstellungen")
        
        st.subheader("Kapital")
        initial_capital = st.number_input(
            "Startkapital (USD)",
            min_value=100.0,
            max_value=1_000_000.0,
            value=float(st.session_state.portfolio["initial_capital"]),
            step=100.0,
            help="Virtuelles Startkapital für die Simulation"
        )
        
        if st.button("Kapital zurücksetzen", use_container_width=True):
            st.session_state.portfolio = {
                "cash": initial_capital,
                "btc": 0.0,
                "initial_capital": initial_capital,
                "trades": [],
                "last_signal": "HOLD",
                "last_price": 0.0,
                "running": False
            }
            st.success("Portfolio zurückgesetzt!")
            st.rerun()
        
        st.divider()
        
        st.subheader("Strategie-Parameter")
        risk_pct = st.slider(
            "Risiko pro Trade (%)",
            min_value=5,
            max_value=100,
            value=25,
            help="Wie viel Prozent des aktuellen Cash pro Kauf eingesetzt werden"
        )
        
        rsi_buy = st.slider("RSI Kauf-Schwelle", 20, 45, 35)
        rsi_sell = st.slider("RSI Verkauf-Schwelle", 55, 80, 65)
        
        st.divider()
        
        auto_trade = st.toggle("Automatisch traden", value=st.session_state.portfolio.get("running", False))
        st.session_state.portfolio["running"] = auto_trade
        
        refresh_interval = st.selectbox("Auto-Refresh (Sekunden)", [30, 60, 120, 300], index=1)
        
        st.divider()
        st.caption("Strategie: RSI + SMA20/SMA50 (regelbasiert)")
        st.caption("Datenquelle: Yahoo Finance (BTC-USD)")
    
    # Daten laden
    with st.spinner("Kursdaten werden geladen..."):
        df = get_btc_data(period="90d", interval="1h")
    
    if df.empty:
        st.error("Keine Kursdaten verfügbar. Bitte später erneut versuchen.")
        return
    
    df = add_indicators(df)
    latest = df.iloc[-1]
    current_price = float(latest["Close"])
    st.session_state.portfolio["last_price"] = current_price
    
    # Signal generieren
    signal = generate_signal(latest, rsi_buy=rsi_buy, rsi_sell=rsi_sell)
    st.session_state.portfolio["last_signal"] = signal
    
    # Automatisch traden wenn aktiviert
    if auto_trade:
        traded = execute_trade(signal, current_price, risk_pct)
        if traded:
            st.toast(f"Trade ausgeführt: {signal} @ ${current_price:,.2f}", icon="✅")
    
    # Portfolio-Werte berechnen
    port = st.session_state.portfolio
    btc_value = port["btc"] * current_price
    total_value = port["cash"] + btc_value
    pnl = total_value - port["initial_capital"]
    pnl_pct = (pnl / port["initial_capital"]) * 100 if port["initial_capital"] > 0 else 0
    
    # ==================== Metriken ====================
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Aktueller BTC-Preis", f"${current_price:,.2f}")
    with col2:
        st.metric("Gesamtwert", f"${total_value:,.2f}", delta=f"{pnl_pct:+.2f}%")
    with col3:
        st.metric("Cash", f"${port['cash']:,.2f}")
    with col4:
        st.metric("BTC Bestand", f"{port['btc']:.6f}")
    with col5:
        color = "normal" if signal == "HOLD" else ("inverse" if signal == "SELL" else "off")
        st.metric("Aktuelles Signal", signal)
    
    # ==================== Chart ====================
    st.subheader("📈 Kurschart + Indikatoren")
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=("BTC-USD", "RSI")
    )
    
    # Kerzenchart
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="BTC"
    ), row=1, col=1)
    
    # SMAs
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA20", line=dict(color="orange", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA50", line=dict(color="blue", width=1)), row=1, col=1)
    
    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", line=dict(color="purple")), row=2, col=1)
    fig.add_hline(y=rsi_buy, line_dash="dash", line_color="green", row=2, col=1)
    fig.add_hline(y=rsi_sell, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="gray", row=2, col=1)
    
    fig.update_layout(
        height=600,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        showlegend=True,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    fig.update_yaxes(title_text="Preis (USD)", row=1, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ==================== Trade-Historie ====================
    st.subheader("📋 Trade-Historie")
    
    if port["trades"]:
        trades_df = pd.DataFrame(port["trades"])
        trades_df = trades_df.iloc[::-1]  # Neueste zuerst
        st.dataframe(
            trades_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "time": "Zeit",
                "type": "Typ",
                "price": st.column_config.NumberColumn("Preis", format="$%.2f"),
                "amount_btc": st.column_config.NumberColumn("BTC Menge", format="%.6f"),
                "value_usd": st.column_config.NumberColumn("Wert USD", format="$%.2f"),
                "signal": "Signal"
            }
        )
        
        # Einfache Statistik
        buys = [t for t in port["trades"] if t["type"] == "BUY"]
        sells = [t for t in port["trades"] if t["type"] == "SELL"]
        st.caption(f"Anzahl Trades: {len(port['trades'])}  |  Käufe: {len(buys)}  |  Verkäufe: {len(sells)}")
    else:
        st.info("Noch keine Trades ausgeführt. Aktiviere 'Automatisch traden' oder warte auf ein Signal.")
    
    # Manueller Trade-Button
    st.subheader("Manuelle Aktion")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("Jetzt KAUFEN (nach Strategie)", use_container_width=True):
            if execute_trade("BUY", current_price, risk_pct):
                st.success("Kauf ausgeführt!")
                st.rerun()
            else:
                st.warning("Kauf nicht möglich (zu wenig Cash oder Bedingungen nicht erfüllt).")
    with col_b:
        if st.button("Jetzt VERKAUFEN", use_container_width=True):
            if execute_trade("SELL", current_price, risk_pct):
                st.success("Verkauf ausgeführt!")
                st.rerun()
            else:
                st.warning("Kein BTC zum Verkaufen vorhanden.")
    with col_c:
        if st.button("Nur Signal aktualisieren", use_container_width=True):
            st.rerun()
    
    # Auto-Refresh
    if auto_trade:
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()
