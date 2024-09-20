import shioaji as sj  # Shioaji永豐的API客戶端
import requests  # 獲取網頁套件
from datetime import date, timedelta, datetime  # 處理日期和時間
import time  # 控制程式的延遲
import schedule  # 定期執行函數
import pandas as pd  # 數據處理和分析的庫
import random  # 亂數
import subprocess  # 創建和管理子進程
import sys  # 對Python直譯器訪問


# API Key 和 Secret Key
API_KEY = "你的 API KEY"
SECRET_KEY = "你的 SECRET KEY"

# 股票代碼
STOCK_CODE = "股票代號"

def initialize_api():
    global api, accounts
    api = sj.Shioaji(simulation=True)
    accounts = api.login(API_KEY, SECRET_KEY)
    if len(accounts) == 0:
        raise ValueError("未找到帳戶")


def truncate_to_two_decimal_places(value):
    return float(f"{value:.2f}")


# 取得個股即時資訊
def get_now_stock():
    global api

    # 設定日期範圍
    delta = timedelta(days=60)
    start_day = date.today() - delta  # 開始日期為60天前
    end_day = date.today()  # 結束日期今天
    
    stock = api.Contracts.Stocks[STOCK_CODE]

    kbars = api.kbars(contract=stock, start=str(start_day), end=str(end_day))
    df = pd.DataFrame({**kbars})
    df.ts = pd.to_datetime(df.ts)
    df.set_index("ts", inplace=True)

    daily_low = df['Low'].resample('D').min().dropna()    # 每日最低價格
    daily_high = df['High'].resample('D').max().dropna()  # 每日最高價格
    daily_Close = df['Close'].resample("D").last().dropna()  # 每日最後一筆交易價格

    consecutive_drops, drop_percentage = calculate_consecutive_drops(daily_Close)  # 計算連續下跌天數及下跌百分比
    
    name = stock.name  # 股票名稱
    code = stock.code  # 股票代碼
    today_low = daily_low.iloc[-1]  # 當日最低
    today_high = daily_high.iloc[-1]  # 當日最高
    yesterday_hist = daily_Close.iloc[-2]  # 倒數第二筆資料，昨日收盤價
    today_hist = daily_Close.iloc[-1]  # 倒數第一筆資料，即時售價
    time = df.index[-1]  # 最後一筆交易日期時間
    
    up_down = today_hist - yesterday_hist  # 漲跌
    up_down_float = truncate_to_two_decimal_places(up_down)
    percentage = (up_down / yesterday_hist) * 100  # 漲跌%
    percentage_float = truncate_to_two_decimal_places(percentage)
    
    # 判斷漲跌
    if up_down > 0:
        up_down_message = f"▲{up_down_float}({percentage_float}%)"
    elif up_down < 0:
        up_down_message = f"▼{up_down_float}({percentage_float}%)"
    else:
        up_down_message = f"─{up_down_float}({percentage_float}%)"

    low = truncate_to_two_decimal_places(today_low)  # 最低價
    high = truncate_to_two_decimal_places(today_high)  # 最高價
    ltr = truncate_to_two_decimal_places(today_hist)  # 當日最後成交價
    msg = (f'\n{name}({code}) \n'
           f'當日最低：{low} \n'
           f'當日最高：{high} \n'
           f'最新價格：{ltr} {up_down_message} \n'
           f'現在時間：{time}\n')

    return msg, today_hist, percentage_float, consecutive_drops, drop_percentage

def calculate_consecutive_drops(close_series):
    df = close_series.to_frame(name='Close')

    consecutive_drops = 0
    total_drop = 0.0

    last_price = df['Close'].iloc[-1]  # 最新價格作為起始點

    for price in df['Close'].iloc[-2::-1]:
        if price > last_price:  # 如果前一天價格大於今天的價格，代表下跌
            consecutive_drops += 1  # 累計下跌天數
            total_drop += (price - last_price)  # 累計下跌的金額
            last_price = price
        else:
            break

    # 計算下跌百分比
    total_drop_percentage = (total_drop / df['Close'].iloc[-1]) * 100 if consecutive_drops > 0 else 0
    drop_percentage = truncate_to_two_decimal_places(total_drop_percentage)

    return consecutive_drops, drop_percentage


def check_and_notify():
    global check_count
    msg, today_hist, percentage_float, consecutive_drops, drop_percentage = get_now_stock()
    try:
        message = ""

        if percentage_float <= -2:
                message += f"單日下跌{percentage_float}%\n若因短期負面因素，視為潛在買入機會\n"

        if consecutive_drops > 3 or drop_percentage > 5:
            message += f"\n連續下跌天數：{consecutive_drops}天\n累計下跌幅度：-{drop_percentage}%"
            
        if message:
            send_line_notify(message)
        else:
            print("沒有顯著的股價變化")

        check_count += 1
        print(f"第{check_count}次執行")

    except Exception as e:
        print(f"錯誤: {e}")
        time.sleep(60)  # 等待1分鐘再繼續

            
def main():
    global api
    initialize_api()

    execute = random.randint(10, 30)
    schedule.every(execute).seconds.do(check_and_notify)  # 每10~30秒執行一次check_and_notify函式

    while True:
        try:
            schedule.run_pending()
            delay = random.randint(3, 5)
            time.sleep(delay)  # 暫停3~5秒，避免過於頻繁地檢查任務
        except Exception as e:
            print(f"主程式錯誤: {e}，重新執行程式")
            time.sleep(60)  # 等待1分鐘
            subprocess.Popen([sys.executable] + sys.argv, close_fds=True)  # 重啟程式
            sys.exit()  # 退出當前進程


def send_line_notify(message):
    msg, today_hist, percentage_float, consecutive_drops, drop_percentage = get_now_stock()

    url = 'https://notify-api.line.me/api/notify'
    token = 'LINE Notify發行的個人權杖'
    headers = {'Authorization': 'Bearer ' + token}

    param = {'message': f'{msg}\n{message}'}

    try:
        # 傳送
        requests.post(url, headers=headers, params=param)  # requests.post向伺服器提交資源或數據  data使用字典的方式傳送資料
    except Exception as e:
        print(f"發送LINE通知時出錯: {e}")

    time.sleep(300)  # 發送後暫停5分鐘，避免頻繁發送


if __name__ == "__main__":
    main()