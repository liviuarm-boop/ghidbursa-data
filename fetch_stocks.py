#!/usr/bin/env python3
"""
GhidBursa.ro — fetch_stocks.py
Trage date din Yahoo Finance pentru toate acțiunile BVB
și salvează în data/stocks.json

Rulează zilnic via GitHub Actions.
"""

import json
import urllib.request
import urllib.error
import datetime
import time
import os

# Map: ticker BVB → simbol Yahoo Finance
STOCKS = {
    "TLV":  "TLV.BX",
    "SNP":  "SNP.BX",
    "H2O":  "H2O.BX",
    "SNG":  "SNG.BX",
    "TGN":  "TGN.BX",
    "TEL":  "TEL.BX",
    "BRD":  "BRD.BX",
    "FP":   "FP.BX",
    "DIGI": "DIGI.BX",
    "ONE":  "ONE.BX",
    "EL":   "EL.BX",
    "M":    "M.BX",
    "SFG":  "SFG.BX",
    "TTS":  "TTS.BX",
    "COTE": "COTE.BX",
    "AQ":   "AQ.BX",
    "WINE": "WINE.BX",
    "TRP":  "TRP.BX",
    "BVB":  "BVB.BX",
    "ALR":  "ALR.BX",
}

def fetch_yahoo(symbol):
    """Trage datele din Yahoo Finance pentru un simbol."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1y"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GhidBursa/1.0)",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data
    except Exception as e:
        print(f"  ERROR {symbol}: {e}")
        return None

def fetch_yahoo_quote(symbol):
    """Trage date fundamentale (P/E, dividend etc.) din Yahoo Finance."""
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=summaryDetail,defaultKeyStatistics,financialData,price"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GhidBursa/1.0)",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data.get("quoteSummary", {}).get("result", [{}])[0]
    except Exception as e:
        print(f"  ERROR quote {symbol}: {e}")
        return {}

def calc_ytd(chart_data):
    """Calculează performanța YTD din datele chart."""
    try:
        result = chart_data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        timestamps = result["timestamp"]
        
        # Găsim primul preț din anul curent
        current_year = datetime.date.today().year
        jan1 = datetime.date(current_year, 1, 1)
        
        first_price = None
        last_price = None
        
        for ts, price in zip(timestamps, closes):
            if price is None:
                continue
            dt = datetime.date.fromtimestamp(ts)
            if dt >= jan1 and first_price is None:
                first_price = price
            last_price = price
        
        if first_price and last_price and first_price > 0:
            ytd = ((last_price - first_price) / first_price) * 100
            return round(ytd, 1)
    except Exception:
        pass
    return None

def safe_val(d, *keys, multiplier=1, decimals=2, default=None):
    """Extrage o valoare nested din dict în mod sigur."""
    try:
        v = d
        for k in keys:
            v = v[k]
        if v is None or v == {}:
            return default
        raw = v.get("raw") if isinstance(v, dict) else v
        if raw is None:
            return default
        result = round(float(raw) * multiplier, decimals)
        return result
    except Exception:
        return default

def main():
    results = {}
    today = datetime.date.today().isoformat()
    
    print(f"Fetching data for {len(STOCKS)} stocks — {today}")
    
    for ticker, yahoo_symbol in STOCKS.items():
        print(f"  {ticker} ({yahoo_symbol})...")
        
        # Date fundamentale
        quote = fetch_yahoo_quote(yahoo_symbol)
        time.sleep(0.5)  # rate limiting
        
        # Date chart pentru YTD
        chart = fetch_yahoo(yahoo_symbol)
        time.sleep(0.5)
        
        summary = quote.get("summaryDetail", {})
        key_stats = quote.get("defaultKeyStatistics", {})
        price_data = quote.get("price", {})
        
        # P/E ratio
        pe = safe_val(summary, "trailingPE", decimals=1)
        if pe is None:
            pe = safe_val(key_stats, "trailingPE", decimals=1)
        
        # Dividend yield (%)
        div_yield = safe_val(summary, "dividendYield", multiplier=100, decimals=1)
        
        # Dividend per share (RON)
        div_per_share = safe_val(summary, "dividendRate", decimals=2)
        
        # Market cap (mld RON) — Yahoo dă în RON
        market_cap_raw = safe_val(price_data, "marketCap", decimals=0)
        market_cap_bln = None
        if market_cap_raw:
            market_cap_bln = round(market_cap_raw / 1_000_000_000, 1)
        
        # EPS
        eps = safe_val(key_stats, "trailingEps", decimals=2)
        
        # YTD performance
        ytd = calc_ytd(chart) if chart else None
        
        # Current price
        price = safe_val(price_data, "regularMarketPrice", decimals=2)
        
        results[ticker] = {
            "ticker": ticker,
            "yahoo_symbol": yahoo_symbol,
            "pe": pe,
            "div_yield": div_yield,
            "div_per_share": div_per_share,
            "market_cap_bln": market_cap_bln,
            "eps": eps,
            "ytd": ytd,
            "price": price,
            "updated": today,
        }
        
        print(f"    P/E={pe} Div={div_yield}% Cap={market_cap_bln}mld YTD={ytd}%")
    
    # Salvează JSON
    os.makedirs("data", exist_ok=True)
    output = {
        "updated": today,
        "stocks": results,
    }
    
    with open("data/stocks.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\nSalvat în data/stocks.json — {len(results)} acțiuni")

if __name__ == "__main__":
    main()
