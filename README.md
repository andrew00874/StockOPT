# Stock Option Analysis 📈

이 프로젝트는 Yahoo Finance의 옵션 데이터를 크롤링하여 **콜 옵션(Call Option)과 풋 옵션(Put Option) 데이터를 분석**하고,
**현재 주가를 기반으로 매수/매도 추천 전략을 제공하는 Python 스크립트**입니다.

## 📌 주요 기능
- **Yahoo Finance에서 옵션 데이터 가져오기**
- **현재 주가(Yahoo Finance API 사용) 가져오기**
- **Put/Call Ratio, Implied Volatility 분석**
- **시장 심리를 고려한 매매 추천 제공**

---

## 🚀 설치 방법

### 1️⃣ 필수 패키지 설치
아래 명령어를 실행하여 프로젝트에서 필요한 모든 패키지를 한 번에 설치할 수 있습니다.

```sh
pip install -r requirements.txt
```

### 2️⃣ 실행 방법
```sh
python stock_stat.py [TICKER]
```
✅ 예제:
```sh
python stock_stat.py AAPL  # 애플 옵션 데이터 분석
python stock_stat.py TSLA  # 테슬라 옵션 데이터 분석
```

---

## 📦 프로젝트 구조
```
/stock_stat_project
│── stock_stat.py       # 메인 실행 파일
│── requirements.txt    # 필요한 패키지 목록
│── README.md           # 프로젝트 설명 문서
```

---

## 🔧 코드 설명

### **📌 옵션 데이터 크롤링**
`fetch_options_data(ticker)` 함수는 **Yahoo Finance에서 옵션 데이터를 가져옵니다.**
```python
def fetch_options_data(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}/options/"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    tables = pd.read_html(StringIO(response.text))
    return tables[0], tables[1], ticker  # Call Options, Put Options 반환
```

### **📌 현재 주가 가져오기 (`yfinance` 활용)**
`get_current_price(ticker)` 함수는 **Yahoo Finance API를 사용하여 현재 주가를 가져옵니다.**
```python
import yfinance as yf

def get_current_price(ticker):
    stock = yf.Ticker(ticker)
    price = stock.history(period="1d")["Close"].iloc[-1]
    return round(price, 2)
```

### **📌 옵션 데이터 분석 및 매매 추천**
- **Put/Call Ratio 계산**
- **Implied Volatility를 고려한 시장 심리 분석**
- **현재 주가를 기반으로 예상 Target Price 도출**
- **매수/매도 전략 추천**
```python
if bullish_sentiment and not high_iv:
    strategy = "🚀 강한 매수 신호: 롱 포지션 추천."
elif bullish_sentiment and high_iv:
    strategy = "⚠️ 조심스러운 매수: 변동성 주의."
elif not bullish_sentiment and high_iv:
    strategy = "📉 매도 신호: 현물 매도 또는 숏 포지션 고려."
else:
    strategy = "🔍 중립: 관망 추천."
```

---

## 📊 실행 결과 예시
```sh
python stock_stat.py AAPL
```

```md
📌 AAPL 옵션 데이터 기반 매매 추천 보고서

🚀 강한 매수 신호: 롱 포지션 추천.
📊 Put/Call Ratio: 0.82
📅 예상 만기일: 2025-03-14
🎯 예상 Target Price: $183.42
💰 현재 주가: $175.25
```

---

## ❓ FAQ

### **1. 특정 티커(AAPL, TSLA 등)의 현재 주가가 나오지 않는 경우?**
✅ `yfinance`가 정상적으로 설치되지 않았을 가능성이 있습니다.
아래 명령어를 실행하세요:
```sh
pip install --upgrade yfinance
```

### **2. 옵션 데이터가 크롤링되지 않는 경우?**
✅ Yahoo Finance 웹사이트 구조가 변경되었을 수 있습니다.
✅ `fetch_options_data(ticker)` 함수에서 **User-Agent를 추가하여 요청**하세요.

---

## 📌 라이선스
이 프로젝트는 **MIT 라이선스** 하에 배포됩니다.

```
MIT License
Copyright (c) 2024
```

---

## 💡 기여 방법
- **버그 수정**이나 **기능 개선 아이디어**가 있다면 Pull Request를 보내주세요!
- 문의사항은 Issues에 등록해 주세요.

---
