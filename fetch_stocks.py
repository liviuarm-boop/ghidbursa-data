#!/usr/bin/env python3
"""
GhidBursa.ro — fetch_stocks.py
Trage date din Yahoo Finance pentru toate acțiunile BVB
și salvează în data/stocks.json
"""

import json
import urllib.request
import datetime
import time
import os

# Map: ticker BVB → simbol Yahoo Finance (sufix .RO pentru BVB România)
STOCKS = {
    "TLV":  "TLV.RO",
    "SNP":  "SNP.RO",
    "H2O":  "H2O.RO",
    "SNG":  "SNG.RO",
    "TGN":  "TGN.RO",
    "TEL":  "TEL.RO",
    "BRD":  "BRD.RO",
    "FP":   "FP.RO",
    "DIGI": "DIGI.RO",
    "ONE":  "ONE.RO",
    "EL":   "EL.RO",
    "M":    "M.RO",
    "SFG":  "SFG.RO",
    "TTS":  "TTS.RO",
    "COTE": "COTE.RO",
    "AQ":   "AQ.RO",
    "WINE": "WINE.RO",
    "TRP":  "TRP.RO",
    "BVB":  "BVB.RO",
    "ALR":  "ALR.RO",
}

def fetch_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())

def fetch_quote_summary(symbol):
    url = (
        f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
        f"?modules=summaryDetail,defaultKeyStatistics,price"
    )
    try:
        data = fetch_url(url)
        result = data.get("quoteSummary", {}).get("result", [])
        return result[0] if result else {}
    except Exception as e:
        print(f"    quote error {symbol}: {e}")
        return {}

def fetch_chart(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1y"
    try:
        return fetch_url(url)
    except Exception as e:
        print(f"    chart error {symbol}: {e}")
        return None

def calc_ytd(chart_data):
    try:
        result = chart_data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        timestamps = result["timestamp"]
        current_year = datetime.date.today().year
        jan1 = datetime.date(current_year, 1, 1)
        first_price = None
        last_price = None
        for ts, price in zip(timestamps, closes):
            if price is None:
                continue
            if datetime.date.fromtimestamp(ts) >= jan1 and first_price is None:
                first_price = price
            last_price = price
        if first_price and last_price and first_price > 0:
            return round(((last_price - first_price) / first_price) * 100, 1)
    except Exception:
        pass
    return None

def safe(d, *keys, mult=1, dec=2):
    try:
        v = d
        for k in keys:
            v = v[k]
        raw = v.get("raw") if isinstance(v, dict) else v
        if raw is None:
            return None
        return round(float(raw) * mult, dec)
    except Exception:
        return None

def main():
    results = {}
    today = datetime.date.today().isoformat()
    print(f"Fetching {len(STOCKS)} stocks — {today}\n")

    for ticker, symbol in STOCKS.items():
        print(f"  {ticker} ({symbol})...", end=" ", flush=True)

        quote = fetch_quote_summary(symbol)
        time.sleep(0.8)
        chart = fetch_chart(symbol)
        time.sleep(0.8)

        summary   = quote.get("summaryDetail", {})
        key_stats = quote.get("defaultKeyStatistics", {})
        price_d   = quote.get("price", {})

        pe        = safe(summary, "trailingPE", dec=1) or safe(key_stats, "trailingPE", dec=1)
        div_yield = safe(summary, "dividendYield", mult=100, dec=1)
        div_ps    = safe(summary, "dividendRate", dec=2)
        cap_raw   = safe(price_d, "marketCap", dec=0)
        cap_bln   = round(cap_raw / 1e9, 1) if cap_raw else None
        eps       = safe(key_stats, "trailingEps", dec=2)
        ytd       = calc_ytd(chart) if chart else None
        price     = safe(price_d, "regularMarketPrice", dec=2)

        results[ticker] = {
            "ticker": ticker,
            "pe": pe,
            "div_yield": div_yield,
            "div_per_share": div_ps,
            "market_cap_bln": cap_bln,
            "eps": eps,
            "ytd": ytd,
            "price": price,
            "updated": today,
        }
        print(f"P/E={pe} Div={div_yield}% Cap={cap_bln}mld YTD={ytd}%")

    os.makedirs("data", exist_ok=True)
    with open("data/stocks.json", "w", encoding="utf-8") as f:
        json.dump({"updated": today, "stocks": results}, f, ensure_ascii=False, indent=2)

    nulls = sum(1 for s in results.values() if all(v is None for k, v in s.items() if k not in ("ticker", "updated")))
    print(f"\nSalvat data/stocks.json — {len(results)} acțiuni, {nulls} fără date")

if __name__ == "__main__":
    main()
