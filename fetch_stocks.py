#!/usr/bin/env python3
"""
GhidBursa.ro — fetch_stocks.py
Trage date din Yahoo Finance pentru toate acțiunile BVB
"""

import json, datetime, os, subprocess, sys

subprocess.run([sys.executable, "-m", "pip", "install", "yfinance", "--quiet"], check=True)
import yfinance as yf

STOCKS = {
    "TLV":  "TLV.RO",  "SNP":  "SNP.RO",  "H2O":  "H2O.RO",
    "SNG":  "SNG.RO",  "TGN":  "TGN.RO",  "TEL":  "TEL.RO",
    "BRD":  "BRD.RO",  "FP":   "FP.RO",   "DIGI": "DIGI.RO",
    "ONE":  "ONE.RO",  "EL":   "EL.RO",   "M":    "M.RO",
    "SFG":  "SFG.RO",  "TTS":  "TTS.RO",  "COTE": "COTE.RO",
    "AQ":   "AQ.RO",   "WINE": "WINE.RO", "TRP":  "TRP.RO",
    "BVB":  "BVB.RO",  "ALR":  "ALR.RO",
}

def calc_ytd(hist):
    try:
        jan1 = datetime.date(datetime.date.today().year, 1, 1)
        h = hist[hist.index.date >= jan1]
        if len(h) < 2:
            return None
        first = float(h["Close"].iloc[0])
        last  = float(h["Close"].iloc[-1])
        return round(((last - first) / first) * 100, 1) if first > 0 else None
    except Exception:
        return None

def r(val, dec=2):
    try:
        return round(float(val), dec) if val is not None else None
    except Exception:
        return None

def main():
    results = {}
    today = datetime.date.today().isoformat()
    print(f"Fetching {len(STOCKS)} stocks — {today}\n")

    for ticker, symbol in STOCKS.items():
        print(f"  {ticker}...", end=" ", flush=True)
        try:
            t    = yf.Ticker(symbol)
            info = t.info
            hist = t.history(period="1y")

            # dividendYield vine ca procent direct (ex: 5.88) pe .RO
            div_yield = r(info.get("dividendYield"), 1)

            # Dacă e sub 1.0 înseamnă că e zecimală — înmulțim
            if div_yield and div_yield < 1.0:
                div_yield = round(div_yield * 100, 1)

            cap_raw = info.get("marketCap")

            results[ticker] = {
                "ticker":         ticker,
                "pe":             r(info.get("trailingPE"), 1),
                "div_yield":      div_yield,
                "div_per_share":  r(info.get("lastDividendValue") or info.get("dividendRate"), 2),
                "market_cap_bln": round(cap_raw / 1e9, 1) if cap_raw else None,
                "eps":            r(info.get("trailingEps"), 2),
                "ytd":            calc_ytd(hist),
                "price":          r(info.get("regularMarketPrice") or info.get("currentPrice"), 2),
                "updated":        today,
            }
            s = results[ticker]
            print(f"P/E={s['pe']} Div={s['div_yield']}% Cap={s['market_cap_bln']}mld YTD={s['ytd']}%")

        except Exception as e:
            print(f"ERROR: {e}")
            results[ticker] = {"ticker": ticker, "pe": None, "div_yield": None,
                "div_per_share": None, "market_cap_bln": None,
                "eps": None, "ytd": None, "price": None, "updated": today}

    os.makedirs("data", exist_ok=True)
    with open("data/stocks.json", "w", encoding="utf-8") as f:
        json.dump({"updated": today, "stocks": results}, f, ensure_ascii=False, indent=2)

    ok = sum(1 for s in results.values() if s.get("pe") or s.get("div_yield"))
    print(f"\nSalvat data/stocks.json — {ok}/{len(results)} cu date fundamentale")

if __name__ == "__main__":
    main()
