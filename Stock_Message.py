import shioaji as sj
import requests
from datetime import date, timedelta, datetime
import time
import schedule
import pandas as pd
import subprocess
import sys


API_KEY = "你的 API KEY"
SECRET_KEY = "你的 SECRET KEY"

STOCK_CODE = "股票代號"

def initialize_api():
    global api
    api = sj.Shioaji(simulation=True)
    accounts = api.login(API_KEY, SECRET_KEY)
    if len(accounts) == 0:
        raise ValueError("未找到帳戶")


def truncate_to_two_decimal_places(value):
    return float(f"{value:.2f}")


def get_now_stock():

    delta = timedelta(days=60)
    start_day = date.today() - delta
    end_day = date.today()
    
    stock = api.Contracts.Stocks[STOCK_CODE]

    kbars = api.kbars(contract=stock, start=str(start_day), end=str(end_day))
    df = pd.DataFrame({**kbars})
    df.ts = pd.to_datetime(df.ts)
    df.set_index("ts", inplace=True)

    daily_low = df['Low'].resample('D').min().dropna()
    daily_high = df['High'].resample('D').max().dropna()
    daily_Close = df['Close'].resample("D").last().dropna()

    consecutive_drops, drop_percentage = calculate_consecutive_drops(daily_Close)
    
    name = stock.name
    code = stock.code
    today_low = daily_low.iloc[-1]
    today_high = daily_high.iloc[-1]
    yesterday_hist = daily_Close.iloc[-2]
    today_hist = daily_Close.iloc[-1]
    time = df.index[-1]
    
    up_down = today_hist - yesterday_hist
    up_down_float = truncate_to_two_decimal_places(up_down)
    percentage = (up_down / yesterday_hist) * 100
    percentage_float = truncate_to_two_decimal_places(percentage)
    
    if up_down > 0:
        up_down_message = f"▲{up_down_float}({percentage_float}%)"
    elif up_down < 0:
        up_down_message = f"▼{up_down_float}({percentage_float}%)"
    else:
        up_down_message = f"─{up_down_float}({percentage_float}%)"

    low = truncate_to_two_decimal_places(today_low)
    high = truncate_to_two_decimal_places(today_high)
    ltr = truncate_to_two_decimal_places(today_hist)
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

    last_price = df['Close'].iloc[-1]

    for price in df['Close'].iloc[-2::-1]:
        if price > last_price:
            consecutive_drops += 1
            total_drop += (price - last_price)
            last_price = price
        else:
            break

    total_drop_percentage = (total_drop / df['Close'].iloc[-1]) * 100 if consecutive_drops > 0 else 0
    drop_percentage = truncate_to_two_decimal_places(total_drop_percentage)

    return consecutive_drops, drop_percentage


def check_and_notify():
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

    except Exception as e:
        print(f"錯誤: {e}")
        time.sleep(60)

            
def main():
    initialize_api()

    schedule.every(30).seconds.do(check_and_notify)

    while True:
        try:
            schedule.run_pending()
            time.sleep(3)
        except Exception as e:
            print(f"主程式錯誤: {e}，重新執行程式")
            time.sleep(60)
            subprocess.Popen([sys.executable] + sys.argv, close_fds=True)
            sys.exit()


def send_line_notify(message):
    msg, today_hist, percentage_float, consecutive_drops, drop_percentage = get_now_stock()

    url = 'https://notify-api.line.me/api/notify'
    token = 'LINE Notify發行的個人權杖'
    headers = {'Authorization': 'Bearer ' + token}

    param = {'message': f'{msg}\n{message}'}

    try:
        # 傳送
        requests.post(url, headers=headers, params=param)
        time.sleep(300)
    except Exception as e:
        print(f"發送LINE通知時出錯: {e}")


if __name__ == "__main__":
    main()