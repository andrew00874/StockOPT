
# 📈 Stock Option Analysis - 옵션 데이터 분석기

이 프로젝트는 Yahoo Finance에서 **실시간 옵션 데이터를 수집하고 분석**하여,  
**시장 참여자들의 심리(Put/Call Ratio, IV Skew, Open Interest 등)**를 정량적으로 해석하고,  
**매수/매도 전략을 추천하는 Python 기반 GUI 애플리케이션**입니다.

---

## 🧩 주요 기능

- ✅ 콜/풋 옵션 데이터 수집 (Yahoo Finance 크롤링)
- ✅ 현재 주가 실시간 조회 (`yfinance`)
- ✅ 시장 심리 지표 계산:
  - Put/Call Ratio
  - IV Skew
  - 평균 Implied Volatility
  - 거래량/미결제약정 분석
- ✅ Tkinter 기반 GUI
- ✅ 전략 메시지 자동 생성 및 박스권 범위 추정

---

## 🖥 실행 방법

### 1️⃣ 필수 패키지 설치

```bash
pip install -r requirements.txt
```

`requirements.txt`에는 다음과 같은 패키지가 포함됩니다:
```
pandas
requests
yfinance
tkinter  # Windows에서는 기본 포함됨
```

### 2️⃣ 실행

```bash
python stock_stat.py
```

실행 후 GUI 창이 열리며, 티커(예: AAPL, TSLA 등)를 입력하면 리포트를 생성합니다.

---

## 📦 프로젝트 구조

```
/stock_stat_project
│
├── stock_stat.py        # 메인 GUI 및 분석 코드
├── requirements.txt     # 필요한 패키지 목록
└── README.md            # 이 문서
```

---

## 🔧 코드 설명 (최신 기준)

### 📌 옵션 데이터 크롤링

```python
def fetch_options_data(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}/options/"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    tables = pd.read_html(StringIO(response.text))
    return tables[0], tables[1], ticker  # Call / Put
```

### 📌 현재 주가 조회

```python
def get_current_price(ticker):
    stock = yf.Ticker(ticker)
    price = stock.history(period="1d")["Close"].iloc[-1]
    return round(price, 2)
```

### 📌 핵심 심리 지표 분석

- Put/Call 거래량 비율
- ATM 기준 IV Skew (풋 IV - 콜 IV)
- 전체 콜 옵션 평균 IV
- 거래량 + OI 기반 박스권 추정

### 📌 전략 판단 로직

```python
if bullish_sentiment and not high_iv and iv_skew < 0:
    strategy = "🚀 매우 강한 매수 신호..."
elif bearish_sentiment and high_iv and iv_skew > 0:
    strategy = "⚠️ 시장 하락 대비 강함..."
...
```

### 📌 GUI (Tkinter)

```python
root = tk.Tk()
ticker_entry = tk.Entry(root)
...
analyze_button = tk.Button(root, text="분석 시작", command=show_report)
```

---

## 📊 실행 결과 예시 (GUI 창)

```
📌 AAPL 옵션 데이터 분석 보고서

🚀 매우 강한 매수 신호: 주식 매수 또는 콜 옵션 매수 + 저변동성 혜택 가능.

📅 옵션 만기일: 2025-03-14
💰 현재 주가: $175.25

🔥 거래량 TOP 옵션 (거래량 + OI 추가)
- 📈 콜 옵션 행사가: $180 (거래량: 15,320, OI: 92,000)
- 📉 풋 옵션 행사가: $170 (거래량: 12,100, OI: 88,400)

📊 시장 심리 분석
- 🔄 Put/Call Ratio: 0.79
- 🔄 IV Skew (Put - Call): 3.21%
- 📌 실시간 변동성: 24.3%
```

---

## 📘 지표 해석 가이드

각 지표별 해석은 [`옵션 심리 분석 리포트 - 지표 해석 가이드`](#📈-옵션-심리-분석-리포트---지표-해석-가이드) 섹션을 참고하세요.

---

## 🧠 기여 & 문의

- PR, 이슈 환영합니다.
- 기능 개선, 추가 지표 요청은 [Issues] 탭에 자유롭게 남겨주세요.

---

## 📄 라이선스

MIT License  
Copyright (c) 2024
