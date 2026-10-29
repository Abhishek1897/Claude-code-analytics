"""Trading Desk: signal engine, wealth forecaster and dashboard builder.

    python wealth_tracker.py                 # build dashboard.html
    python wealth_tracker.py --regen-prices  # re-create the simulated prices.csv first

Pipeline
  1. Prices    - daily closes for 20 assets from prices.csv (date, ticker, name,
                 asset_class, close[, source]). If missing, a seeded *simulated*
                 history is generated so the desk works offline. Swap in real
                 closes with the same columns and nothing else changes.
  2. Signals   - 14-period RSI (Wilder smoothing) per asset.
                 RSI < 30 -> BUY (oversold), RSI > 70 -> CAUTION (overbought).
                 Written to signals.csv.
  3. Forecast  - Future Wealth: lump sum and/or monthly contribution (DCA)
                 projected 12 months ahead at fixed assumed annual growth rates.
  4. Dashboard - dashboard.html (self-contained, opens from disk): signals table,
                 Future Wealth forecaster, and the cash ledger from cleaned_data.csv.
"""
import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "templates" / "trading_desk.html"

# --- Configuration ---------------------------------------------------------------
RSI_PERIOD = 14
OVERSOLD = 30      # RSI below this -> BUY
OVERBOUGHT = 70    # RSI above this -> CAUTION

# Forecaster assumptions. Annual rates are effective (compounded monthly), so a
# lump sum held 12 months grows by exactly the annual rate.
GROWTH_RATES = {"Stocks": 0.10, "Crypto": 0.30}
HORIZON_MONTHS = 12

# Universe for the simulated history:
# (ticker, name, class, starting price, daily volatility, drift over the last 20 periods)
# The recent drift gives the sample a mix of trending and range-bound assets.
ASSETS = [
    ("AAPL",  "Apple",               "Stocks", 228.0,  0.015,  0.0000),
    ("MSFT",  "Microsoft",           "Stocks", 432.0,  0.014,  0.0040),
    ("NVDA",  "NVIDIA",              "Stocks", 138.0,  0.030,  0.0120),
    ("AMZN",  "Amazon",              "Stocks", 186.0,  0.020, -0.0010),
    ("GOOGL", "Alphabet",            "Stocks", 166.0,  0.018,  0.0015),
    ("META",  "Meta Platforms",      "Stocks", 575.0,  0.022,  0.0090),
    ("TSLA",  "Tesla",               "Stocks", 250.0,  0.035, -0.0150),
    ("JPM",   "JPMorgan Chase",      "Stocks", 222.0,  0.013,  0.0005),
    ("V",     "Visa",                "Stocks", 290.0,  0.012,  0.0020),
    ("JNJ",   "Johnson & Johnson",   "Stocks", 160.0,  0.010, -0.0060),
    ("XOM",   "Exxon Mobil",         "Stocks", 118.0,  0.016, -0.0020),
    ("KO",    "Coca-Cola",           "Stocks",  70.0,  0.009,  0.0000),
    ("BTC",   "Bitcoin",             "Crypto", 68000., 0.030,  0.0080),
    ("ETH",   "Ethereum",            "Crypto", 2600.0, 0.038, -0.0030),
    ("SOL",   "Solana",              "Crypto", 170.0,  0.050,  0.0160),
    ("BNB",   "BNB",                 "Crypto", 590.0,  0.030,  0.0010),
    ("XRP",   "XRP",                 "Crypto",   0.55, 0.045, -0.0050),
    ("ADA",   "Cardano",             "Crypto",   0.36, 0.050, -0.0180),
    ("DOGE",  "Dogecoin",            "Crypto",   0.13, 0.060,  0.0050),
    ("AVAX",  "Avalanche",           "Crypto",  27.0,  0.055, -0.0220),
]
HISTORY_DAYS = 90   # calendar days of history to simulate


# --- 1. Prices -----------------------------------------------------------------------
def generate_sample_prices(path, end=None, seed=7):
    """Write a reproducible simulated price history. Stocks trade on weekdays,
    crypto every day. Not real market data."""
    end = pd.Timestamp(end or date.today())
    start = end - pd.Timedelta(days=HISTORY_DAYS)
    rng = np.random.default_rng(seed)
    rows = []
    for ticker, name, cls, p0, vol, recent_drift in ASSETS:
        days = pd.bdate_range(start, end) if cls == "Stocks" else pd.date_range(start, end)
        n = len(days)
        drift = np.zeros(n)
        drift[-20:] = recent_drift
        returns = rng.normal(drift, vol)
        closes = p0 * np.exp(np.cumsum(returns))
        rows += [(d.date().isoformat(), ticker, name, cls, round(float(c), 6), "simulated")
                 for d, c in zip(days, closes)]
    df = pd.DataFrame(rows, columns=["date", "ticker", "name", "asset_class", "close", "source"])
    df.to_csv(path, index=False)
    return df


def load_prices(path, regen=False):
    if regen or not Path(path).exists():
        generate_sample_prices(path)
        print(f"Generated simulated prices -> {path}")
    df = pd.read_csv(path, parse_dates=["date"])
    missing = {"date", "ticker", "name", "asset_class", "close"} - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    return df.sort_values(["ticker", "date"]).reset_index(drop=True)


# --- 2. Signal engine ------------------------------------------------------------------
def rsi(closes, period=RSI_PERIOD):
    """Wilder's RSI. Returns a Series aligned to `closes`; the first `period`
    values are NaN (not enough history yet)."""
    closes = pd.Series(closes, dtype=float).reset_index(drop=True)
    delta = closes.diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    out = pd.Series(np.nan, index=closes.index)
    if len(closes) <= period:
        return out
    avg_gain = gain.iloc[1:period + 1].mean()     # seed: simple average of the first `period` moves
    avg_loss = loss.iloc[1:period + 1].mean()
    for i in range(period, len(closes)):
        if i > period:                            # then Wilder smoothing
            avg_gain = (avg_gain * (period - 1) + gain.iloc[i]) / period
            avg_loss = (avg_loss * (period - 1) + loss.iloc[i]) / period
        if avg_loss == 0:
            out.iloc[i] = 100.0 if avg_gain > 0 else 50.0
        else:
            out.iloc[i] = 100 - 100 / (1 + avg_gain / avg_loss)
    return out


def classify(value):
    if pd.isna(value):
        return "N/A"
    if value < OVERSOLD:
        return "BUY"
    if value > OVERBOUGHT:
        return "CAUTION"
    return "NEUTRAL"


def build_signals(prices):
    rows = []
    for ticker, g in prices.groupby("ticker", sort=False):
        closes = g["close"].reset_index(drop=True)
        r = rsi(closes)
        last, prev = closes.iloc[-1], closes.iloc[-2]
        rows.append({
            "ticker": ticker,
            "name": g["name"].iloc[0],
            "asset_class": g["asset_class"].iloc[0],
            "as_of": g["date"].iloc[-1].date().isoformat(),
            "close": last,
            "change_1d_pct": (last / prev - 1) * 100,
            "change_14d_pct": (last / closes.iloc[-1 - RSI_PERIOD] - 1) * 100
                              if len(closes) > RSI_PERIOD else np.nan,
            "rsi_14": r.iloc[-1],
            "signal": classify(r.iloc[-1]),
            "spark": closes.tail(30).round(6).tolist(),
        })
    return pd.DataFrame(rows)


# --- 3. Forecaster ----------------------------------------------------------------------
def forecast(lump_sum, monthly, annual_rate, months=HORIZON_MONTHS):
    """Projected value after `months`. Monthly contributions are invested at the
    start of each month, so the first one compounds for the full period."""
    m = (1 + annual_rate) ** (1 / 12) - 1
    lump_fv = lump_sum * (1 + m) ** months
    dca_fv = sum(monthly * (1 + m) ** k for k in range(1, months + 1))
    return {"lump": lump_fv, "dca": dca_fv, "total": lump_fv + dca_fv,
            "invested": lump_sum + monthly * months}


# --- 4. Dashboard --------------------------------------------------------------------------
def load_ledger(path):
    if not Path(path).exists():
        return []
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    return json.loads(df.to_json(orient="records"))


def build_dashboard(signals, ledger, out, simulated):
    sig_records = json.loads(signals.round({"close": 6, "change_1d_pct": 2, "change_14d_pct": 2,
                                            "rsi_14": 1}).to_json(orient="records"))
    config = {"rsiPeriod": RSI_PERIOD, "oversold": OVERSOLD, "overbought": OVERBOUGHT,
              "asOf": signals["as_of"].max(), "simulated": simulated}
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__SIGNALS__", json.dumps(sig_records))
            .replace("__LEDGER__", json.dumps(ledger))
            .replace("__CONFIG__", json.dumps(config))
            .replace("__RATES__", json.dumps(GROWTH_RATES))
            .replace("__HORIZON__", str(HORIZON_MONTHS)))
    Path(out).write_text(html, encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prices", default=str(ROOT / "prices.csv"))
    ap.add_argument("--ledger", default=str(ROOT / "cleaned_data.csv"))
    ap.add_argument("--signals-out", default=str(ROOT / "signals.csv"))
    ap.add_argument("--out", default=str(ROOT / "dashboard.html"))
    ap.add_argument("--regen-prices", action="store_true", help="re-create the simulated price file")
    args = ap.parse_args(argv)

    prices = load_prices(args.prices, regen=args.regen_prices)
    simulated = bool("source" in prices and (prices["source"] == "simulated").any())
    signals = build_signals(prices)
    signals.drop(columns="spark").to_csv(args.signals_out, index=False)
    build_dashboard(signals, load_ledger(args.ledger), args.out, simulated)

    counts = signals["signal"].value_counts()
    print(f"Signals: {len(signals)} assets | BUY {counts.get('BUY', 0)} | "
          f"CAUTION {counts.get('CAUTION', 0)} | NEUTRAL {counts.get('NEUTRAL', 0)}")
    print(signals.sort_values("rsi_14")[["ticker", "asset_class", "close", "rsi_14", "signal"]]
          .to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
    print(f"Wrote {args.signals_out} and {args.out}")


if __name__ == "__main__":
    main()
