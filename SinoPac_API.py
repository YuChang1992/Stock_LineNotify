import shioaji as sj
import json
import pandas as pd
from datetime import date, timedelta

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
                    "username": accounts[0].username}

        elif action == "get_ma_stop_loss":
            stock_code = event.get("stock_code")
            buy_price = event.get("buy_price")
            ma_diff_data = get_current_ma_diff(event, stock_code, buy_price)
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"account_id": accounts[0].account_id,
                    "responseData": ma_diff_data}
                )
            }
        elif action == "get_index_info":
            index_info = get_index_information(event)
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"account_id": accounts[0].account_id,
                    "responseData": index_info}
                )
            }
        elif action == "get_stock_macd":
            stock_code = event.get("stock_code")
            stock_macd = get_stock_macd(event, stock_code)
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"account_id": accounts[0].account_id,
                    "responseData": stock_macd}
                )
            }
        elif action == "get_now_stock":
            stock_code = event.get("stock_code")
            up_down = get_now_stock(event, stock_code)
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"account_id": accounts[0].account_id,
                    "responseData": up_down}
                )
            }
        else:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"account_id": accounts[0].account_id,
                    "responseData": "發生錯誤"}
                )
            }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def calculate_moving_averages(event, stock_code, window=60, buy_price=None):
    get_api_and_accounts(event)

    today = date.today()
    delta = timedelta(days=180)
    date_180 = today - delta
    
    kbars = api.kbars(
        contract=api.Contracts.Stocks[stock_code],
        start=str(date_180),
        end=str(today)
    )

    df = pd.DataFrame({**kbars})
    df.ts = pd.to_datetime(df.ts)
    df.set_index("ts", inplace=True)

    df = df.resample("D").last().dropna()

    df["5MA"] = df["Close"].rolling(window=5).mean().round(2)
    df["10MA"] = df["Close"].rolling(window=10).mean().round(2)
    df["20MA"] = df["Close"].rolling(window=20).mean().round(2)
    df["60MA"] = df["Close"].rolling(window=60).mean().round(2)
    df["20MA/60MA"] = (df["20MA"] / df["60MA"]).round(2)

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


def get_index_information(event):
    get_api_and_accounts(event)
    
    delta = timedelta(days=180)
    start_day = date.today() - delta
    end_day = date.today()

    tse_index = api.Contracts.Indexs.TSE["001"]
    otc_index = api.Contracts.Indexs.OTC["101"]

    tse_kbars = api.kbars(contract=tse_index, start=str(start_day), end=str(end_day))
    otc_kbars = api.kbars(contract=otc_index, start=str(start_day), end=str(end_day))

    tse_df = pd.DataFrame({**tse_kbars})
    tse_df.ts = pd.to_datetime(tse_df.ts)
    tse_df.set_index("ts", inplace=True)
    otc_df = pd.DataFrame({**otc_kbars})
    otc_df.ts = pd.to_datetime(otc_df.ts)
    otc_df.set_index("ts", inplace=True)

    tse_daily_df = tse_df.resample("D").last().dropna()
    otc_daily_df = otc_df.resample("D").last().dropna()

    tse_macd_df = calculate_macd(tse_daily_df)
    otc_macd_df = calculate_macd(otc_daily_df)

    tse_response_msg = index_macd_notify(tse_macd_df["Hist"])
    otc_response_msg = index_macd_notify(otc_macd_df["Hist"])

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
    

def get_stock_macd(event, stock_code):
    get_api_and_accounts(event)

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


def calculate_ema(df, column, span):
    return df[column].ewm(span=span, adjust=False).mean()


def calculate_macd(df, short_span=12, long_span=26, signal_span=9):
    df["EMA_short"] = calculate_ema(df, "Close", short_span)
    df["EMA_long"] = calculate_ema(df, "Close", long_span)
    df["MACD"] = df["EMA_short"] - df["EMA_long"]
    df["Signal"] = calculate_ema(df, "MACD", signal_span)
    df["Hist"] = df["MACD"] - df["Signal"]
    return df


def index_macd_notify(df):
    today_hist = df.iloc[-1]
    yesterday_hist = df.iloc[-2]

    if today_hist > 0:
        if yesterday_hist < 0:
            response_message = "『綠轉紅』市場情緒由負轉正，觀察是否有進一步增長的空間。\n"
            response_message += "嘗試尋找強勢族群進場，仍需保持謹慎。"
        elif today_hist > yesterday_hist:
            response_message = "『紅柱增長』可以積極做多\n"
            response_message += "找到強勢族群中最好的，做好做滿。"
        else:
            response_message = "『紅柱縮短』降低槓桿跟部位，不再買入，留倉觀察"
    elif today_hist < 0:
        if yesterday_hist > 0:
            response_message = "『紅轉綠』市場情緒由正轉負，小心進一步下跌風險。\n"
            response_message += "建議減少倉位，觀望更明顯的反轉訊號。"
        elif today_hist < yesterday_hist:
            response_message = "『綠柱增長』不要看盤了，買了錢會賠光光\n"
            response_message += "禁止買入任何部位，嚴禁抄底\n"
            response_message += "如果持股已經套牢，彈上來是給你停損的"
        else:
            response_message = "『綠柱縮短』可以嘗試做多強勢族群，不上槓桿，嚴守停損\n"
            response_message += "記住這是搶反彈，停損一定要守在成本\n"
            response_message += "如果持股已經套牢，彈上來是給你停損的"
    else:
        response_message = "直方圖無變化，保持觀望。"

    return response_message


def stock_macd_notify(df):
    today_hist = df.iloc[-1]
    yesterday_hist = df.iloc[-2]

    if today_hist > 0:
        if today_hist > yesterday_hist:
            response_message = "『紅柱增長』續抱"
        else:
            response_message = "『紅柱縮短』停利降低部位"
    else:
        if today_hist < yesterday_hist:
            response_message = "『綠柱增長』不要買進"
        else:
            response_message = "『綠柱縮短』嘗試抄底建倉，小量進場試單"

    return response_message


def getAmountRankChangeCount(event):
    get_api_and_accounts(event)

    today = date.today()

    scanners = api.scanners(
        scanner_type=sj.constant.ScannerType.AmountRank, count=100, date=str(today)
    )

    df = pd.DataFrame(s.__dict__ for s in scanners)
    df.ts = pd.to_datetime(df.ts)

    changeTypeDf = df.change_type.value_counts()

    for i in range(1, 6):
        if changeTypeDf.get(i, 0) == 0:
            changeTypeDf[i] = 0

    limitUpAmount = int(changeTypeDf[1])
    upAmount = int(changeTypeDf[2])
    unChangeAmount = int(changeTypeDf[3])
    downAmount = int(changeTypeDf[4])
    limitDownAmount = int(changeTypeDf[5])

    result = {
        "漲停": limitUpAmount,
        "上漲": upAmount,
        "平盤": unChangeAmount,
        "下跌": downAmount,
        "跌停": limitDownAmount,
    }
    return result


if __name__ == "__main__":
    event = {
        "api_key": "你的 API KEY",
        "secret_key": "你的 SECRET KEY",
        "action": "要執行的動作",
        "stock_code": "股票代碼",
        "buy_price": "買入價格(數值)"
    }
    context = {}

    response = lambda_handler(event, None)

    print(response)