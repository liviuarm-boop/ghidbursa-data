#!/usr/bin/env python3
import json, datetime, os, subprocess, sys

subprocess.run([sys.executable, "-m", "pip", "install", "yfinance", "--quiet"], check=True)
import yfinance as yf

today = datetime.date.today().isoformat()

# Testăm doar TLV ca să vedem ce returnează
t = yf.Ticker("TLV.RO")

print("=== INFO ===")
try:
    info = t.info
    print(json.dumps(info, indent=2, default=str))
except Exception as e:
    print(f"INFO ERROR: {e}")

print("\n=== FAST_INFO ===")
try:
    fi = t.fast_info
    print(f"market_cap: {fi.market_cap}")
    print(f"price: {fi.last_price}")
    print(f"pe_ratio: {fi.pe_ratio}")
except Exception as e:
    print(f"FAST_INFO ERROR: {e}")

print("\n=== HISTORY ===")
try:
    hist = t.history(period="5d")
    print(hist.tail())
except Exception as e:
    print(f"HISTORY ERROR: {e}")

# Salvează JSON gol ca să nu crape workflow-ul
os.makedirs("data", exist_ok=True)
with open("data/stocks.json", "w") as f:
    json.dump({"updated": today, "stocks": {}}, f)
print("\nDone")
