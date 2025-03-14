import pandas as pd
import sys
import requests
import re
from io import StringIO
import yfinance as yf  # yfinance 추가

def fetch_options_data(ticker):
    """
    Yahoo Finance에서 특정 티커의 옵션 데이터를 가져오는 함수.
    """
    url = f"https://finance.yahoo.com/quote/{ticker}/options/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"❌ 데이터 가져오기 실패: {ticker}의 옵션 데이터를 가져올 수 없습니다.")
        return None

    tables = pd.read_html(StringIO(response.text))

    if len(tables) < 2:
        print(f"❌ 옵션 데이터 없음: {ticker}의 옵션 데이터를 찾을 수 없습니다.")
        return None

    try:
        call_options = tables[0]  # 콜 옵션 데이터
        put_options = tables[1]  # 풋 옵션 데이터
        return call_options, put_options, ticker
    except Exception as e:
        print(f"❌ 데이터 파싱 오류: {e}")
        return None

def extract_expiry_date(contract_name):
    """
    옵션 계약명에서 만기일을 추출하는 함수.
    """
    match = re.search(r"(\d{6})", contract_name)
    if match:
        expiry_date_raw = match.group(1)  # 예: '250314'
        return f"20{expiry_date_raw[:2]}-{expiry_date_raw[2:4]}-{expiry_date_raw[4:]}"  # '2025-03-14'
    return "N/A"

def get_current_price(ticker):
    """
    Yahoo Finance의 yfinance 모듈을 활용하여 현재 주가를 가져오는 함수.
    """
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")["Close"].iloc[-1]
        return round(price, 2)
    except Exception as e:
        print(f"⚠️ {ticker}의 현재 주가를 가져오는 데 실패했습니다: {e}")
        return "N/A"

def parse_options_data(call_df, put_df, ticker):
    """
    옵션 데이터를 분석하고 매수/매도를 추천하는 보고서를 생성하는 함수.
    """
    if call_df is None or put_df is None:
        return "❌ 유효한 옵션 데이터를 가져오지 못했습니다."

    # 데이터 전처리: 숫자 형식 변환 (천 단위 콤마 제거)
    for df in [call_df, put_df]:
        df["Volume"] = pd.to_numeric(df["Volume"].replace("-", "0").astype(str).str.replace(",", ""), errors='coerce').fillna(0)
        df["Implied Volatility"] = pd.to_numeric(df["Implied Volatility"].astype(str).replace("%", "", regex=True), errors='coerce').fillna(0)
        df["Last Price"] = pd.to_numeric(df["Last Price"], errors='coerce').fillna(0)
        df["Open Interest"] = pd.to_numeric(df["Open Interest"].replace("-", "0").astype(str).str.replace(",", ""), errors='coerce').fillna(0)
        df["Bid-Ask Spread"] = abs(df["Ask"] - df["Bid"])

    # 만기일 가져오기
    expiry_date = extract_expiry_date(call_df.iloc[0]['Contract Name'])

    # 현재 주가 가져오기 (yfinance 활용)
    current_price = get_current_price(ticker)
    if current_price == "N/A":
        print(f"⚠️ {ticker}의 현재 주가를 가져올 수 없습니다. 기본값을 사용합니다.")
        current_price = call_df["Strike"].median()

    current_price = float(current_price)

    # Put/Call Ratio 계산
    total_call_volume = call_df["Volume"].sum()
    total_put_volume = put_df["Volume"].sum()
    put_call_ratio = total_put_volume / total_call_volume if total_call_volume > 0 else float('inf')

    # 가장 높은 거래량을 가진 옵션 찾기
    most_traded_call_strike = call_df.loc[call_df["Volume"].idxmax(), "Strike"]
    most_traded_put_strike = put_df.loc[put_df["Volume"].idxmax(), "Strike"]

    # 예상 Target Price 계산
    avg_strike = (call_df["Strike"].mean() + put_df["Strike"].mean()) / 2
    atm_strike = call_df.loc[(call_df["Strike"] - current_price).abs().idxmin(), "Strike"]
    most_liquid_call_strike = call_df.loc[call_df["Open Interest"].idxmax(), "Strike"]
    most_liquid_put_strike = put_df.loc[put_df["Open Interest"].idxmax(), "Strike"]
    most_liquid_strike = (most_liquid_call_strike + most_liquid_put_strike) / 2  # 콜/풋 평균 사용
    target_price = (most_liquid_strike * 0.05 + avg_strike * 0.05 + atm_strike * 0.9)

    # 시장 심리 분석 (PCR, 거래량, IV 포함)
    bullish_sentiment = (call_df["Volume"].mean() > put_df["Volume"].mean()) and (put_call_ratio < 1)
    high_iv = call_df["Implied Volatility"].mean() > put_df["Implied Volatility"].mean()

    # 매수/매도 추천 전략 도출
    if bullish_sentiment and not high_iv:
        strategy = "🚀 강한 매수 신호: 현물(주식) 또는 레버리지 롱 포지션 추천."
    elif bullish_sentiment and high_iv:
        strategy = "⚠️ 조심스러운 매수: 레버리지 롱 포지션 가능하나 변동성 주의."
    elif not bullish_sentiment and high_iv:
        strategy = "📉 매도 신호: 현물 매도 또는 숏 포지션 고려."
    else:
        strategy = "🔍 중립: 시장 방향성이 뚜렷하지 않으므로 관망 추천."

    volatility = call_df["Implied Volatility"].mean() / 100  # 변동성을 소수로 변환
    min_target_price = target_price * (1 - volatility * 0.2)  # 조정 계수 추가
    max_target_price = target_price * (1 + volatility * 0.2)


    # 보고서 생성
    report_text = f"""
    📌 {ticker} 옵션 데이터 기반 매매 추천 보고서

    {strategy}
    📊 Put/Call Ratio: {put_call_ratio:.2f}
    📅 만기일: {expiry_date}
    🎯 예상 Target Price: ${min_target_price:.2f} ~ ${max_target_price:.2f}
    💰 현재 주가: ${current_price}
    🔥 거래량 가장 높은 콜 옵션 가격: ${most_traded_call_strike}
    🔥 거래량 가장 높은 풋 옵션 가격: ${most_traded_put_strike}
    🔥 실시간 변동성 지표 {volatility:.2f}
    """

    return report_text, ticker

def main():
    if len(sys.argv) < 2:
        print("사용법: python 파일이름.py TSLA")
        return

    ticker = sys.argv[1].upper()
    df_ticker = fetch_options_data(ticker)
    if df_ticker is None:
        print(f"❌ {ticker}의 옵션 데이터를 가져오지 못했습니다. 프로그램을 종료합니다.")
        return
    call_df, put_df, ticker = df_ticker
    options_report, ticker = parse_options_data(call_df, put_df, ticker)
    print(options_report)

if __name__ == "__main__":
    main()
