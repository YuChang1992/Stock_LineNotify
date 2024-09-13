# Stock_LineNotify
因為我只購買單一市值型ETF，長期持有的情況下，寫了簡單的低點買進判斷

利用永豐API(Shioaji)提供的即時股票數據，系統定期檢查指定股票的價格變動，根據價格變化的幅度提供交易建議，並透過LINE Notify將到價通知發送給使用者

即時股票數據獲取
● 使用Shioaji API獲取指定股票的即時交易數據，包括當日最高價、最低價、即時價格及昨日收盤價。

數據處理與簡單的低點判斷
● 對獲取的股票數據進行整理和分析，計算當日股價變動和漲跌百分比。
● 當價格跌幅超過設定閾值時，提供買進建議。

自動化檢查與通知
● 使用schedule定期執行檢查函數，確保即時獲取最新股市資訊。
● 當股價變動超過設定閾值時，透過 LINE Notify 發送通知消息。

登出與重啟
● 每完成10次檢查後，自動登出帳號並重啟程式，確保系統持續運行。

參考資料:
https://sinotrade.github.io/zh_TW/
https://github.com/Sinotrade/Shioaji
https://schedule.readthedocs.io/en/stable/index.html