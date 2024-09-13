import shioaji as sj  # Shioaji是用於永豐的API客戶端
import json  # 處理JSON格式的數據
import pandas as pd  # 數據處理和分析的庫
from datetime import date, timedelta  # 處理日期和時間

api = None
accounts = None
    
def get_api_and_accounts(event):
    global api, accounts
    api_key = event.get("api_key")
    secret_key = event.get("secret_key")

    if not api_key or not secret_key:
        raise ValueError("API Key 或 Secret Key 為空")

    if api is None or accounts is None:
        initialize_api(api_key, secret_key)

def initialize_api(api_key, secret_key):
    global api, accounts
    try:
        api = sj.Shioaji(simulation=True)
        accounts = api.login(api_key, secret_key)
        if len(accounts) == 0:
            raise ValueError("未找到帳戶")
    except Exception as e:
        raise RuntimeError(f"初始化 API 失敗: {str(e)}")

def lambda_handler(event, context):
    try:
        get_api_and_accounts(event)
        action = event.get("action")
        
        if action == "get_account_id":
            return {"statusCode": 200,
                    "person_id": accounts[0].person_id,
                    "broker_id": accounts[0].broker_id,
                    "account_id": accounts[0].account_id,
                    "username": accounts[0].username}  # 返回第一個帳戶的帳戶資料

        elif action == "get_ma_stop_loss":
            stock_code = event.get("stock_code")  # 提取股票代碼
            buy_price = event.get("buy_price")  # 提取買入價格
            ma_diff_data = get_current_ma_diff(event, stock_code, buy_price)  # 調用get_current_ma_diff函數獲取MA跟買價的價差
            return {
                "statusCode": 200,  # 返回請求成功
                "body": json.dumps(
                    {"account_id": accounts[0].account_id,
                    "responseData": ma_diff_data}  # 返回帳戶ID和MA跟買價的價差
                )
            }
        elif action == "get_index_info":
            index_info = get_index_information(event)  # 調用get_index_information函數獲取加權指數&櫃買指數的MACD方向
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"account_id": accounts[0].account_id,
                    "responseData": index_info}  # 返回帳戶ID和加權指數&櫃買指數的MACD方向
                )
            }
        elif action == "get_stock_macd":
            stock_code = event.get("stock_code")
            stock_macd = get_stock_macd(event, stock_code)  # 調用get_stock_macd函數獲取MACD指標數據
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"account_id": accounts[0].account_id,
                    "responseData": stock_macd}  # 返回帳戶ID和MACD指標數據
                )
            }
        elif action == "get_now_stock":
            stock_code = event.get("stock_code")
            up_down = get_now_stock(event, stock_code)  # 調用get_now_stock函數獲取個股資訊
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"account_id": accounts[0].account_id,
                    "responseData": up_down}  # 返回帳戶ID和和個股漲跌
                )
            }
        else:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"account_id": accounts[0].account_id,
                    "responseData": "發生錯誤"}  # 返回帳戶ID和錯誤信息
                )
            }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def calculate_moving_averages(event, stock_code, window=60, buy_price=None):
    get_api_and_accounts(event)

    # 設定日期範圍
    today = date.today()
    delta = timedelta(days=180)
    date_180 = today - delta
    
    # 取得指定股票代碼在指定日期範圍內的K線數據
    kbars = api.kbars(
        contract=api.Contracts.Stocks[stock_code],
        start=str(date_180),
        end=str(today)
    )

    df = pd.DataFrame({**kbars})
    df.ts = pd.to_datetime(df.ts)
    df.set_index("ts", inplace=True)

    df = df.resample("D").last().dropna()

    # 計算移動平均線
    df["5MA"] = df["Close"].rolling(window=5).mean().round(2)  # 5日
    df["10MA"] = df["Close"].rolling(window=10).mean().round(2)  # 10日
    df["20MA"] = df["Close"].rolling(window=20).mean().round(2)  # 20日(月線)
    df["60MA"] = df["Close"].rolling(window=60).mean().round(2)  # 60日(季線)
    df["20MA/60MA"] = (df["20MA"] / df["60MA"]).round(2)  # 計算20日移動平均線與60日移動平均線的比率

    # 計算與買價的百分比差距
    if buy_price is not None:
        df["5MA_diff"] = ((buy_price - df["5MA"]) / buy_price * 100).round(2)
        df["10MA_diff"] = ((buy_price - df["10MA"]) / buy_price * 100).round(2)
        df["20MA_diff"] = ((buy_price - df["20MA"]) / buy_price * 100).round(2)
        df["60MA_diff"] = ((buy_price - df["60MA"]) / buy_price * 100).round(2)

    return df[
        [
            "5MA",
            "10MA",
            "20MA",
            "60MA",
            "20MA/60MA",
            "5MA_diff",
            "10MA_diff",
            "20MA_diff",
            "60MA_diff",
        ]
    ].dropna()


# 計算與買價的價差
def get_current_ma_diff(event, stock_code, buy_price=None):
    ma_data = calculate_moving_averages(event, stock_code, buy_price=buy_price)
    current_5ma_diff = ma_data["5MA_diff"].iloc[-1]
    current_10ma_diff = ma_data["10MA_diff"].iloc[-1]
    current_20ma_diff = ma_data["20MA_diff"].iloc[-1]
    current_60ma_diff = ma_data["60MA_diff"].iloc[-1]
    current_2060_diff = ma_data["20MA/60MA"].iloc[-1]

    result = {
        "5MA_diff": current_5ma_diff,
        "10MA_diff": current_10ma_diff,
        "20MA_diff": current_20ma_diff,
        "60MA_diff": current_60ma_diff,
        "20ma_60ma_diff": current_2060_diff,
    }
    return json.dumps(result)

    # 寫入ma_diff檔案
    # json_result = json.dumps(result, indent=4)
    # with open('ma_diff.json', 'w') as file:
    #     file.write(json_result)
    # print("已成功寫入 ma_diff.json")


# 取加權指數&櫃買指數的MACD方向
def get_index_information(event):
    get_api_and_accounts(event)
    
    # 設定日期範圍
    delta = timedelta(days=180)
    start_day = date.today() - delta
    end_day = date.today()

    tse_index = api.Contracts.Indexs.TSE["001"]  # 獲取加權指數（TSE）
    otc_index = api.Contracts.Indexs.OTC["101"]  # 獲取櫃買指數（OTC）

    # 取得加權指數資料在指定日期範圍內的K線數據
    tse_kbars = api.kbars(contract=tse_index, start=str(start_day), end=str(end_day))
    # 取得櫃買指數資料在指定日期範圍內的K線數據
    otc_kbars = api.kbars(contract=otc_index, start=str(start_day), end=str(end_day))

    tse_df = pd.DataFrame({**tse_kbars})
    tse_df.ts = pd.to_datetime(tse_df.ts)
    tse_df.set_index("ts", inplace=True)
    otc_df = pd.DataFrame({**otc_kbars})
    otc_df.ts = pd.to_datetime(otc_df.ts)
    otc_df.set_index("ts", inplace=True)

    tse_daily_df = tse_df.resample("D").last().dropna()
    otc_daily_df = otc_df.resample("D").last().dropna()

    # 對加權指數和櫃買指數的日K數據計算MACD指標
    tse_macd_df = calculate_macd(tse_daily_df)
    otc_macd_df = calculate_macd(otc_daily_df)

    # 生成加權指數和櫃買指數的MACD通知訊息
    tse_response_msg = index_macd_notify(tse_macd_df["Hist"])
    otc_response_msg = index_macd_notify(otc_macd_df["Hist"])

    # 獲取今日前100名漲跌家數
    amountRankChangeCount = getAmountRankChangeCount(event)

    result = {
        "加權指數MACD": tse_response_msg,
        "櫃買指數MACD": otc_response_msg,
        "今日前100名的漲跌家數": amountRankChangeCount,
    }
    return result

    # 寫入stock_macd檔案
    # with open('index_information.json', 'w', encoding='utf-8') as file:
    #     file.write(json.dumps(result, ensure_ascii=False, indent=4))
    # print("已成功寫入 index_information.json")


def truncate_to_two_decimal_places(value):
    return float(f"{value:.2f}")


# 取得個股即時資訊
def get_now_stock(event, stock_code):
    get_api_and_accounts(event)

    kbars = api.kbars(contract=api.Contracts.Stocks[stock_code])
    df = pd.DataFrame({**kbars})
    df.ts = pd.to_datetime(df.ts)
    df.set_index("ts", inplace=True)
    df = df.resample("D").last().dropna()

    today_hist = df.iloc[-1,3]
    print("即時售價",today_hist)
    yesterday_hist = df.iloc[-2,3]

    up_down = today_hist - yesterday_hist
    up_down_float = truncate_to_two_decimal_places(up_down)
    percentage = (up_down / yesterday_hist) * 100
    percentage_float = truncate_to_two_decimal_places(percentage)

    if up_down > 0:
        print(f"▲ {up_down_float} ({percentage_float}%)")
    elif up_down < 0:
        print(f"▼ {up_down_float} ({percentage_float}%)")
    else:
        print(f"─ {up_down_float} ({percentage_float}%)")

    if percentage_float <= -8:
        print(f"下跌{percentage_float}% 建議大量買入，利用大幅回檔機會")
    elif percentage_float <= -5:
        print(f"下跌{percentage_float}% 建議適量買入，降低成本")
    elif percentage_float <= -2:
        print(f"下跌{percentage_float}% 建議少量買入，觀察是否反彈")
    

# 取個股MACD方向
def get_stock_macd(event, stock_code):
    get_api_and_accounts(event)

    # 設定日期範圍
    delta = timedelta(days=180)
    start_day = date.today() - delta
    end_day = date.today()

    kbars = api.kbars(
        contract=api.Contracts.Stocks[stock_code],
        start=str(start_day),
        end=str(end_day)
    )

    df = pd.DataFrame({**kbars})
    df.ts = pd.to_datetime(df.ts)
    df.set_index("ts", inplace=True)

    df = df.resample("D").last().dropna()
    stock_macd_df = calculate_macd(df)

    stock_macd_message = stock_macd_notify(stock_macd_df["Hist"])
    result = {f"{stock_code}的MACD": stock_macd_message}
    return result

    # 寫入stock_macd檔案
    # with open('stock_macd.json', 'w', encoding='utf-8') as file:
    #     file.write(json.dumps(result, ensure_ascii=False, indent=4))
    # print("已成功寫入 stock_macd.json")


# 計算指數移動平均線EMA
def calculate_ema(df, column, span):
    return df[column].ewm(span=span, adjust=False).mean()


# 計算MACD
def calculate_macd(df, short_span=12, long_span=26, signal_span=9):  # 短期EMA的跨度(默認為12天)，長期(默認為26天)，信號線(默認為9天)
    df["EMA_short"] = calculate_ema(df, "Close", short_span)  # 計算短期EMA
    df["EMA_long"] = calculate_ema(df, "Close", long_span)  # 計算長期EMA
    # 計算MACD值
    df["MACD"] = df["EMA_short"] - df["EMA_long"]  # MACD是短期EMA減長期EMA
    # 計算EMA信號線
    df["Signal"] = calculate_ema(df, "MACD", signal_span)  # 信號線是MACD的9日平均值
    # 計算MACD直方圖
    df["Hist"] = df["MACD"] - df["Signal"]  #顯示MACD的波動幅度，是MACD和信號線之間的差值
    return df


# 判斷加權指數跟櫃買指數MACD的趨勢
def index_macd_notify(df):
    today_hist = df.iloc[-1]  # 取列表中倒數第一筆數據，是今天的MACD直方圖
    yesterday_hist = df.iloc[-2]  # 取列表中倒數第二筆數據，是昨天的MACD直方圖

    if today_hist > 0:  # 今日是紅柱
        if yesterday_hist < 0:  # 昨天是綠柱，今天轉紅柱
            response_message = "『綠轉紅』市場情緒由負轉正，觀察是否有進一步增長的空間。\n"
            response_message += "嘗試尋找強勢族群進場，仍需保持謹慎。"
        elif today_hist > yesterday_hist:  # 今日紅柱比昨日增長
            response_message = "『紅柱增長』可以積極做多\n"
            response_message += "找到強勢族群中最好的，做好做滿。"
        else:  # 今日紅柱比昨日縮短
            response_message = "『紅柱縮短』降低槓桿跟部位，不再買入，留倉觀察"
    elif today_hist < 0:  # 今日是綠柱
        if yesterday_hist > 0:  # 昨天是紅柱，今天轉綠柱
            response_message = "『紅轉綠』市場情緒由正轉負，小心進一步下跌風險。\n"
            response_message += "建議減少倉位，觀望更明顯的反轉訊號。"
        elif today_hist < yesterday_hist:  # 今日綠柱比昨日增長
            response_message = "『綠柱增長』不要看盤了，買了錢會賠光光\n"
            response_message += "禁止買入任何部位，嚴禁抄底\n"
            response_message += "如果持股已經套牢，彈上來是給你停損的"
        else:  # 今日綠柱比昨日縮短
            response_message = "『綠柱縮短』可以嘗試做多強勢族群，不上槓桿，嚴守停損\n"
            response_message += "記住這是搶反彈，停損一定要守在成本\n"
            response_message += "如果持股已經套牢，彈上來是給你停損的"
    else:
        response_message = "直方圖無變化，保持觀望。"

    return response_message  # 回傳直方圖趨勢的通知訊息


# 判斷個股MACD的趨勢
def stock_macd_notify(df):
    today_hist = df.iloc[-1]  # 取列表中倒數第一筆數據，是今天的MACD直方圖值
    yesterday_hist = df.iloc[-2]  # 取列表中倒數第二筆數據，是昨天的MACD直方圖值

    if today_hist > 0:  # 如果今天的直方圖大於0(紅柱)
        if today_hist > yesterday_hist:  # 如果今天的紅柱比昨天增長
            response_message = "『紅柱增長』續抱"
        else:  # 如果今天的紅柱比昨天縮短
            response_message = "『紅柱縮短』停利降低部位"
    else:  # 如果今天的直方圖小於0(綠柱)
        if today_hist < yesterday_hist:  # 如果今天的綠柱比昨天增長
            response_message = "『綠柱增長』不要買進"
        else:  # 如果今天的綠柱比昨天縮短
            response_message = "『綠柱縮短』嘗試抄底建倉，小量進場試單"

    return response_message  # 回傳直方圖趨勢的通知訊息


# 排行前100名的漲跌家數
def getAmountRankChangeCount(event):
    get_api_and_accounts(event)

    today = date.today()

    # 獲取今天的數據，按成交金額排序，取前100的股票
    scanners = api.scanners(
        scanner_type=sj.constant.ScannerType.AmountRank, count=100, date=str(today)
    )

    df = pd.DataFrame(s.__dict__ for s in scanners)
    df.ts = pd.to_datetime(df.ts)

    # 取change_type,計算漲停 上漲 下跌 跌停 平盤家數
    changeTypeDf = df.change_type.value_counts()

    for i in range(1, 6):
        if changeTypeDf.get(i, 0) == 0:
            changeTypeDf[i] = 0

    # 獲取每種類型的數量
    limitUpAmount = int(changeTypeDf[1])  # 漲停
    upAmount = int(changeTypeDf[2])  # 上漲
    unChangeAmount = int(changeTypeDf[3])  # 平盤
    downAmount = int(changeTypeDf[4])  # 下跌
    limitDownAmount = int(changeTypeDf[5])  # 跌停

    result = {
        "漲停": limitUpAmount,
        "上漲": upAmount,
        "平盤": unChangeAmount,
        "下跌": downAmount,
        "跌停": limitDownAmount,
    }
    return result

#--------------------------------------------------

if __name__ == "__main__":
    event = {
        "api_key": "你的 API KEY",
        "secret_key": "你的 SECRET KEY",
        "action": "要執行的動作",
        "stock_code": "股票代碼",
        "buy_price": "買入價格(數值)"
    }
    context = {}  # 在本地測試時，這個可以是空的

    # 調用 lambda_handler 函式
    response = lambda_handler(event, None)

    # 打印返回結果
    print(response)