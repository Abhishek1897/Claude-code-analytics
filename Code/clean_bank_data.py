"""Clean bank_statement.csv -> cleaned_data.csv.

Steps: standardize dates to YYYY-MM-DD, parse amounts to numbers (filling
missing ones with the column mean), normalize text fields, drop duplicates.
"""
import re
import sys
from datetime import datetime

import pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else "bank_statement.csv"
DST = sys.argv[2] if len(sys.argv) > 2 else "cleaned_data.csv"

DATE_FORMATS = [
    "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d",
    "%m/%d/%Y", "%d/%m/%Y", "%m/%d/%y", "%d/%m/%y",
    "%m-%d-%Y", "%d-%m-%Y", "%d.%m.%Y", "%m.%d.%Y",
    "%b %d %Y", "%b %d %y", "%B %d %Y", "%d %b %Y", "%d %B %Y",
    "%d-%b-%Y", "%d-%b-%y", "%b-%d-%Y",
]


def date_candidates(raw):
    """Return every distinct date the raw string could plausibly mean."""
    if pd.isna(raw) or not str(raw).strip():
        return []
    s = str(raw).strip()
    s = re.sub(r"[T ]\d{1,2}:\d{2}(:\d{2})?$", "", s)   # drop time part
    s = re.sub(r"^[A-Za-z]{3},\s*", "", s)              # drop weekday "Mon, "
    s = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", s)        # 20th -> 20
    s = s.replace(",", "")
    found = set()
    for fmt in DATE_FORMATS:
        try:
            d = datetime.strptime(s, fmt).date()
        except ValueError:
            continue
        if 2000 <= d.year <= 2100:
            found.add(d)
    return sorted(found)


def standardize_dates(series):
    """Parse dates; resolve DD/MM vs MM/DD ambiguity by picking the candidate
    closest to the previous transaction (the statement is chronological)."""
    out, prev = [], None
    for raw in series:
        cands = date_candidates(raw)
        if not cands:
            out.append(None)
            continue
        pick = cands[0] if prev is None else min(cands, key=lambda d: abs((d - prev).days))
        out.append(pick.isoformat())
        prev = pick
    return out


def parse_amount(raw):
    if pd.isna(raw) or not str(raw).strip():
        return None
    s = str(raw).strip().replace("$", "").replace(",", "").replace(" ", "")
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        value = float(s)
    except ValueError:
        return None
    return -abs(value) if negative else value


df = pd.read_csv(SRC, dtype=str)
rows_in = len(df)

for col in ["TransactionID", "Description", "Category", "Currency", "AccountNo"]:
    df[col] = df[col].str.strip().str.replace(r"\s+", " ", regex=True)
df["Currency"] = df["Currency"].str.upper()

df["Date"] = standardize_dates(df["Date"])

df["Amount"] = df["Amount"].map(parse_amount)
missing_amounts = int(df["Amount"].isna().sum())
mean_amount = df["Amount"].mean()
df["Amount"] = df["Amount"].fillna(mean_amount).round(2)

# Duplicates: same transaction after normalization (case-insensitive text).
key = df.assign(
    _desc=df["Description"].str.lower(),
    _cat=df["Category"].str.lower(),
)[["TransactionID", "Date", "_desc", "_cat", "Amount", "AccountNo"]]
dup_mask = key.duplicated(keep="first")
dropped = df.loc[dup_mask, "TransactionID"].tolist()
df = df.loc[~dup_mask].reset_index(drop=True)

df.to_csv(DST, index=False, float_format="%.2f")

print(f"Rows in: {rows_in}  ->  rows out: {len(df)}")
print(f"Duplicates removed ({len(dropped)}): {', '.join(dropped)}")
print(f"Missing amounts filled with mean ({mean_amount:.2f}): {missing_amounts}")
print(f"Rows with no usable date: {df.loc[df['Date'].isna(), 'TransactionID'].tolist()}")
