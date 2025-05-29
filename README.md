
# 📈 Stock Option Analysis - 옵션 데이터 분석기

Yahoo Finance에서 실시간 옵션 데이터를 수집하여  
**시장 참여자 심리 (Put/Call 비율, IV Skew, 거래량/OI 집중 등)**을 정량적으로 분석하고,  
AI 수준의 **전략 추천 메시지**를 제공하는 Python 기반 GUI 애플리케이션입니다.

---

## 🧩 주요 기능

- ✅ 콜/풋 옵션 체인 자동 수집 (`requests`, `pandas.read_html`)
- ✅ 옵션 만기일 자동 탐지 (재시도 로직 포함)
- ✅ 심리 분석 지표 계산:
  - Put/Call Volume Ratio
  - IV Skew (ATM 기준)
  - 평균 IV 및 스프레드
  - Open Interest 및 거래량 집중도
  - ATM 옵션 집중도 분석
- ✅ 전략 추천 엔진 (다단계 조건 기반)
- ✅ 신뢰도 지수 계산 (Volume, OI, ATM 비중, 만기일 기준)
- ✅ 시장 박스권 예측 (OI 누적 + 가중치 기반)
- ✅ Tkinter GUI 인터페이스
- ✅ 비동기 처리로 GUI 멈춤 없이 실행

---

## 🖥 실행 방법

### 1️⃣ 패키지 설치

```bash
pip install -r requirements.txt
```

### 2️⃣ 실행

```bash
python stock_stat.py
```

GUI 창에서 티커(AAPL, TSLA 등)를 입력하고 만기일을 선택하면  
자동으로 분석 보고서가 생성됩니다.

---

## 🔧 기술 설명

### ▶ 만기일 가져오기 (`yfinance`) 개선

```python
@lru_cache
def get_expiry_dates(ticker):
    for attempt in range(3):
        try:
            return yf.Ticker(ticker).options
        except Exception:
            time.sleep(2)
```

- 재시도 및 시간 딜레이 포함
- 빈 리스트 반환 시 에러 메시지 출력

### ▶ 옵션 데이터 수집 (`requests` + `read_html`)

```python
def fetch_options_data(ticker, expiry_timestamp):
    url = f"https://finance.yahoo.com/quote/{ticker}/options?date={expiry_timestamp}"
    tables = pd.read_html(StringIO(requests.get(url).text))
    return tables[0], tables[1]
```

### ▶ 심리 지표 계산 및 전략 판단

- Put/Call 비율
- IV Skew 및 평균 IV
- ATM 기준 집중도
- 가장 많이 거래된 행사가 분석
- 박스권(가중치 기반) 및 Open Interest 누적범위 추정
- 전략 조건 예:
  ```python
  if bullish_sentiment and not high_iv and iv_skew < -2:
      strategy = "🚀 매우 강한 매수 신호"
  ```

### ▶ 신뢰도 지수 계산 로직

```python
reliability_index = (
    volume_score * 0.3 +
    oi_score * 0.3 +
    atm_score * 0.2 +
    time_score * 0.2
)
```

- Volume, OI, ATM 집중도, 만기일 등 4가지 축 종합 평가

---

## 📊 GUI 예시

```
📌 TSLA 옵션 분석 보고서

📈 전략: 📉 조심스러운 매도 신호 (IV 높고 풋 우세)
📅 만기일: 2025-06-21
💰 현재가: $175.30

🔥 가장 활발한 옵션
- 콜: $180 (거래량: 12,300 / OI: 95,000)
- 풋: $170 (거래량: 14,400 / OI: 102,500)

🔍 Put/Call Ratio: 1.31
🔍 IV Skew: +6.2%
📈 평균 IV: 31.4%

📦 예상 박스권: $168.0 ~ $182.5
🧮 신뢰도 지수: 0.84 → 매우 신뢰할 수 있음
```

---

## 📌 리포트 해석 가이드 요약

| 지표 | 낮을 때 의미 | 높을 때 의미 |
|------|--------------|--------------|
| Put/Call Ratio | 상승 기대감 | 하락 대비 심리 |
| IV Skew | 상승 기대 (콜 우세) | 하락 우려 (풋 우세) |
| 평균 IV | 안정 시장 | 높은 기대 변동성 |
| 신뢰도 지수 | 참고용 | 고신뢰 해석 가능 |

---

## 🔁 향후 추가 예정 기능

- 옵션 체인 변화량 트래킹 (일자별 비교)
- 델타 기반 ITM/OTM 집중 분석
- 머신러닝 예측모델 연동
- 전략 추천 히스토리 저장 (CSV/DB)

---

## 🧠 기여 & 문의

기능 개선, 버그 제보, 전략 로직 제안은 언제든지 환영합니다.  
Issues 또는 PR을 통해 자유롭게 참여해주세요.

---

## 📄 라이선스

MIT License  
© 2025 Jaemin
