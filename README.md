
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

# 📈 옵션 심리 분석 리포트 - 지표 해석 가이드

이 분석기는 Yahoo Finance의 실시간 옵션 데이터를 기반으로 시장 참여자들의 심리를 다양한 지표로 분석합니다.  
아래는 리포트에 나오는 주요 지표들의 의미와 해석 방법을 정리한 내용입니다.

---

## 🔄 Put/Call Ratio

- **정의:** 풋 옵션 거래량 ÷ 콜 옵션 거래량  
- **시장 심리 해석:**

| 비율(Put/Call) | 해석 |
|----------------|------|
| **< 0.7**      | 투자자들이 상승에 더 베팅하고 있음 (강한 매수 심리) |
| **0.7 ~ 1.0**  | 중립 또는 약한 상승 기대감 |
| **> 1.0**      | 하락에 대한 대비 심리, 약세 경계 (풋 거래 비중 ↑) |
| **> 1.3**      | 강한 하락 우려 또는 공포 심리 반영 |

> 🔍 **낮을수록** 투자자들은 시장 상승을 기대하고, **높을수록** 하락 대비에 집중합니다.

---

## 🔄 IV Skew (Implied Volatility Skew)

- **정의:** ATM(등가격) 기준 풋 옵션 IV - 콜 옵션 IV  
- **시장 심리 해석:**

| IV Skew 값 | 해석 |
|------------|------|
| **> 0**    | 풋 옵션 IV가 높음 → 하락 대비 수요 증가 (하락 리스크 우려) |
| **< 0**    | 콜 옵션 IV가 높음 → 상승 기대감 존재 |
| **= 0**    | 대칭적 → 상승/하락에 대해 중립적 기대 |

> 예: `+5%` → 풋 쪽에 더 높은 보험 수요 있음 → 하락 방어 심리  
> 예: `-3%` → 콜 쪽이 더 비쌈 → 상승 기대감 반영

---

## 📌 실시간 변동성 (IV 평균)

- **정의:** 전체 콜 옵션들의 평균 암묵적 변동성 (Implied Volatility)
- **해석:**

| 평균 IV (%) | 시장 상태 |
|-------------|-----------|
| **< 20%**   | 안정된 시장 (변동성 낮음) |
| **20 ~ 35%**| 보통 수준의 기대 변동성 |
| **> 35%**   | 높은 변동성 기대 (이벤트/뉴스 가능성) |
| **> 50%**   | 극단적 공포 또는 급등/급락 가능성 내포 |

> IV가 높을수록 프리미엄이 비싸지며 옵션 매수자는 신중해야 합니다.

---

## 🔥 거래량 + OI (Open Interest)

- **Volume:** 특정 옵션이 당일 얼마나 활발히 거래되었는가를 나타냄  
- **Open Interest:** 해당 옵션에 여전히 열려있는 계약 수 → 누적 포지션

### 심리 해석:

- **거래량이 많고 OI도 많다:** 신규 진입 + 강한 관심도 → 시장의 핵심 포인트
- **거래량은 많지만 OI는 낮다:** 단기 매매 중심 (단타 세력)
- **OI만 높고 거래량은 적다:** 장기 보유 포지션 / 과거 포지션 유지 중

---

## 🧭 박스권 해석 (조정된 박스권)

이 박스권은 상위 85% OI 구간 + 가장 활발한 거래 행사가 기준으로 계산됩니다.

- **하단 = 주요 지지선 (Put 수요가 집중된 가격대)**
- **상단 = 주요 저항선 (Call 수요가 집중된 가격대)**

해당 구간에 있을수록 시장은 **그 범위 내에서 움직일 가능성이 높다**고 참여자들이 판단하고 있음을 뜻합니다.

---

## 📌 요약

| 지표 | 낮을 때 의미 | 높을 때 의미 |
|------|--------------|--------------|
| Put/Call Ratio | 낙관 (상승 심리) | 비관 (하락 대비) |
| IV Skew | 상승 기대 | 하락 우려 |
| 평균 IV | 안정 | 불안정/변동성 ↑ |
| OI | 관심 적음 | 시장 집중 구간 |

---

🧠 이 가이드를 참고하여 리포트 데이터를 더 정확하게 해석하고  
당일 시장 흐름과 참여자 심리를 빠르게 파악해보세요!


---

## 🧠 기여 & 문의

- PR, 이슈 환영합니다.
- 기능 개선, 추가 지표 요청은 [Issues] 탭에 자유롭게 남겨주세요.

---

## 📄 라이선스

MIT License  
Copyright (c) 2024
