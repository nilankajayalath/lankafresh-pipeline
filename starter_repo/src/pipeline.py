"""
LankaFresh sales analytics pipeline (STARTER - contains known bugs).

This module is supposed to:
  1. Load the three sales files (2021-2022 csv, 2023-2024 csv, 2025 xlsx).
  2. Clean and standardise them into one tidy table.
  3. Compute monthly revenue per location and compare against targets.

It currently runs but produces WRONG numbers, and some tests fail.
Your job: debug it systematically, fix it, and extend it (see TASK_BRIEF).
Do NOT rewrite from scratch unless you can justify why.
"""
import os
import pandas as pd
import numpy as np
from pathlib import Path

# Data folder. Override with the LANKAFRESH_DATA env var (useful for cron / CI).
DATA = Path(os.environ.get("LANKAFRESH_DATA", Path(__file__).resolve().parents[1].parent / "data"))

KNOWN_LOCATIONS = ["Colombo", "Kandy", "Galle", "Jaffna", "Kurunegala", "Matara"]
# Date formats seen in the three source files (tried in order, per row).
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"]
# A row is an outlier if units_sold > OUTLIER_FACTOR x the median units of its category.
OUTLIER_FACTOR = 10
KEY = ["date", "location", "category"]  # one row per day / outlet / category

# Filled by clean(): row-level data-quality events + summary counts (read by src/report.py).
LAST_QUALITY = {"events": None, "summary": {}}


def _find_header_row(path, sheet_name):
    """Return the 0-based row index of the real header (the row whose first cell is 'date').

    The 2025 workbook has a note row (+ a blank row) above the header, so a plain
    read_excel() would treat the note as the header and every column would be 'Unnamed'.
    """
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=15)
    for i, v in enumerate(raw.iloc[:, 0]):
        if str(v).strip().lower() == "date":
            return i
    raise ValueError(f"Could not find a 'date' header row in {path}")


def load_sales():
    """Load and concatenate all three sales files into one DataFrame.

    Columns are matched BY NAME (files have different column orders) and a
    `source_file` column is added so data-quality issues can be traced back.
    """
    a = pd.read_csv(DATA / "sales_2021_2022.csv")
    # FIX 1: 2023-2024 file is semicolon-separated (column order differs; concat aligns by name).
    b = pd.read_csv(DATA / "sales_2023_2024.csv", sep=";")
    # FIX 1b (untested bug): 2025 workbook has a note row above the header.
    xlsx = DATA / "sales_2025.xlsx"
    hdr = _find_header_row(xlsx, "daily_sales")
    c = pd.read_excel(xlsx, sheet_name="daily_sales", header=hdr)
    for frame, name in ((a, "sales_2021_2022.csv"), (b, "sales_2023_2024.csv"), (c, "sales_2025.xlsx")):
        frame.columns = [str(col).strip().lower() for col in frame.columns]
        frame["source_file"] = name
    return pd.concat([a, b, c], ignore_index=True)


def _parse_dates(series):
    """Parse a mixed-format date column; each row is tried against every known format."""
    s = series.astype("string").str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    for fmt in DATE_FORMATS:
        todo = out.isna()
        if not todo.any():
            break
        out[todo] = pd.to_datetime(s[todo], format=fmt, errors="coerce")
    return out


def _events(rows, issue, action, note=""):
    """Row-level data-quality events (what was found, what we did about it)."""
    cols = [c for c in ["source_file", "date", "location", "category", "units_sold",
                        "unit_price", "returns", "revenue"] if c in rows.columns]
    ev = rows[cols].copy()
    ev.insert(0, "note", note)
    ev.insert(0, "action", action)
    ev.insert(0, "issue", issue)
    return ev


def clean(df):
    """Standardise locations, parse dates, fix/drop bad rows.

    Every change is recorded in the module-level ``LAST_QUALITY["events"]`` (a DataFrame)
    so the data-quality report can say exactly what happened to which row.
    """
    df = df.copy()
    events = []
    raw_rows = len(df)

    # FIX 2: canonical location names (case + surrounding/inner whitespace).
    df["location"] = (df["location"].astype("string").str.strip()
                      .str.replace(r"\s+", " ", regex=True).str.title())
    bad_loc = ~df["location"].isin(KNOWN_LOCATIONS)
    if bad_loc.any():
        events.append(_events(df[bad_loc], "unknown_location", "dropped"))
        df = df[~bad_loc]

    # FIX 3: multi-format date parsing (was a single hard-coded format -> ~70% NaT).
    raw_dates = df["date"].copy()
    df["date"] = _parse_dates(df["date"])
    bad_date = df["date"].isna()
    if bad_date.any():
        ev = _events(df[bad_date].assign(date=raw_dates[bad_date]), "unparseable_date", "dropped")
        events.append(ev)
        df = df[~bad_date]

    for col in ["units_sold", "unit_price", "returns", "revenue"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["units_sold", "returns"])

    # FIX 4: negative units are sign data-entry errors. |units| reproduces the reported
    # revenue exactly in the source data, so we correct instead of dropping.
    neg = df["units_sold"] < 0
    if neg.any():
        events.append(_events(df[neg], "negative_units", "sign_corrected", "units_sold = abs(units_sold)"))
        df.loc[neg, "units_sold"] = df.loc[neg, "units_sold"].abs()

    # Duplicates: one row per (date, location, category). Done AFTER the sign fix because a
    # sign-flipped row can be a duplicate of a correct one.
    dup = df.duplicated(KEY, keep="first")
    if dup.any():
        events.append(_events(df[dup], "duplicate_row", "dropped", "same date/location/category already present"))
        df = df[~dup]

    # Outliers (units typed with extra zeros, e.g. 7200 instead of 144).
    cat_median = df.groupby("category")["units_sold"].transform("median")
    outlier = df["units_sold"] > OUTLIER_FACTOR * cat_median

    # Missing unit_price: recover from the reported revenue (revenue = (units-returns)*price).
    # For outlier rows units can't be trusted, so use the category/outlet median price instead.
    miss = df["unit_price"].isna()
    net = df["units_sold"] - df["returns"]
    from_rev = miss & ~outlier & (net > 0)
    df.loc[from_rev, "unit_price"] = (df["revenue"] / net).round(2)[from_rev]
    still = df["unit_price"].isna()
    if still.any():
        med = df.groupby(["category", "location"])["unit_price"].transform("median")
        df.loc[still, "unit_price"] = med[still]
    if miss.any():
        events.append(_events(df[miss], "missing_unit_price", "imputed",
                              "revenue/(units-returns); median price if units were an outlier"))

    if outlier.any():
        implied = (df["revenue"] / df["unit_price"] + df["returns"]).round()
        ok = outlier & implied.between(1, OUTLIER_FACTOR * cat_median)
        events.append(_events(df[ok], "outlier_units", "corrected",
                              "units = revenue/unit_price + returns"))
        df.loc[ok, "units_sold"] = implied[ok]
        unfixable = outlier & ~ok
        if unfixable.any():
            events.append(_events(df[unfixable], "outlier_units", "dropped", "could not be reconciled"))
            df = df[~unfixable]

    # stock_on_hand is not used for revenue; missing values are only reported.
    n_stock = int(df["stock_on_hand"].isna().sum()) if "stock_on_hand" in df else 0

    df = df.sort_values(KEY).reset_index(drop=True)
    ev_all = (pd.concat(events, ignore_index=True) if events else
              pd.DataFrame(columns=["issue", "action", "note"]))
    # Stored at module level (NOT in df.attrs: a DataFrame inside attrs breaks pandas
    # groupby/concat downstream).
    LAST_QUALITY.update(events=ev_all, summary={"rows_loaded": raw_rows,
                        "rows_after_cleaning": len(df), "missing_stock_on_hand": n_stock})
    return df


def add_revenue(df):
    """Revenue = (units_sold - returns) * unit_price."""
    df = df.copy()
    # FIX 5: returns were ignored.
    df["revenue_calc"] = (df["units_sold"] - df["returns"]) * df["unit_price"]
    return df


def monthly_revenue_by_location(df):
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M")
    # FIX 6: aggregate the freshly computed revenue (not the stale 'revenue' column from the
    # files). Output column is still called 'revenue' - downstream contract unchanged.
    out = (df.groupby(["location", "month"])["revenue_calc"].sum()
             .rename("revenue").reset_index())
    return out


def compare_to_targets(monthly):
    targets = pd.read_csv(DATA / "location_targets.tsv", sep="\t")
    targets["location"] = targets["location"].str.strip().str.title()
    merged = monthly.merge(targets, on="location", how="left")
    merged["pct_of_target"] = merged["revenue"] / merged["monthly_revenue_target_LKR"]
    return merged


def run():
    df = load_sales()
    df = clean(df)
    df = add_revenue(df)
    monthly = monthly_revenue_by_location(df)
    result = compare_to_targets(monthly)
    return result


if __name__ == "__main__":
    print(run().head(20))
