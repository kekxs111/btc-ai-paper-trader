# BTC AI Paper Trader (Streamlit)

**Nur Paper-Trading / Simulation – kein echtes Geld!**

Eine einfache Streamlit-App, mit der du einen virtuellen Geldbetrag festlegst und eine regelbasierte "KI"-Strategie automatisch Bitcoin traden lässt.

## Wichtige Warnung

- Dies ist **kein** Finanzprodukt und **kein** Tipp.
- Die Strategie ist bewusst einfach und transparent (RSI + Moving Averages).
- Es gibt **keine Gewinn-Garantie**. Die meisten Trading-Bots verlieren langfristig Geld.
- Streamlit ist nicht für 24/7-Live-Trading geeignet.
- Bei echtem Trading riskierst du den Totalverlust deines Kapitals.

## Features

- Einstellbarer Start-Kapitalbetrag
- Regelbasierte Strategie ("KI"):
  - RSI (Relative Strength Index)
  - SMA 20 / SMA 50
  - Einfache Buy/Sell-Signale mit Risikomanagement
- Virtuelles Portfolio (Cash + BTC)
- Live-Kurs von Yahoo Finance
- Trade-Historie + P&L
- Interaktiver Chart
- Auto-Refresh (Simulation)

## Lokal starten

```bash
git clone https://github.com/kekxs111/btc-ai-paper-trader.git
cd btc-ai-paper-trader
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud

1. Gehe zu [share.streamlit.io](https://share.streamlit.io)
2. Verbinde dein GitHub-Konto
3. Wähle dieses Repository und die Datei `app.py`
4. Deployen

## Strategie (vereinfacht)

- **Buy**: RSI < 35 und Kurs über SMA20 und SMA20 > SMA50 (Aufwärtstrend + überverkauft)
- **Sell**: RSI > 65 oder Kurs unter SMA20
- Positionsgröße: max. X % des aktuellen Kapitals pro Trade (einstellbar)
- Kein Leverage, nur Spot-Long

## Disclaimer

Diese App dient ausschließlich zu Bildungs- und Demonstrationszwecken. Der Autor übernimmt keinerlei Haftung für Verluste, die durch die Nutzung oder Weiterentwicklung entstehen.
