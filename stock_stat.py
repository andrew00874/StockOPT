import pandas as pd
import requests
import re
import yfinance as yf
import tkinter as tk
from tkinter import messagebox, ttk
from io import StringIO
import datetime
import calendar
from functools import lru_cache
import threading

# 캐싱을 통한 성능 최적화 - 동일한 티커에 대한 반복 요청 방지
@lru_cache(maxsize=32)
def fetch_options_data(ticker, expiry_timestamp=None):
    base_url = f"https://finance.yahoo.com/quote/{ticker}/options"
    if expiry_timestamp:
        url = f"{base_url}?date={expiry_timestamp}"
    else:
        url = base_url

    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)  # 타임아웃 추가
        
        if response.status_code != 200:
            return None

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
        print(f"데이터 가져오기 오류: {e}")
        return None

# 캐싱을 통한 성능 최적화
@lru_cache(maxsize=32)
def get_expiry_dates(ticker):
    try:
        stock = yf.Ticker(ticker)
        return stock.options or []  # None 대신 빈 리스트 반환
    except Exception as e:
        print(f"만기일 가져오기 오류: {e}")
        return []

def extract_expiry_date(contract_name):
    match = re.search(r"(\d{6})", contract_name)
    if match:
        expiry_date_raw = match.group(1)
        return f"20{expiry_date_raw[:2]}-{expiry_date_raw[2:4]}-{expiry_date_raw[4:]}"
    return "N/A"

@lru_cache(maxsize=32)
def get_current_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")["Close"].iloc[-1]
        return round(price, 2)
    except Exception as e:
        print(f"현재가 가져오기 오류: {e}")
        return "N/A"
    
def get_oi_range(df, threshold=0.85):
    """거래량 기반 레인지 계산"""
    if df.empty or df["Open Interest"].sum() == 0:
        return 0, 0  # 기본값 반환
        
    df_sorted = df.sort_values("Strike")
    df_sorted["OI_Cumsum"] = df_sorted["Open Interest"].cumsum()
    total_oi = df_sorted["Open Interest"].sum()
    
    if total_oi == 0:
        return df_sorted["Strike"].min(), df_sorted["Strike"].max()
        
    df_filtered = df_sorted[df_sorted["OI_Cumsum"] <= total_oi * threshold]
    
    if df_filtered.empty:
        return df_sorted["Strike"].min(), df_sorted["Strike"].max()
        
    return df_filtered["Strike"].min(), df_filtered["Strike"].max()

def get_box_range_weighted(df, current_price, strike_distance_limit=0.25):
    """가중치 기반 박스권 계산"""
    if df.empty:
        return None
        
    lower = current_price * (1 - strike_distance_limit)
    upper = current_price * (1 + strike_distance_limit)
    df_filtered = df[df["Strike"].between(lower, upper)].copy()
    
    if df_filtered.empty or df_filtered["Open Interest"].sum() == 0:
        return None

    # 0으로 나누는 오류 방지
    df_filtered["WeightedScore"] = df_filtered["Open Interest"] * 0.3 + df_filtered["Volume"] * 0.7
    
    if df_filtered["WeightedScore"].max() == 0:
        return None
        
    best_strike = df_filtered.loc[df_filtered["WeightedScore"].idxmax(), "Strike"]
    
    return best_strike

def clean_numeric_columns(df, columns):
    """숫자형 칼럼 정리를 위한 헬퍼 함수"""
    for col in columns:
        if col in df.columns:
            # 숫자가 아닌 문자 제거 후 숫자로 변환
            df[col] = pd.to_numeric(
                df[col].astype(str).replace("-", "0").replace("%", "", regex=True).replace(",", "", regex=True), 
                errors='coerce'
            ).fillna(0)
    return df

def parse_options_data(call_df, put_df, ticker):
    """옵션 데이터 파싱 및 분석"""
    # 기본 검증
    if call_df is None or put_df is None:
        return "❌ 유효한 옵션 데이터를 가져오지 못했습니다."
    if "Strike" not in call_df.columns or "Strike" not in put_df.columns:
        return "⚠️ 해당 만기일에 옵션 데이터(콜/풋)가 존재하지 않습니다."

    # 데이터 전처리
    numeric_columns = ["Volume", "Implied Volatility", "Last Price", "Open Interest", "Bid", "Ask", "Change"]
    call_df = clean_numeric_columns(call_df, numeric_columns)
    put_df = clean_numeric_columns(put_df, numeric_columns)
    
    # Bid-Ask 스프레드 계산
    for df in [call_df, put_df]:
        df["Bid-Ask Spread"] = abs(df["Ask"] - df["Bid"])

    # 기본 데이터 추출
    try:
        expiry_date = extract_expiry_date(call_df.iloc[0]['Contract Name'])
    except (IndexError, KeyError):
        expiry_date = "N/A"
        
    current_price = get_current_price(ticker)
    if current_price == "N/A":
        current_price = call_df["Strike"].median()
    current_price = float(current_price)
    
    # 거래량 및 포지션 분석
    total_call_volume = call_df["Volume"].sum()
    total_put_volume = put_df["Volume"].sum()
    put_call_ratio = total_put_volume / total_call_volume if total_call_volume > 0 else float('inf')
    
    # 오류 방지를 위한 체크
    if call_df.empty or put_df.empty or call_df["Volume"].max() == 0 or put_df["Volume"].max() == 0:
        return "❌ 데이터가 충분하지 않습니다. 다른 만기일을 선택해보세요."
    
    # 최다 거래 행사가
    most_traded_call_strike = call_df.loc[call_df["Volume"].idxmax(), "Strike"]
    most_traded_put_strike = put_df.loc[put_df["Volume"].idxmax(), "Strike"]
    most_traded_call_oi = call_df.loc[call_df["Volume"].idxmax(), "Open Interest"]
    most_traded_put_oi = put_df.loc[put_df["Volume"].idxmax(), "Open Interest"]
    most_traded_call_volume = call_df.loc[call_df["Volume"].idxmax(), "Volume"]
    most_traded_put_volume = put_df.loc[put_df["Volume"].idxmax(), "Volume"]
    
    # 가장 큰 변화율
    highest_change_call = call_df.loc[call_df["Change"].idxmax()]
    highest_change_put = put_df.loc[put_df["Change"].idxmax()]
    
    # ATM 옵션 분석
    try:
        atm_call_row = call_df.loc[(call_df["Strike"] - current_price).abs().idxmin()]
        atm_put_row = put_df.loc[(put_df["Strike"] - current_price).abs().idxmin()]
        atm_call_iv = atm_call_row["Implied Volatility"]
        atm_put_iv = atm_put_row["Implied Volatility"]
        iv_skew = atm_put_iv - atm_call_iv
    except:
        atm_call_iv = atm_put_iv = iv_skew = 0
    
    # 시장 심리 분석
    bearish_sentiment = (put_df["Volume"].mean() > call_df["Volume"].mean())
    bullish_sentiment = (call_df["Volume"].mean() > put_df["Volume"].mean() and 
                         put_call_ratio < 1 and 
                         highest_change_call["Change"] > highest_change_put["Change"])
    
    # 변동성 분석
    mean_iv = (call_df["Implied Volatility"].mean() + put_df["Implied Volatility"].mean()) / 2
    iv_diff = abs(atm_call_iv - atm_put_iv)
    high_iv = (mean_iv > 30 or iv_diff > 5)
    
    # 레인지 분석
    try:
        filtered_put_min, _ = get_oi_range(put_df, threshold=0.85)
        _, filtered_call_max = get_oi_range(call_df, threshold=0.85)
        filtered_put_min = max(filtered_put_min, most_traded_put_strike)
        filtered_call_max = min(filtered_call_max, most_traded_call_strike)
    except:
        filtered_put_min = filtered_call_max = current_price

    # 박스권 분석
    put_box_min = get_box_range_weighted(put_df, current_price, strike_distance_limit=0.3)
    call_box_max = get_box_range_weighted(call_df, current_price, strike_distance_limit=0.3)

    # 스큐 분석
    skew_threshold = 2.0
    is_significant_positive_skew = iv_skew > skew_threshold
    is_significant_negative_skew = iv_skew < -skew_threshold
    
    # 신뢰도 지수 계산
    try:
        today = datetime.datetime.utcnow()
        expiry_dt = datetime.datetime.strptime(expiry_date, "%Y-%m-%d")
        days_to_expiry = (expiry_dt - today).days
    except:
        days_to_expiry = 30  # 기본값
    
    volume_score = min((total_call_volume + total_put_volume) / 100000, 1.0)
    oi_score = min((call_df["Open Interest"].sum() + put_df["Open Interest"].sum()) / 200000, 1.0)

    # ATM 옵션 집중도 분석
    call_atm_mask = call_df["Strike"].between(current_price - 5, current_price + 5)
    put_atm_mask = put_df["Strike"].between(current_price - 5, current_price + 5)
    atm_volume = call_df[call_atm_mask]["Volume"].sum() + put_df[put_atm_mask]["Volume"].sum()
    atm_concentration = atm_volume / (total_call_volume + total_put_volume + 1e-6)
    atm_score = min(atm_concentration * 2, 1.0)

    # 시간 점수
    if 5 <= days_to_expiry <= 30:
        time_score = 1.0
    elif days_to_expiry <= 60:
        time_score = 0.7
    else:
        time_score = 0.3

    # 종합 신뢰도 지수
    reliability_index = round((
        volume_score * 0.3 +
        oi_score * 0.3 +
        atm_score * 0.2 +
        time_score * 0.2
    ), 2)

    # 신뢰도 메시지
    if reliability_index >= 0.8:
        reliability_msg = "거래량과 포지션이 풍부하며, 만기일도 적절합니다. → 매우 신뢰할 수 있습니다."
    elif reliability_index >= 0.6:
        reliability_msg = "보통 수준의 신뢰도입니다. 시장 심리 해석은 가능하지만 다소 주의가 필요합니다."
    else:
        reliability_msg = "데이터 신뢰도가 낮습니다. 해당 만기일은 참고 수준으로만 해석하세요."

    # 전략 추천
    strategy = "🔍 중립: 시장 방향성이 뚜렷하지 않음."
    
    # 전략 로직 개선 - 조건 명확화 및 중복 제거
    if bullish_sentiment:
        if not high_iv and is_significant_negative_skew:
            strategy = "🚀 매우 강한 매수 신호: 주식 매수 또는 레버리지 매수 + 저변동성 혜택 가능."
        elif high_iv and is_significant_negative_skew:
            strategy = "📈 조심스러운 매수 신호: 상승 기대는 있으나 변동성 리스크 존재."
        elif not high_iv:
            strategy = "🚀 매수 신호: 주식 매수 또는 콜 옵션 매수 유효."
        else:
            strategy = "📈 조심스러운 매수 신호: 상승 기대는 있으나 확실치 않음."
    elif bearish_sentiment:
        if not high_iv and is_significant_positive_skew:
            strategy = "⚠️ 매우 강한 매도 신호: 현물 매도 및 숏 포지션 유리 + 변동성 낮음."
        elif high_iv and is_significant_positive_skew:
            strategy = "📉 조심스러운 매도 신호: 하락 대비 심리 강화 + 변동성 주의."
        elif not high_iv:
            strategy = "⚠️ 일반 매도 신호: 방향은 약세지만 리스크는 낮음."
        else:
            strategy = "📉 조심스러운 매도 신호: 하락 대비 심리 강화이나 확실치 않음."
    else:
        if put_call_ratio > 1.2 and high_iv:
            strategy = "🧐 하락 대비 강화 중 (공포 심리 징후)"
        elif put_call_ratio < 0.8 and not high_iv:
            strategy = "👀 조심스러운 상승 기대감 (거래 약하지만 방향성 존재)"

    # 보고서 텍스트 생성
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
    - 📌 실시간 변동성: {mean_iv:.1f}%

    📈 신뢰도 분석
    - 🧮 신뢰도 지수: {reliability_index} / 1.00
    - 📘 해석: {reliability_msg}

    """.strip()
    
    # 박스권 정보 추가
    if put_box_min and call_box_max:
        report_text += f"\n\n📦 시장 참여자 예상 박스권: ${put_box_min:.1f} ~ ${call_box_max:.1f}"

    return report_text

# GUI 관련 함수들
def show_report_window(report):
    """보고서 표시 윈도우"""
    top = tk.Toplevel()
    top.title("옵션 데이터 분석 결과")
    top.geometry("700x650")

    text = tk.Text(top, wrap="word", font=("Segoe UI Emoji", 12))
    text.insert("1.0", report)
    text.config(state="disabled")
    
    # 스크롤바 추가
    scrollbar = tk.Scrollbar(top, command=text.yview)
    text.config(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text.pack(expand=True, fill="both", padx=10, pady=10)

def update_expiry_dates():
    """만기일 업데이트 - 비동기 처리"""
    ticker = ticker_entry.get().upper()
    if not ticker:
        messagebox.showerror("입력 오류", "티커명을 입력하세요!")
        return

    expiry_combo['values'] = []
    expiry_combo.set("불러오는 중...")
    
    # 로딩 표시기
    loading_label.config(text="데이터 불러오는 중...")
    loading_label.pack(pady=5)
    
    def fetch_dates():
        date_list = get_expiry_dates(ticker)
        
        # GUI 업데이트는 메인 스레드에서
        root.after(0, lambda: update_ui(date_list))
    
    def update_ui(date_list):
        if date_list:
            expiry_combo['values'] = date_list
            expiry_combo.set(date_list[0])
        else:
            expiry_combo.set("만기일 없음")
        loading_label.pack_forget()
        
    # 별도 스레드로 데이터 가져오기
    threading.Thread(target=fetch_dates, daemon=True).start()

def show_report():
    """보고서 표시 - 비동기 처리"""
    ticker = ticker_entry.get().upper()
    if not ticker:
        messagebox.showerror("입력 오류", "티커명을 입력하세요!")
        return

    selected_date = expiry_combo.get()
    if not selected_date or selected_date == "불러오는 중..." or selected_date == "만기일 없음":
        messagebox.showerror("입력 오류", "유효한 만기일을 선택하세요!")
        return
    
    # 로딩 표시기
    loading_label.config(text="분석 중...")
    loading_label.pack(pady=5)
    analyze_button.config(state=tk.DISABLED)
    
    def analyze():
        try:
            expiry_timestamp = calendar.timegm(datetime.datetime.strptime(selected_date, "%Y-%m-%d").timetuple())
            df_ticker = fetch_options_data(ticker, expiry_timestamp=expiry_timestamp)
            
            if df_ticker is None:
                root.after(0, lambda: show_error(f"{ticker}의 옵션 데이터를 가져올 수 없습니다."))
                return
                
            call_df, put_df, ticker_name = df_ticker
            report = parse_options_data(call_df, put_df, ticker_name)
            
            # GUI 업데이트는 메인 스레드에서
            root.after(0, lambda: display_report(report))
        except Exception as e:
            root.after(0, lambda: show_error(f"오류 발생: {str(e)}"))
    
    def display_report(report):
        loading_label.pack_forget()
        analyze_button.config(state=tk.NORMAL)
        show_report_window(report)
    
    def show_error(message):
        loading_label.pack_forget()
        analyze_button.config(state=tk.NORMAL)
        messagebox.showerror("분석 오류", message)
    
    # 별도 스레드로 분석 실행
    threading.Thread(target=analyze, daemon=True).start()

# GUI 구성
def create_gui():
    global root, ticker_entry, expiry_combo, analyze_button, loading_label
    
    root = tk.Tk()
    root.title("옵션 데이터 분석기")
    root.geometry("500x400")

    # 스타일 설정
    style = ttk.Style()
    style.configure('TButton', font=('Arial', 12))
    style.configure('TCombobox', font=('Arial', 12))

    # 메인 프레임
    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # 티커 입력
    tk.Label(main_frame, text="티커명을 입력하세요:", font=("Arial", 14)).pack(pady=10)
    ticker_entry = tk.Entry(main_frame, font=("Arial", 16), width=15)
    ticker_entry.pack(pady=5)

    # 만기일 선택
    tk.Label(main_frame, text="만기일 선택:", font=("Arial", 12)).pack(pady=5)
    expiry_combo = ttk.Combobox(main_frame, font=("Arial", 12), width=15)
    expiry_combo.pack(pady=5)

    # 버튼 프레임
    button_frame = tk.Frame(main_frame)
    button_frame.pack(pady=10)

    # 버튼들
    update_button = ttk.Button(button_frame, text="만기일 불러오기", command=update_expiry_dates)
    update_button.pack(side=tk.LEFT, padx=5)

    analyze_button = ttk.Button(button_frame, text="분석 시작", command=show_report, style='TButton')
    analyze_button.pack(side=tk.LEFT, padx=5)

    # 로딩 라벨 (초기에는 숨김)
    loading_label = tk.Label(main_frame, text="", font=("Arial", 10), fg="blue")
    
    # 정보 라벨
    info_label = tk.Label(main_frame, text="주의: 분석 결과는 참고용이며 투자 권유가 아닙니다.", 
                         font=("Arial", 9), fg="gray")
    info_label.pack(side=tk.BOTTOM, pady=10)

    return root

if __name__ == "__main__":
    root = create_gui()
    root.mainloop()