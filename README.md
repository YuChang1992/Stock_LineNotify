# Stock_LineNotify
在這通膨的時代，幣值持續縮水，僅靠收入已經不夠了，投資成為提升財富的重要途徑之一。
利用股票數據評估長短期趨勢，並透過排程設置到價通知，定期回傳交易建議。

利用永豐API (Shioaji) 提供的即時股票數據，定期檢查指定股票的價格變動。通過數據處理，計算短期和長期的EMA、MACD等指標，以評估股票趨勢。當股價變動超過設定幅度時，系統會自動透過LINE Notify發送通知，讓使用者定期收到最新的交易建議，從而把握投資機會。

計算當日下跌金額、連續下跌天數、累積下跌幅度，提供交易建議。
計算短期和長期EMA、MACD、信號線及直方圖，分析直方圖和MACD的交叉情況，提供交易建議。

參考資料:
https://sinotrade.github.io/zh_TW/
https://github.com/Sinotrade/Shioaji
https://schedule.readthedocs.io/en/stable/index.html