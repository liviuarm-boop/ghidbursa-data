Output

#!/usr/bin/env python3
"""
BVB Fear & Greed Index Calculator v2
- BET index: Stooq.com (bet.xb) — mai fiabil decat Yahoo
- Componente: Yahoo Finance (.RO) — deja functioneaza
- Fallback: reconstruieste BET din componente ponderate
"""
import json, datetime, sys, io, urllib.request
import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed", file=sys.stderr); sys.exit(1)

STOOQ_BET = "https://stooq.com/q/d/l/?s=bet.xb&i=d"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

COMPONENTS = {
    "H2O.RO": 0.22, "TLV.RO": 0.18, "SNP.RO": 0.12, "SNG.RO": 0.10,
    "SNN.RO": 0.08, "BRD.RO": 0.07, "EL.RO":  0.06, "TGN.RO": 0.04,
    "TEL.RO": 0.03, "DIGI.RO":0.03, "M.RO":   0.02, "ONE.RO": 0.02,
    "TTS.RO": 0.02, "FP.RO":  0.01,
}

def dl_stooq():
    try:
        req = urllib.request.Request(STOOQ_BET, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(raw), parse_dates=["Date"])
        df = df.sort_values("Date").reset_index(drop=True)
        if len(df) < 10: return None
        close = df.set_index("Date")["Close"]
        print(f"  + Stooq BET: {len(close)} zile, last={close.iloc[-1]:.2f}")
        return close
    except Exception as e:
        print(f"  - Stooq: {e}", file=sys.stderr); return None

def dl_yf(ticker, period="9mo"):
    try:
        df = yf.download(ticker, period=period, progress=False, timeout=30, auto_adjust=True)
        if df is None or len(df) < 10: return None
        if hasattr(df.columns, "levels"): df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        print(f"  - {ticker}: {e}", file=sys.stderr); return None

def reconstruct_bet(stocks):
    series_list, weights_list = [], []
    for ticker, weight in COMPONENTS.items():
        df = stocks.get(ticker)
        if df is None or len(df) < 50: continue
        norm = df["Close"] / df["Close"].iloc[0]
        series_list.append(norm); weights_list.append(weight)
    if not series_list: return None
    combined = pd.concat(series_list, axis=1).dropna()
    if len(combined) < 50: return None
    w = np.array(weights_list[:len(series_list)]); w = w / w.sum()
    # Result is a weighted ratio starting near 1.0 at period start
    result = pd.Series(combined.values @ w, index=combined.index) * 100
    print(f"  + BET reconstruit din {len(series_list)} componente: {len(result)} zile")
    return result

def momentum(close, n=125):
    if close is None or len(close) < n: return None, {}
    p = float(close.iloc[-1]); sma = float(close.iloc[-n:].mean())
    pct = (p - sma) / sma * 100
    return round(float(np.clip((pct+30)/60*100, 0, 100)), 1), {
        "price": round(p,2), "sma_125": round(sma,2), "pct_vs_sma": round(pct,2)}

def volatility(close, n=20):
    if close is None or len(close) < n+1: return None, {}
    ann = float(close.pct_change().dropna().iloc[-n:].std()) * (252**0.5) * 100
    return round(float(np.clip((40-ann)/35*100, 0, 100)), 1), {"annualized_vol_pct": round(ann,2)}

def breadth(stocks, n=50):
    above = total = 0
    for df in stocks.values():
        if df is None or len(df) < n: continue
        c = df["Close"]
        if float(c.iloc[-1]) > float(c.iloc[-n:].mean()): above += 1
        total += 1
    if not total: return None, {}
    return round(above/total*100, 1), {"above_sma50": above, "total_stocks": total}

def label_ro(s):
    if s is None: return "N/A"
    if s <= 20: return "Frica extrema"
    if s <= 40: return "Frica"
    if s <= 60: return "Neutru"
    if s <= 80: return "Lacomie"
    return "Lacomie extrema"

def label_en(s):
    if s is None: return "N/A"
    if s <= 20: return "Extreme Fear"
    if s <= 40: return "Fear"
    if s <= 60: return "Neutral"
    if s <= 80: return "Greed"
    return "Extreme Greed"

def main():
    print("="*55 + "\nBVB Fear & Greed v2\n" + "="*55)

    print("\n[1] Componente BET (Yahoo Finance)...")
    stocks = {}
    for t in COMPONENTS:
        df = dl_yf(t)
        stocks[t] = df
        print(f"  {'+'if df is not None else '-'} {t}: {len(df) if df is not None else 'FAIL'}")
    ok = sum(1 for v in stocks.values() if v is not None)
    print(f"  OK: {ok}/{len(COMPONENTS)}")

    print("\n[2] BET index (Stooq)...")
    bet = dl_stooq()
    if bet is None:
        print("  Stooq esuat, reconstruiesc din componente...")
        bet = reconstruct_bet(stocks)
    bet_source = "stooq" if bet is not None and "reconstruit" not in str(bet) else "reconstructed" if bet is not None else "unavailable"

    print("\n[3] Indicatori...")
    ms, md = momentum(bet)
    vs, vd = volatility(bet)
    bs, bd = breadth(stocks)
    print(f"  Momentum:     {ms} — {label_ro(ms)}")
    print(f"  Volatilitate: {vs} — {label_ro(vs)}")
    print(f"  Breadth:      {bs} — {label_ro(bs)}")

    if ms is not None and vs is not None and bs is not None:
        w = [(ms,0.40),(vs,0.30),(bs,0.30)]; method = "3 indicatori completi"
    elif bs is not None:
        w = [(bs,1.0)]; method = "breadth (BET indisponibil)"
    else:
        w = []; method = "fara date"

    valid = [(s,wt) for s,wt in w if s is not None]
    comp = round(sum(s*wt for s,wt in valid)/sum(wt for _,wt in valid),1) if valid else None
    print(f"\n  SCOR: {comp} — {label_ro(comp)} ({method})")

    out = {
        "score": comp, "label_ro": label_ro(comp), "label_en": label_en(comp),
        "updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_ro": datetime.datetime.now().strftime("%d %b %Y, %H:%M"),
        "method": method,
        "indicators": {
            "momentum":   {"score": ms, "label": label_ro(ms), "weight": "40%", "description": "Pretul BET vs SMA 125 zile", **md},
            "volatility": {"score": vs, "label": label_ro(vs), "weight": "30%", "description": "Volatilitate anualizata 20 zile", **vd},
            "breadth":    {"score": bs, "label": label_ro(bs), "weight": "30%", "description": "% actiuni BET peste SMA 50 zile", **bd},
        },
        "data_quality": {"bet_source": bet_source, "bet_days": len(bet) if bet is not None else 0, "components_ok": ok, "components_total": len(COMPONENTS)},
        "disclaimer": "Scor orientativ bazat pe date publice. Nu constituie consultanta financiara.",
    }
    with open("score.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nscore.json scris.")
    if comp is None: print("ERROR: scor null!", file=sys.stderr); sys.exit(1)

if __name__ == "__main__":
    main()
