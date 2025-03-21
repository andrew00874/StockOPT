import pandas as pd
import requests
import re
import yfinance as yf
import tkinter as tk
from tkinter import messagebox
from io import StringIO

def fetch_options_data(ticker):
    """
    Yahoo Finance에서 특정 티커의 옵션 데이터를 가져오는 함수.
    """
    url = f"https://finance.yahoo.com/quote/{ticker}/options/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return None

    tables = pd.read_html(StringIO(response.text))

    if len(tables) < 2:
        return None

    try:
        call_options = tables[0]  # 콜 옵션 데이터
        put_options = tables[1]  # 풋 옵션 데이터
        return call_options, put_options, ticker
    except:
        return None

def extract_expiry_date(contract_name):
    """
    옵션 계약명에서 만기일을 추출하는 함수.
    """
    match = re.search(r"(\d{6})", contract_name)
    if match:
        expiry_date_raw = match.group(1)
        return f"20{expiry_date_raw[:2]}-{expiry_date_raw[2:4]}-{expiry_date_raw[4:]}"
    return "N/A"

def get_current_price(ticker):
    """
    yfinance를 사용하여 현재 주가를 가져오는 함수.
    """
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")["Close"].iloc[-1]
        return round(price, 2)
    except:
        return "N/A"
    
def get_oi_range(df, threshold=0.85):
    """
    Open Interest 누적 비율 기준으로 상위 특정 퍼센트(예: 85%)의 범위 내에서 최소/최대 행사가 선택.
    """
    df_sorted = df.sort_values("Strike")  # 행사가 정렬
    df_sorted["OI_Cumsum"] = df_sorted["Open Interest"].cumsum()  # 누적합 계산
    total_oi = df_sorted["Open Interest"].sum()

    # 전체 OI 중 특정 퍼센트(threshold) 내에 속하는 행사가만 선택
    df_filtered = df_sorted[df_sorted["OI_Cumsum"] <= total_oi * threshold]

    # 최종적으로 남은 행사가의 최소/최대값을 선택
    return df_filtered["Strike"].min(), df_filtered["Strike"].max()

def parse_options_data(call_df, put_df, ticker):
    """
    옵션 데이터를 분석하고 보고서를 생성하는 함수.
    """
    if call_df is None or put_df is None:
        return "❌ 유효한 옵션 데이터를 가져오지 못했습니다."

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
    most_traded_put_oi = put_df.loc[put_df["Volume"].idxmax(), "Open Interest"]  # ✅ OI 추가

    highest_change_call = call_df.loc[call_df["Change"].idxmax()]
    highest_change_put = put_df.loc[put_df["Change"].idxmax()]

    avg_strike = (call_df["Strike"].mean() + put_df["Strike"].mean()) / 2
    atm_strike = call_df.loc[(call_df["Strike"] - current_price).abs().idxmin(), "Strike"]
    target_price = (avg_strike * 0.2 + atm_strike * 0.8)

    # IV Skew 계산
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

    # OI 기반 박스권 조정
    filtered_put_min, _ = get_oi_range(put_df, threshold=0.85)
    _, filtered_call_max = get_oi_range(call_df, threshold=0.85)

    # 거래량을 고려하여 박스권 조정
    filtered_put_min = max(filtered_put_min, most_traded_put_strike)
    filtered_call_max = min(filtered_call_max, most_traded_call_strike)

    # ✅ 기본 `strategy` 값 설정 (모든 경우 대비)
    
    strategy = "🔍 중립: 시장 방향성이 뚜렷하지 않음."

    # 의미 있는 skew 임계값 설정
    skew_threshold = 2.0 #skew_threshold = 2.0: 2% 이상일 때만 skew를 의미 있는 심리로 간주
    is_significant_positive_skew = iv_skew > skew_threshold
    is_significant_negative_skew = iv_skew < -skew_threshold

    # 우선순위: 강한 신호 → 약한 신호 → 중립
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

    # ✅ `report_text`가 항상 생성되도록 보장
    report_text = f"""
    📌 {ticker} 옵션 데이터 분석 보고서

    {strategy}
    {bullish_sentiment} {bearish_sentiment} {high_iv} {iv_skew}
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


# ✅ 결과를 별도 창으로 보여주는 함수
def show_report_window(report):
    top = tk.Toplevel()
    top.title("옵션 데이터 분석 결과")
    top.geometry("700x500")  # 크기 조정 가능

    text = tk.Text(top, wrap="word", font=("Segoe UI Emoji", 12))
    text.insert("1.0", report)
    text.config(state="disabled")  # 편집 금지
    text.pack(expand=True, fill="both", padx=10, pady=10)

# ✅ GUI 함수
def show_report():
    ticker = ticker_entry.get().upper()
    if not ticker:
        messagebox.showerror("입력 오류", "티커명을 입력하세요!")
        return

    df_ticker = fetch_options_data(ticker)
    if df_ticker is None:
        messagebox.showerror("데이터 오류", f"{ticker}의 옵션 데이터를 가져올 수 없습니다.")
        return

    call_df, put_df, ticker = df_ticker
    report = parse_options_data(call_df, put_df, ticker)
    
    show_report_window(report)  # ✅ 별도 창으로 결과 출력

# ✅ Tkinter GUI 설정
root = tk.Tk()
root.title("옵션 데이터 분석기")
root.geometry("500x250")

label = tk.Label(root, text="티커명을 입력하세요:", font=("Arial", 14))
label.pack(pady=10)

ticker_entry = tk.Entry(root, font=("Arial", 16))
ticker_entry.pack(pady=5)

analyze_button = tk.Button(root, text="분석 시작", command=show_report, font=("Arial", 14))
analyze_button.pack(pady=10)

root.mainloop()
