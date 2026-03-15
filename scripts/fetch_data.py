#!/usr/bin/env python3
"""
BVB Fear & Greed Index Calculator
Rulat zilnic de GitHub Actions. Scrie score.json in radacina repo-ului.
"""
import json
import datetime
import sys
import numpy as np

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed", file=sys.stderr)
    sys.exit(1)

# ── DATE ──────────────────────────────────────────────────────
BET_TICKER = "^BET.RO"

# Componente BET cu ticker Yahoo Finance
COMPONENTS = [
    "TLV.RO",   # Banca Transilvania
    "H2O.RO",   # Hidroelectrica
    "SNP.RO",   # OMV Petrom
    "SNG.RO",   # Romgaz
    "SNN.RO",   # Nuclearelectrica
    "BRD.RO",   # BRD Groupe SG
    "EL.RO",    # Electrica
    "TGN.RO",   # Transgaz
    "TEL.RO",   # Transelectrica
    "DIGI.RO",  # Digi Communications
    "M.RO",     # MedLife
    "ONE.RO",   # One United Properties
    "TTS.RO",   # Transport Trade Services
    "FP.RO",    # Fondul Proprietatea
]

# ── DOWNLOAD ──────────────────────────────────────────────────
def download_ticker(ticker, period="9mo"):
    """Descarca date istorice pentru un ticker. Returneaza DataFrame sau None."""
    try:
        df = yf.download(
            ticker,
            period=period,
            progress=False,
            timeout=30,
            auto_adjust=True
        )
        if df is None or len(df) < 10:
            return None
        # Flatten MultiIndex columns daca exista
        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        print(f"  WARN: {ticker} failed — {e}", file=sys.stderr)
        return None

# ── INDICATORI ────────────────────────────────────────────────

def indicator_momentum(close_series, window=125):
    """
    Momentum: pretul BET vs media mobila pe 125 zile.
    Peste medie = lacomie, sub medie = frica.
    Scor 0-100.
    """
    if close_series is None or len(close_series) < window:
        return None, {}

    price   = float(close_series.iloc[-1])
    sma     = float(close_series.iloc[-window:].mean())
    pct_diff = (price - sma) / sma * 100  # ex: +8.3% sau -5.1%

    # Normalizam: -15% = scor 0, +15% = scor 100
    score = float(np.clip((pct_diff + 15) / 30 * 100, 0, 100))

    return round(score, 1), {
        "price":   round(price, 2),
        "sma_125": round(sma, 2),
        "pct_vs_sma": round(pct_diff, 2),
    }


def indicator_volatility(close_series, window=20):
    """
    Volatilitate: deviatia standard anualizata pe 20 zile.
    Volatilitate mare = frica, mica = lacomie.
    Scor 0-100 (inversat).
    """
    if close_series is None or len(close_series) < window + 1:
        return None, {}

    returns = close_series.pct_change().dropna().iloc[-window:]
    annual_vol = float(returns.std()) * (252 ** 0.5) * 100  # in procente

    # Normalizam (inversat): 40%+ volatilitate = scor 0, 5% = scor 100
    score = float(np.clip((40 - annual_vol) / 35 * 100, 0, 100))

    return round(score, 1), {
        "annualized_vol_pct": round(annual_vol, 2),
    }


def indicator_breadth(stocks_data, window=50):
    """
    Market breadth: cate actiuni din BET sunt peste SMA 50 zile.
    Majoritate deasupra = lacomie, sub = frica.
    Scor 0-100 direct (procentul celor de deasupra SMA).
    """
    above = 0
    total = 0

    for ticker, df in stocks_data.items():
        if df is None or len(df) < window:
            continue
        close = df["Close"]
        current   = float(close.iloc[-1])
        sma_50    = float(close.iloc[-window:].mean())
        if current > sma_50:
            above += 1
        total += 1

    if total == 0:
        return None, {}

    pct_above = (above / total) * 100
    return round(pct_above, 1), {
        "above_sma50": above,
        "total_stocks": total,
    }


# ── ETICHETA ──────────────────────────────────────────────────

def score_to_label(score):
    if score is None: return "N/A"
    if score <= 20:   return "Frica extrema"
    if score <= 40:   return "Frica"
    if score <= 60:   return "Neutru"
    if score <= 80:   return "Lacomie"
    return "Lacomie extrema"


def score_to_label_en(score):
    if score is None: return "N/A"
    if score <= 20:   return "Extreme Fear"
    if score <= 40:   return "Fear"
    if score <= 60:   return "Neutral"
    if score <= 80:   return "Greed"
    return "Extreme Greed"


# ── MAIN ──────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("BVB Fear & Greed — calcul scor")
    print("=" * 50)

    # 1. Descarca BET index
    print(f"\nDescarc {BET_TICKER}...")
    bet_df = download_ticker(BET_TICKER)
    bet_close = bet_df["Close"] if bet_df is not None else None
    n_bet = len(bet_df) if bet_df is not None else 0
    print(f"  -> {n_bet} zile de date")

    # 2. Descarca componente
    print(f"\nDescarc {len(COMPONENTS)} componente BET...")
    stocks = {}
    for ticker in COMPONENTS:
        df = download_ticker(ticker)
        if df is not None:
            stocks[ticker] = df
            print(f"  + {ticker}: {len(df)} zile")
        else:
            stocks[ticker] = None
            print(f"  - {ticker}: ESUAT")

    ok_count = sum(1 for v in stocks.values() if v is not None)
    print(f"\nDate OK: {ok_count}/{len(COMPONENTS)} componente")

    # 3. Calculeaza indicatori
    print("\nCalculez indicatori...")

    mom_score, mom_data = indicator_momentum(bet_close)
    vol_score, vol_data = indicator_volatility(bet_close)
    bre_score, bre_data = indicator_breadth(stocks)

    print(f"  Momentum:    {mom_score} — {score_to_label(mom_score)}")
    print(f"  Volatilitate:{vol_score} — {score_to_label(vol_score)}")
    print(f"  Breadth:     {bre_score} — {score_to_label(bre_score)}")

    # 4. Scor compozit (ponderat)
    weights = [
        (mom_score, 0.40),  # momentum — cel mai predictiv
        (vol_score, 0.30),  # volatilitate
        (bre_score, 0.30),  # breadth
    ]
    valid = [(s, w) for s, w in weights if s is not None]

    if valid:
        composite = sum(s * w for s, w in valid) / sum(w for _, w in valid)
        composite = round(composite, 1)
    else:
        composite = None

    print(f"\n  SCOR FINAL:  {composite} — {score_to_label(composite)}")

    # 5. Scrie score.json
    output = {
        "score":     composite,
        "label_ro":  score_to_label(composite),
        "label_en":  score_to_label_en(composite),
        "updated":   datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_ro": datetime.datetime.now().strftime("%d %b %Y, %H:%M"),
        "indicators": {
            "momentum": {
                "score": mom_score,
                "label": score_to_label(mom_score),
                "weight": "40%",
                "description": "Pretul BET vs media 125 zile",
                **mom_data,
            },
            "volatility": {
                "score": vol_score,
                "label": score_to_label(vol_score),
                "weight": "30%",
                "description": "Volatilitate anualizata 20 zile (inversata)",
                **vol_data,
            },
            "breadth": {
                "score": bre_score,
                "label": score_to_label(bre_score),
                "weight": "30%",
                "description": "% actiuni BET peste SMA 50 zile",
                **bre_data,
            },
        },
        "data_quality": {
            "bet_days":          n_bet,
            "components_ok":     ok_count,
            "components_total":  len(COMPONENTS),
        },
        "disclaimer": "Scor orientativ bazat pe date publice. Nu constituie consultanta financiara.",
    }

    with open("score.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nscore.json scris cu succes.")
    print("=" * 50)
    print(json.dumps(output, ensure_ascii=False, indent=2))

    # Fail daca nu avem niciun scor valid (sa detectam problemele in CI)
    if composite is None:
        print("\nERROR: Nu s-a putut calcula scorul!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
