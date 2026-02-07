import ccxt
import pandas as pd
import requests
import time
from datetime import datetime, timezone

# ===============================
# 🔴 YOUR TELEGRAM DETAILS
# ===============================
TOKEN = "8364584748:AAFeym3et4zJwmdKRxYtP3ieIKV8FuPWdQ8"
CHAT_ID = "@Tradecocom"

# ===============================
# SETTINGS
# ===============================
PAIRS = ["BTC/USDT", "ETH/USDT", "BNB", "SOL/USDT"]

TIMEFRAMES = ["5m", "15m", "30m", "1h", "4h", "1d"]

EMA_FAST = 20
EMA_SLOW = 50
SWING_LOOKBACK = 15

exchange = ccxt.bybit({
    "enableRateLimit": True,
    "options": {
        "defaultType": "spot"
    }
})


last_alert = {}  # prevents duplicate alerts

# ===============================
# TELEGRAM MESSAGE
# ===============================
def send_alert(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=data)

# ===============================
# FETCH DATA
# ===============================
def get_data(symbol, timeframe):
    candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
    df = pd.DataFrame(candles, columns=["time", "open", "high", "low", "close", "volume"])
    return df

# ===============================
# SIGNAL CHECK
# ===============================
def check_signal(symbol, timeframe):
    df = get_data(symbol, timeframe)

    df["ema20"] = df["close"].ewm(span=EMA_FAST).mean()
    df["ema50"] = df["close"].ewm(span=EMA_SLOW).mean()

    prev_fast = df["ema20"].iloc[-2]
    prev_slow = df["ema50"].iloc[-2]
    curr_fast = df["ema20"].iloc[-1]
    curr_slow = df["ema50"].iloc[-1]

    price = df["close"].iloc[-1]

    swing_high = df["high"].iloc[-SWING_LOOKBACK:].max()
    swing_low = df["low"].iloc[-SWING_LOOKBACK:].min()

    signal = None

    if prev_fast < prev_slow and curr_fast > curr_slow:
        signal = "🟢 BUY | EMA 20 Cross Above EMA 50"

    elif prev_fast > prev_slow and curr_fast < curr_slow:
        signal = "🔴 SELL | EMA 20 Cross Below EMA 50"

    elif price > swing_high:
        signal = "🚀 BULLISH BREAKOUT | Swing High Broken"

    elif price < swing_low:
        signal = "🩸 BEARISH BREAKDOWN | Swing Low Broken"

    if signal:
        key = f"{symbol}_{timeframe}_{signal}"
        if last_alert.get(key) != df["time"].iloc[-1]:
            last_alert[key] = df["time"].iloc[-1]

            message = (
                f"{signal}\n\n"
                f"📊 Pair: {symbol}\n"
                f"⏱ Timeframe: {timeframe}\n"
                f"💰 Price: {price}\n"
                f"🕒 UTC: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
            )
            send_alert(message)
            return True

    return False

# ===============================
# MAIN LOOP (ONE SIGNAL PER 5 MIN)
# ===============================
print("🚀 TradingCo Signal Bot Started")

while True:
    try:
        sent = False

        for pair in PAIRS:
            for tf in TIMEFRAMES:
                if check_signal(pair, tf):
                    sent = True
                    break
            if sent:
                break

        time.sleep(300)  # 5 minutes

    except Exception as e:
        print("Error:", e)
        time.sleep(60)
