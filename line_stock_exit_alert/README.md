# LINE 台股移動停利提醒

## 使用方式

1. 到 LINE Developers 建立 Messaging API Channel，取得 Channel access token。
2. 讓你的 LINE 官方帳號加你好友。
3. 取得你的 userId，填到 GitHub Secrets。
4. GitHub Repository Settings > Secrets and variables > Actions 新增：
   - LINE_CHANNEL_ACCESS_TOKEN
   - LINE_TO_ID
5. 上傳本專案到 GitHub。
6. Actions 會在台灣時間週一到週五 08:30 自動執行。

## 調整持股

修改 `holdings.json`：
- `cost_price`：成本價
- `shares`：股數
- `trail_pct`：從最高收盤價回落幾 % 觸發移動停利
- `take_profit_pct`：漲幾 % 後啟動移動停利
- `stop_loss_pct`：跌幾 % 停損

## 注意

這是紀律提醒工具，不是投資建議。
