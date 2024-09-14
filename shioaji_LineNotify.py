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
    delta = timedelta(days=20)
    start_day = date.today() - delta  # 開始日期為20天前(考慮到年假不開市)
    end_day = date.today()  # 結束日期今天
    
    stock = api.Contracts.Stocks[STOCK_CODE]
    kbars = api.kbars(contract=stock, start=str(start_day), end=str(end_day))
    df = pd.DataFrame({**kbars})
    df.ts = pd.to_datetime(df.ts)
    df.set_index("ts", inplace=True)
    df = df.resample("D").last().dropna()
    
    name = stock.name  # 股票名稱
    code = stock.code  # 股票代碼
    today_high = df.iloc[-1, 1]  # 當日最高
    today_low = df.iloc[-1, 2]  # 當日最低
    yesterday_hist = df.iloc[-2, 3]  # 倒數第二筆資料，昨日收盤價
    today_hist = df.iloc[-1, 3]  # 倒數第一筆資料，即時售價
    
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

    now = datetime.now()  # 獲取當前時間
    time = now.strftime('%Y-%m-%d %H:%M:%S')

    low = truncate_to_two_decimal_places(today_low)  # 最低價
    high = truncate_to_two_decimal_places(today_high)  # 最高價
    ltr = truncate_to_two_decimal_places(today_hist)  # 當日最後成交價
    msg = (f'\n{name}({code}) \n'
           f'當日最低：{low} \n'
           f'當日最高：{high} \n'
           f'最新價格：{ltr} {up_down_message} \n'
           f'現在時間：{time}\n')

    flow_rate = api.usage()
    print(flow_rate)

    return msg, today_hist, percentage_float


def check_and_notify():
    msg, today_hist, percentage_float = get_now_stock()
    try:
        if today_hist is None:
            print("無法取得股票數據")
        elif percentage_float is not None:
            if percentage_float <= -8:
                message = f"下跌{percentage_float}% 建議大量買入，利用大幅回檔機會"
            elif percentage_float <= -5:
                message = f"下跌{percentage_float}% 建議適量買入，降低成本"
            elif percentage_float <= -2:
                message = f"下跌{percentage_float}% 建議少量買入，觀察是否反彈"
            else:
                print("沒有顯著的股價下跌")
                message = None
            
            if message:
                send_line_notify(message)

    except Exception as e:
        print(f"錯誤: {e}")
        time.sleep(30)

            
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
    msg, today_hist, percentage_float = get_now_stock()

    url = 'https://notify-api.line.me/api/notify'
    token = 'LINE Notify發行的個人權杖'
    headers = {'Authorization': 'Bearer ' + token}

    param = {'message': f'{msg}\n{message}'}

    try:
        # 傳送
        data = requests.post(url, headers=headers, params=param)  # requests.post向伺服器提交資源或數據  data使用字典的方式傳送資料
        print(data)
    except Exception as e:
        print(f"發送LINE通知時出錯: {e}")


if __name__ == "__main__":
    main()