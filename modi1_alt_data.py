import pandas as pd
import yfinance as yf
from pytrends.request import TrendReq
import time
import os
import sys
from datetime import datetime as _dt

_now = _dt.now()
_market_start = _now.replace(hour=9, minute=15, second=0, microsecond=0)
_market_end = _now.replace(hour=15, minute=30, second=0, microsecond=0)
if _now < _market_start or _now > _market_end:
    print(f"Outside market hours ({_now.strftime('%H:%M:%S')}), skipping run.")
    exit()
from intraday_watchlist import INTRADAY_SYMBOLS

LOCK_FILE = "alt_data.lock"
if os.path.exists(LOCK_FILE):
    print("Previous alt-data run still in progress, skipping.")
    sys.exit(0)
with open(LOCK_FILE, "w") as f:
    f.write("running")


class Modi1AltDataEngine:
    def __init__(self, stock_tickers):
        self.tickers = stock_tickers
        self.pytrends = TrendReq(hl='en-IN', tz=330)

    def get_search_term(self, ticker):
        """Get a clean company name to search Google Trends for."""
        try:
            info = yf.Ticker(ticker + ".NS").info
            name = info.get("shortName") or info.get("longName")
            if name:
                for suffix in [" Ltd.", " Ltd", " Limited", " Industries", " Pharma Ltd"]:
                    if name.endswith(suffix):
                        name = name[: -len(suffix)]
                return name.strip()
        except Exception:
            pass
        return ticker

    def fetch_batch_momentum(self, batch):
        """batch: list of (ticker, search_term) tuples, max 5."""
        terms = [t[1] for t in batch]
        results = {}
        try:
            self.pytrends.build_payload(terms, cat=0, timeframe='today 1-m', geo='IN')
            interest_df = self.pytrends.interest_over_time()
            for ticker, term in batch:
                if term in interest_df.columns and not interest_df.empty:
                    recent_avg = interest_df[term].tail(7).mean()
                    historical_avg = interest_df[term].head(23).mean()
                    if historical_avg == 0:
                        results[ticker] = 0.0
                    else:
                        momentum = ((recent_avg - historical_avg) / historical_avg) * 100
                        results[ticker] = round(momentum, 2)
                else:
                    results[ticker] = None
        except Exception as e:
            print(f"  Batch error ({terms}): {e}")
            for ticker, _ in batch:
                results[ticker] = None
        return results

    def generate_alt_data_report(self):
        print("Resolving company names...")
        ticker_terms = []
        for ticker in self.tickers:
            term = self.get_search_term(ticker)
            ticker_terms.append((ticker, term))
            time.sleep(0.3)

        results = []
        batch_size = 5
        total_batches = (len(ticker_terms) + batch_size - 1) // batch_size
        for i in range(0, len(ticker_terms), batch_size):
            batch = ticker_terms[i:i + batch_size]
            batch_num = i // batch_size + 1
            print(f"[Batch {batch_num}/{total_batches}] Fetching: {[t[1] for t in batch]}")
            batch_results = self.fetch_batch_momentum(batch)
            for ticker, term in batch:
                results.append({
                    'symbol': ticker,
                    'Search Term': term,
                    'Momentum (%)': batch_results.get(ticker)
                })
            time.sleep(10)

        return pd.DataFrame(results)


if __name__ == "__main__":
    modi1_engine = Modi1AltDataEngine(INTRADAY_SYMBOLS)
    alt_data_df = modi1_engine.generate_alt_data_report()
    print("\n--- MODI1 Alternative Data Output ---")
    print(alt_data_df)
    alt_data_df.to_csv("alt_data_momentum.csv", index=False)
    print("\nSaved to alt_data_momentum.csv")

if os.path.exists(LOCK_FILE):
    os.remove(LOCK_FILE)