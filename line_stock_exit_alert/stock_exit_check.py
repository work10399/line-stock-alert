import json
import os
import sys
import requests
import yfinance as yf
from datetime import datetime
from zoneinfo import ZoneInfo

HOLDINGS_FILE = "holdings.json"
LOOKBACK_PERIOD = os.getenv("LOOKBACK_PERIOD", "1y")
TAIPEI = ZoneInfo("Asia/Taipei")

def line_push(text: str) -> None:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    to = os.environ["LINE_TO_ID"]
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": to,
        "messages": [{"type": "text", "text": text[:4900]}],
        "notificationDisabled": False
    }
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    r.raise_for_status()

def fetch_close_series(ticker: str):
    df = yf.download(ticker, period=LOOKBACK_PERIOD, interval="1d", auto_adjust=False, progress=False)
    if df.empty and ticker.endswith(".TW"):
        df = yf.download(ticker.replace(".TW", ".TWO"), period=LOOKBACK_PERIOD, interval="1d", auto_adjust=False, progress=False)
    if df.empty and ticker.endswith(".TWO"):
        df = yf.download(ticker.replace(".TWO", ".TW"), period=LOOKBACK_PERIOD, interval="1d", auto_adjust=False, progress=False)
    if df.empty:
        raise RuntimeError(f"{ticker} 抓不到收盤價")
    close = df["Close"].dropna()
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    return close

def judge(stock: dict) -> dict:
    close = fetch_close_series(stock["ticker"])
    latest = float(close.iloc[-1])
    highest = float(close.max())
    cost = float(stock["cost_price"])

    trail_pct = float(stock.get("trail_pct", 8)) / 100
    take_profit_pct = float(stock.get("take_profit_pct", 20)) / 100
    stop_loss_pct = float(stock.get("stop_loss_pct", 10)) / 100

    trail_line = highest * (1 - trail_pct)
    take_profit_line = cost * (1 + take_profit_pct)
    stop_loss_line = cost * (1 - stop_loss_pct)
    pnl_pct = (latest / cost - 1) * 100

    if latest <= stop_loss_line:
        action = "🔴 停損出場"
    elif highest >= take_profit_line and latest <= trail_line:
        action = "🟠 觸發移動停利"
    elif latest >= take_profit_line:
        action = "🟢 已達停利區，續抱但啟動移動停利"
    else:
        action = "⚪ 續抱觀察"

    return {
        "name": stock["name"],
        "ticker": stock["ticker"],
        "latest": latest,
        "highest": highest,
        "cost": cost,
        "shares": int(stock["shares"]),
        "pnl_pct": pnl_pct,
        "trail_line": trail_line,
        "take_profit_line": take_profit_line,
        "stop_loss_line": stop_loss_line,
        "action": action
    }

def main():
    with open(HOLDINGS_FILE, "r", encoding="utf-8") as f:
        holdings = json.load(f)

    now = datetime.now(TAIPEI).strftime("%Y-%m-%d %H:%M")
    results = []
    errors = []

    for stock in holdings:
        try:
            results.append(judge(stock))
        except Exception as e:
            errors.append(f"{stock.get('name')} {stock.get('ticker')}：{e}")

    urgent = [r for r in results if "停損" in r["action"] or "觸發" in r["action"]]
    watch = [r for r in results if r not in urgent]

    lines = [f"📈 持股出場提醒｜{now}", f"檢查區間：{LOOKBACK_PERIOD}", ""]

    if urgent:
        lines.append("🚨 今日需處理")
        for r in urgent:
            lines.append(
                f"{r['name']}({r['ticker']}) {r['action']}\n"
                f"收盤 {r['latest']:.2f}｜成本 {r['cost']:.2f}｜損益 {r['pnl_pct']:.1f}%\n"
                f"移停線 {r['trail_line']:.2f}｜停損線 {r['stop_loss_line']:.2f}"
            )
            lines.append("")
    else:
        lines.append("✅ 今日沒有觸發出場")
        lines.append("")

    lines.append("📌 觀察清單")
    for r in sorted(watch, key=lambda x: x["pnl_pct"], reverse=True):
        lines.append(
            f"{r['name']} {r['pnl_pct']:.1f}%｜收 {r['latest']:.2f}｜{r['action']}"
        )

    if errors:
        lines.append("")
        lines.append("⚠️ 抓價失敗")
        lines.extend(errors)

    message = "\n".join(lines)
    print(message)

    if os.getenv("LINE_CHANNEL_ACCESS_TOKEN") and os.getenv("LINE_TO_ID"):
        line_push(message)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程式失敗：{e}", file=sys.stderr)
        raise
