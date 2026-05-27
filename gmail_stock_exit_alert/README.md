# Gmail 台股移動停利提醒

每天台灣時間週一到週五 08:30，GitHub Actions 會自動執行，並寄 Gmail 給你。

## GitHub Secrets 需要設定

- GMAIL_USER：寄件 Gmail，例如 yourname@gmail.com
- GMAIL_APP_PASSWORD：Gmail 應用程式密碼，不是 Gmail 登入密碼
- MAIL_TO：收件信箱，可以跟 GMAIL_USER 一樣

## 調整持股

修改 `holdings.json`。

## 測試

GitHub repo > Actions > Daily Gmail Stock Exit Alert > Run workflow。
