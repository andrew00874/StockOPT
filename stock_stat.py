import pandas as pd
import requests
import re
import yfinance as yf
import tkinter as tk
from tkinter import messagebox, ttk
from io import StringIO
import datetime
import calendar

def fetch_options_data(ticker, expiry_timestamp=None):
    base_url = f"https://finance.yahoo.com/quote/{ticker}/options"
    if expiry_timestamp:
        url = f"{base_url}?date={expiry_timestamp}"
    else:
        url = base_url

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return None

    try:
        tables = pd.read_html(StringIO(response.text))

        # 옵션 데이터로 예상되는 테이블만 필터링
        valid_tables = []
        for table in tables:
            if "Strike" in table.columns:
                try:
                    # Strike 열이 실제로 숫자형으로 변환 가능한 경우만
                    pd.to_numeric(table["Strike"].dropna().iloc[:3])
                    valid_tables.append(table)
                except:
                    continue

        if len(valid_tables) < 2:
            return None

        call_options = valid_tables[0]
        put_options = valid_tables[1]

        return call_options, put_options, ticker

    except Exception as e:
        print("파싱 오류:", e)
        return None



def get_expiry_dates(ticker):
    stock = yf.Ticker(ticker)
    try:
        return stock.options  # e.g., ['2025-03-21', '2025-03-28', ...]
    except:
        return []

def extract_expiry_date(contract_name):
    match = re.search(r"(\d{6})", contract_name)
    if match:
        expiry_date_raw = match.group(1)
        return f"20{expiry_date_raw[:2]}-{expiry_date_raw[2:4]}-{expiry_date_raw[4:]}"
    return "N/A"

def get_current_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")["Close"].iloc[-1]
        return round(price, 2)
    except:
        return "N/A"
    
def get_oi_range(df, threshold=0.85):
    df_sorted = df.sort_values("Strike")
    df_sorted["OI_Cumsum"] = df_sorted["Open Interest"].cumsum()
    total_oi = df_sorted["Open Interest"].sum()
    df_filtered = df_sorted[df_sorted["OI_Cumsum"] <= total_oi * threshold]
    return df_filtered["Strike"].min(), df_filtered["Strike"].max()

def parse_options_data(call_df, put_df, ticker):
    if call_df is None or put_df is None:
        return "❌ 유효한 옵션 데이터를 가져오지 못했습니다."
    if "Strike" not in call_df.columns or "Strike" not in put_df.columns:
        return "⚠️ 해당 만기일에 옵션 데이터(콜/풋)가 존재하지 않습니다."

    for df in [call_df, put_df]:
        df["Volume"] = pd.to_numeric(df["Volume"].replace("-", "0").astype(str).str.replace(",", ""), errors='coerce').fillna(0)
        df["Implied Volatility"] = pd.to_numeric(df["Implied Volatility"].astype(str).replace("%", "", regex=True), errors='coerce').fillna(0)
        df["Last Price"] = pd.to_numeric(df["Last Price"], errors='coerce').fillna(0)
        df["Open Interest"] = pd.to_numeric(df["Open Interest"].replace("-", "0").astype(str).str.replace(",", ""), errors='coerce').fillna(0)
        df["Bid"] = pd.to_numeric(df["Bid"], errors='coerce').fillna(0)
        df["Ask"] = pd.to_numeric(df["Ask"], errors='coerce').fillna(0)
        df["Bid-Ask Spread"] = abs(df["Ask"] - df["Bid"])
        df["Change"] = pd.to_numeric(df["Change"], errors='coerce').fillna(0)

    expiry_date = extract_expiry_date(call_df.iloc[0]['Contract Name'])
    current_price = get_current_price(ticker)
    if current_price == "N/A":
        current_price = call_df["Strike"].median()
    current_price = float(current_price)

    total_call_volume = call_df["Volume"].sum()
    total_put_volume = put_df["Volume"].sum()
    put_call_ratio = total_put_volume / total_call_volume if total_call_volume > 0 else float('inf')

    most_traded_call_strike = call_df.loc[call_df["Volume"].idxmax(), "Strike"]
    most_traded_put_strike = put_df.loc[put_df["Volume"].idxmax(), "Strike"]
    most_traded_call_oi = call_df.loc[call_df["Volume"].idxmax(), "Open Interest"]
    most_traded_put_oi = put_df.loc[put_df["Volume"].idxmax(), "Open Interest"]

    highest_change_call = call_df.loc[call_df["Change"].idxmax()]
    highest_change_put = put_df.loc[put_df["Change"].idxmax()]

    avg_strike = (call_df["Strike"].mean() + put_df["Strike"].mean()) / 2
    atm_strike = call_df.loc[(call_df["Strike"] - current_price).abs().idxmin(), "Strike"]
    target_price = (avg_strike * 0.2 + atm_strike * 0.8)

    atm_call_row = call_df.loc[(call_df["Strike"] - current_price).abs().idxmin()]
    atm_put_row = put_df.loc[(put_df["Strike"] - current_price).abs().idxmin()]
    atm_call_iv = atm_call_row["Implied Volatility"]
    atm_put_iv = atm_put_row["Implied Volatility"]
    iv_skew = atm_put_iv - atm_call_iv

    volatility = call_df["Implied Volatility"].mean() / 100
    min_target_price = target_price * (1 - volatility * 0.2)
    if min_target_price > current_price:
        min_target_price = current_price * (1 - volatility * 0.2)
    max_target_price = target_price * (1 + volatility * 0.2)
    most_traded_call_volume = call_df.loc[call_df["Volume"].idxmax(), "Volume"]
    most_traded_put_volume = put_df.loc[put_df["Volume"].idxmax(), "Volume"]

    bullish_sentiment = (call_df["Volume"].mean() > put_df["Volume"].mean()) and (put_call_ratio < 1) and (highest_change_call["Change"] > highest_change_put["Change"])
    high_iv = call_df["Implied Volatility"].mean() > put_df["Implied Volatility"].mean()
    bearish_sentiment = (most_traded_call_strike < most_traded_put_strike)
    mean_vix = (call_df["Implied Volatility"].mean() + put_df["Implied Volatility"].mean()) / 2

    filtered_put_min, _ = get_oi_range(put_df, threshold=0.85)
    _, filtered_call_max = get_oi_range(call_df, threshold=0.85)
    filtered_put_min = max(filtered_put_min, most_traded_put_strike)
    filtered_call_max = min(filtered_call_max, most_traded_call_strike)

    strategy = "🔍 중립: 시장 방향성이 뚜렷하지 않음."
    skew_threshold = 2.0
    is_significant_positive_skew = iv_skew > skew_threshold
    is_significant_negative_skew = iv_skew < -skew_threshold

    if bullish_sentiment and not bearish_sentiment and not high_iv and is_significant_negative_skew:
        strategy = "🚀 매우 강한 매수 신호: 주식 매수 또는 레버리지 매수 + 저변동성 혜택 가능."
    elif not bullish_sentiment and bearish_sentiment and not high_iv and is_significant_positive_skew:
        strategy = "⚠️ 매우 강한 매도 신호: 현물 매도 추천 및 숏 포지션 매수 추천"
    elif bullish_sentiment and not high_iv and is_significant_negative_skew:
        strategy = "🚀 매수 신호: 주식 매수 또는 레버리지 매수 + 저변동성 혜택 가능."
    elif bullish_sentiment and high_iv and is_significant_negative_skew:
        strategy = "📈 조심스러운 매수 신호: 현물 및 롱 포지션 매수 추천하지만 변동성 주의."
    elif not bullish_sentiment and high_iv and is_significant_positive_skew:
        strategy = "📉 조심스러운 매도 신호: 현물 매도 또는 숏 포지션 고려 (변동성 ↑ + 하락 대비 심리)"
    elif not bullish_sentiment and not high_iv and is_significant_positive_skew:
        strategy = "⚠️ 일반 매도 신호: 시장 약세 가능성 → 현물 매도/방어적 포지션 검토"

    report_text = f"""
    📌 {ticker} 옵션 데이터 분석 보고서

    {strategy}
    📅 기준 옵션 만기일: {expiry_date}
    💰 현재 주가: ${current_price}

    🔥 거래량 TOP 옵션
    - 📈 콜 옵션 행사가: ${most_traded_call_strike}
        - Volume : {most_traded_call_volume}
        - OI : {most_traded_call_oi}
    - 📉 풋 옵션 행사가: ${most_traded_put_strike} 
        - Volume : {most_traded_put_volume}
        - OI : {most_traded_put_oi}

    📊 시장 심리 분석
    - 🔄 Put/Call Ratio: {put_call_ratio:.2f}
    - 🔄 IV Skew (Put - Call): {iv_skew:.2f}%
    - 📌 실시간 변동성: {mean_vix:.1f}%
    """.strip()

    return report_text

def show_report_window(report):
    top = tk.Toplevel()
    top.title("옵션 데이터 분석 결과")
    top.geometry("700x500")

    text = tk.Text(top, wrap="word", font=("Segoe UI Emoji", 12))
    text.insert("1.0", report)
    text.config(state="disabled")
    text.pack(expand=True, fill="both", padx=10, pady=10)

def update_expiry_dates():
    ticker = ticker_entry.get().upper()
    if not ticker:
        return

    expiry_combo['values'] = []
    expiry_combo.set("불러오는 중...")

    date_list = get_expiry_dates(ticker)
    if date_list:
        expiry_combo['values'] = date_list
        expiry_combo.set(date_list[0])
    else:
        expiry_combo.set("만기일 없음")

def show_report():
    ticker = ticker_entry.get().upper()
    if not ticker:
        messagebox.showerror("입력 오류", "티커명을 입력하세요!")
        return

    selected_date = expiry_combo.get()
    if not selected_date:
        messagebox.showerror("입력 오류", "만기일을 선택하세요!")
        return

    import calendar

# 기존 코드 수정
    expiry_timestamp = calendar.timegm(datetime.datetime.strptime(selected_date, "%Y-%m-%d").timetuple())
    df_ticker = fetch_options_data(ticker, expiry_timestamp=expiry_timestamp)

    if df_ticker is None:
        messagebox.showerror("데이터 오류", f"{ticker}의 옵션 데이터를 가져올 수 없습니다.")
        return

    call_df, put_df, ticker = df_ticker
    report = parse_options_data(call_df, put_df, ticker)
    
    show_report_window(report)

# ✅ GUI 구성
root = tk.Tk()
root.title("옵션 데이터 분석기")
root.geometry("500x350")

label = tk.Label(root, text="티커명을 입력하세요:", font=("Arial", 14))
label.pack(pady=10)

ticker_entry = tk.Entry(root, font=("Arial", 16))
ticker_entry.pack(pady=5)

expiry_label = tk.Label(root, text="만기일 선택:", font=("Arial", 12))
expiry_label.pack(pady=5)

expiry_combo = ttk.Combobox(root, font=("Arial", 12))
expiry_combo.pack(pady=5)

update_button = tk.Button(root, text="만기일 불러오기", command=update_expiry_dates, font=("Arial", 12))
update_button.pack(pady=5)

analyze_button = tk.Button(root, text="분석 시작", command=show_report, font=("Arial", 14))
analyze_button.pack(pady=15)

root.mainloop()
