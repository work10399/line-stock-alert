import json
import os
import sys
import smtplib
import yfinance as yf
from datetime import datetime
from zoneinfo import ZoneInfo
from email.mime.text import MIMEText

HOLDINGS_FILE = "holdings.json"
LOOKBACK_PERIOD = os.getenv("LOOKBACK_PERIOD", "1y")
TAIPEI = ZoneInfo("Asia/Taipei")

def send_gmail(subject: str, body: str) -> None:
    gmail_user = os.environ["GMAIL_USER"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    mail_to = os.environ["MAIL_TO"]

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = mail_to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_app_password)
        server.send_message(msg)

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
    market_value = latest * int(stock.get("shares", 0))
    cost_value = cost * int(stock.get("shares", 0))
    unrealized = market_value - cost_value

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
        "shares": int(stock.get("shares", 0)),
        "pnl_pct": pnl_pct,
        "market_value": market_value,
        "unrealized": unrealized,
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

    total_value = sum(r["market_value"] for r in results)
    total_unrealized = sum(r["unrealized"] for r in results)

    lines = [
        f"持股出場提醒｜{now}",
        f"檢查區間：{LOOKBACK_PERIOD}",
        f"目前總市值：約 {total_value:,.0f} 元",
        f"未實現損益：約 {total_unrealized:,.0f} 元",
        ""
    ]

    if urgent:
        lines.append("【今日需處理】")
        for r in urgent:
            lines.append(
                f"{r['name']} ({r['ticker']})｜{r['action']}\n"
                f"收盤 {r['latest']:.2f}｜成本 {r['cost']:.2f}｜損益 {r['pnl_pct']:.1f}%\n"
                f"最高收盤 {r['highest']:.2f}｜移停線 {r['trail_line']:.2f}｜停損線 {r['stop_loss_line']:.2f}\n"
            )
    else:
        lines.append("【今日需處理】")
        lines.append("沒有觸發停損或移動停利。")
        lines.append("")

    lines.append("【觀察清單】")
    for r in sorted(watch, key=lambda x: x["pnl_pct"], reverse=True):
        lines.append(
            f"{r['name']}｜{r['pnl_pct']:.1f}%｜收盤 {r['latest']:.2f}｜{r['action']}"
        )

    if errors:
        lines.append("")
        lines.append("【抓價失敗】")
        lines.extend(errors)

    body = "\n".join(lines)
    print(body)

    if os.getenv("GMAIL_USER") and os.getenv("GMAIL_APP_PASSWORD") and os.getenv("MAIL_TO"):
        send_gmail("每日持股停利/出場提醒", body)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程式失敗：{e}", file=sys.stderr)
        raise
