import shioaji as sj  # Shioaji是用於永豐的API客戶端
import requests  # 獲取網頁套件
from datetime import date, timedelta  # 處理日期和時間
from datetime import datetime
import pandas as pd  # 數據處理和分析的庫


# API Key 和 Secret Key
API_KEY = "你的 API KEY"
SECRET_KEY = "你的 SECRET KEY"

# 股票代碼
STOCK_CODE = "股票代號"


def initialize_api():
    global api
    api = sj.Shioaji(simulation=True)
    accounts = api.login(API_KEY, SECRET_KEY)
    if len(accounts) == 0:
        raise ValueError("未找到帳戶")


# 取得個股長短期MACD方向
def get_stock_macd():
    initialize_api()

    # 設定日期範圍
    delta = timedelta(days=180)
    start_day = date.today() - delta  # 開始日期為180天前
    end_day = date.today()  # 結束日期今天
    
    stock = api.Contracts.Stocks[STOCK_CODE]
    
    kbars = api.kbars(contract=stock, start=str(start_day), end=str(end_day))  # "2024-08-05"
    df = pd.DataFrame({**kbars})  # 轉換為DataFrame陣列
    df.ts = pd.to_datetime(df.ts)
    df.set_index("ts", inplace=True)

    name = stock.name  # 股票名稱
    code = stock.code  # 股票代碼
    time = df.index[-1]  # 最後一筆成交時間

    # 每日K棒
    df = df.resample("D").last().dropna()  # 每日最後一筆價格，並刪除缺失值
    # 日K線資料計算短長期的MACD指標
    stock_macd_df = calculate_macd(df)
    stock_long_macd_df = calculate_long_macd(df)

    stock_macd_message = stock_macd_notify(stock_macd_df)  # 調用函式生成股票的歷史數據

    stock_long_macd_message = stock_macd_notify_long_term(stock_long_macd_df)

    msg = (f'\n{name}({code}) \n'
           f'短期趨勢：\n{stock_macd_message} \n'
           f'長期趨勢：\n{stock_long_macd_message} \n'
           f'日期時間：{time}\n')
    print(msg)

    flow_rate = api.usage()
    print(flow_rate)

    return msg


# 計算某個欄的指數移動平均線EMA
def calculate_ema(df, column, span):
    return df[column].ewm(span=span, adjust=False).mean()


# 計算MACD
def calculate_macd(df, short_span=12, long_span=26, signal_span=9):  # 短期指數移動平均線(EMA)的跨度(默認為12天)，長期(默認為26天)，信號線(默認為9天)
    df["EMA_short"] = calculate_ema(df, "Close", short_span)  # 調用calculate_ema函數，計算以Close欄為基準的短期EMA
    df["EMA_long"] = calculate_ema(df, "Close", long_span)  # 計算長期EMA
    # 計算DIF線(MACD快線)
    df["MACD"] = df["EMA_short"] - df["EMA_long"]  # MACD是短期EMA和長期EMA之間的差值，可顯示短期趨勢和長期趨勢之間的差異
    # 計算DEM線、MACD慢線(訊號線)
    df["Signal"] = calculate_ema(df, "MACD", signal_span)  # 信號線是MACD的9日平均值，是MACD的平滑版
    # 計算MACD直方圖
    df["Hist"] = df["MACD"] - df["Signal"]  # Histograms是MACD和Signal之間的差值，用來識別趨勢的強度和反轉信號
    return df


# 計算長期MACD
def calculate_long_macd(df, short_span=60, long_span=120, signal_span=9):
    df["MACD_60"] = calculate_ema(df, "Close", short_span)
    df["MACD_120"] = calculate_ema(df, "Close", long_span)
    # 計算DIF線(MACD快線)
    df["LONG_MACD"] = df["MACD_60"] - df["MACD_120"]
    # 計算DEM線、MACD慢線(訊號線)
    df["LONG_Signal"] = calculate_ema(df, "LONG_MACD", signal_span)
    # 計算MACD直方圖
    df["LONG_Hist"] = df["LONG_MACD"] - df["LONG_Signal"]
    return df


# 判斷個股MACD的趨勢
def stock_macd_notify(df):

    # 取近三天的MACD
    today_macd = df['MACD'].iloc[-1]  # 倒數第一筆數據
    yesterday_macd = df['MACD'].iloc[-2]  # 倒數第二筆數據
    two_days_ago_macd = df['MACD'].iloc[-3]  # 倒數第三筆數據
    # 取近三天的Signal信號線
    today_signal = df['Signal'].iloc[-1]
    yesterday_signal = df['Signal'].iloc[-2]
    two_days_ago_signal = df['Signal'].iloc[-3]
    # 取近兩天的Histogram直方圖
    today_hist = df['Hist'].iloc[-1]
    yesterday_hist = df['Hist'].iloc[-2]

    hist_message = ""
    # 判斷Histogram直方圖紅綠轉換
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
    # 判斷 MACD 線和 Signal 線的交叉
    if two_days_ago_macd <= two_days_ago_signal and yesterday_macd > yesterday_signal and today_macd > today_signal:
        # MACD 線從下方連續上穿 Signal 線
        message = "黃金交叉，顯示買入信號"
    elif two_days_ago_macd >= two_days_ago_signal and yesterday_macd < yesterday_signal and today_macd < today_signal:
        # MACD 線從上方連續下穿 Signal 線
        message = "死亡交叉，顯示賣出信號"
    else:
        # 無交叉信號情況
        message = "無明顯交叉信號，繼續觀察"
    
    response_message = f"{hist_message}\n{message}"

    return response_message  # 回傳趨勢的通知訊息


# 判斷個股長期MACD
def stock_macd_notify_long_term(df):
    last_hist = df['Hist'].iloc[-1]
    hist_mean = df["Hist"].mean()

    hist_message = ""

    # 判斷Histogram直方圖紅綠轉換
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

    # 判斷MACD線和Signal線的交叉
    if crossover_count >= 10:
        message = "潛在買入機會，考慮進場"
    elif previous_count >= 10:
        message = "潛在賣出機會，考慮賣出"
    
    response_message = f"{hist_message}\n{message}"

    return response_message  # 回傳趨勢的通知訊息


def send_line_notify(message):

    url = 'https://notify-api.line.me/api/notify'
    token = 'LINE Notify發行的個人權杖'
    headers = {'Authorization': 'Bearer ' + token}

    param = {'message': f'{message}'}

    data = requests.post(url, headers=headers, params=param)  # requests.post向伺服器提交資源或數據  data使用字典的方式傳送資料
    print(data)


if __name__ == "__main__":
    message = get_stock_macd()
    send_line_notify(message)