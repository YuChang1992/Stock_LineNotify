import shioaji as sj
import requests
from datetime import date, timedelta
from datetime import datetime
import pandas as pd


API_KEY = "你的 API KEY"
SECRET_KEY = "你的 SECRET KEY"


STOCK_CODE = "股票代號"


def initialize_api():
    global api
    api = sj.Shioaji(simulation=True)
    accounts = api.login(API_KEY, SECRET_KEY)
    if len(accounts) == 0:
        raise ValueError("未找到帳戶")


def get_stock_macd():
    initialize_api()

    delta = timedelta(days=180)
    start_day = date.today() - delta
    end_day = date.today()
    
    stock = api.Contracts.Stocks[STOCK_CODE]
    
    kbars = api.kbars(contract=stock, start=str(start_day), end=str(end_day))
    df = pd.DataFrame({**kbars})
    df.ts = pd.to_datetime(df.ts)
    df.set_index("ts", inplace=True)

    name = stock.name
    code = stock.code
    time = df.index[-1]

    df = df.resample("D").last().dropna()
    stock_macd_df = calculate_macd(df)
    stock_long_macd_df = calculate_long_macd(df)

    stock_macd_message = stock_macd_notify(stock_macd_df)

    stock_long_macd_message = stock_macd_notify_long_term(stock_long_macd_df)

    msg = (f'\n{name}({code}) \n'
           f'短期趨勢：\n{stock_macd_message} \n'
           f'長期趨勢：\n{stock_long_macd_message} \n'
           f'日期時間：{time}\n')
    print(msg)

    flow_rate = api.usage()
    print(flow_rate)

    return msg


def calculate_ema(df, column, span):
    return df[column].ewm(span=span, adjust=False).mean()


def calculate_macd(df, short_span=12, long_span=26, signal_span=9):
    df["EMA_short"] = calculate_ema(df, "Close", short_span)
    df["EMA_long"] = calculate_ema(df, "Close", long_span)
    df["MACD"] = df["EMA_short"] - df["EMA_long"]
    df["Signal"] = calculate_ema(df, "MACD", signal_span)
    df["Hist"] = df["MACD"] - df["Signal"]
    return df


def calculate_long_macd(df, short_span=60, long_span=120, signal_span=9):
    df["MACD_60"] = calculate_ema(df, "Close", short_span)
    df["MACD_120"] = calculate_ema(df, "Close", long_span)
    df["LONG_MACD"] = df["MACD_60"] - df["MACD_120"]
    df["LONG_Signal"] = calculate_ema(df, "LONG_MACD", signal_span)
    df["LONG_Hist"] = df["LONG_MACD"] - df["LONG_Signal"]
    return df


def stock_macd_notify(df):

    today_macd = df['MACD'].iloc[-1]
    yesterday_macd = df['MACD'].iloc[-2]
    two_days_ago_macd = df['MACD'].iloc[-3]
    today_signal = df['Signal'].iloc[-1]
    yesterday_signal = df['Signal'].iloc[-2]
    two_days_ago_signal = df['Signal'].iloc[-3]
    today_hist = df['Hist'].iloc[-1]
    yesterday_hist = df['Hist'].iloc[-2]

    hist_message = ""
    if today_hist > 0:
        if yesterday_hist > 0:
            if today_hist > yesterday_hist:
                hist_message = "『紅柱』持續增長，趨勢上漲"
            else:
                hist_message = "『紅柱』縮短，停止買入，留倉觀察"
        else:
            hist_message = "『綠轉紅』可能趨勢轉強，考慮進場"
    elif today_hist < 0:
        if yesterday_hist < 0:
            if today_hist < yesterday_hist:
                hist_message = "『綠柱』持續增長，趨勢下跌"
            else:
                hist_message = "『綠柱』縮短，抄底建倉，小量進場"
        else:
            hist_message = "『紅轉綠』可能趨勢轉弱，謹慎操作"
    else:
        hist_message = "無明顯變化，無法判斷趨勢"

    message = ""
    if two_days_ago_macd <= two_days_ago_signal and yesterday_macd > yesterday_signal and today_macd > today_signal:
        message = "黃金交叉，顯示買入信號"
    elif two_days_ago_macd >= two_days_ago_signal and yesterday_macd < yesterday_signal and today_macd < today_signal:
        message = "死亡交叉，顯示賣出信號"
    else:
        message = "無明顯交叉信號，繼續觀察"
    
    response_message = f"{hist_message}\n{message}"

    return response_message


def stock_macd_notify_long_term(df):
    last_hist = df['Hist'].iloc[-1]
    hist_mean = df["Hist"].mean()

    hist_message = ""

    if last_hist > 0:
        if hist_mean > 0:
            hist_message = "上升趨勢增長，顯示長期潛力"
        else:
            hist_message = "上升趨勢縮減，考慮降低持倉"
    elif last_hist < 0:
        if hist_mean < 0:
            hist_message = "下降趨勢增長，顯示長期風險"
        else:
            hist_message = "下降趨勢縮減，考慮適量進場"

    message = ""

    crossover_count = sum((df['MACD'].iloc[-i] > df['Signal'].iloc[-i]) for i in range(1, 21))
    previous_count = sum((df['MACD'].iloc[-i] < df['Signal'].iloc[-i]) for i in range(1, 21))

    if crossover_count >= 10:
        message = "潛在買入機會，考慮進場"
    elif previous_count >= 10:
        message = "潛在賣出機會，考慮賣出"
    
    response_message = f"{hist_message}\n{message}"

    return response_message


def send_line_notify(message):

    url = 'https://notify-api.line.me/api/notify'
    token = 'LINE Notify發行的個人權杖'
    headers = {'Authorization': 'Bearer ' + token}

    param = {'message': f'{message}'}

    data = requests.post(url, headers=headers, params=param)
    print(data)


if __name__ == "__main__":
    message = get_stock_macd()
    send_line_notify(message)