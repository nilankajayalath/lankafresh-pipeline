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
import pandas as pd
import numpy as np
from pathlib import Path

DATA = Path(__file__).resolve().parents[1].parent / "data"


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


def clean(df):
    """Standardise locations, parse dates, drop bad rows."""
    # BUG 2: location is not normalised (casing + whitespace differ across
    # files), so the same outlet is later counted as several outlets.
    df["location"] = df["location"]

    # BUG 3: dates come in three different formats; a single hard-coded format
    # silently turns most of them into NaT.
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")

    # BUG 4: negative data-entry errors in units_sold are left in, dragging
    # revenue down instead of being removed or corrected.
    df = df.dropna(subset=["date"])
    return df


def add_revenue(df):
    """Revenue should be (units_sold - returns) * unit_price."""
    # BUG 5: returns are ignored, so revenue is overstated.
    df["revenue_calc"] = df["units_sold"] * df["unit_price"]
    return df


def monthly_revenue_by_location(df):
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M")
    # BUG 6: groupby uses sum of the STALE 'revenue' column from the files
    # instead of the freshly computed 'revenue_calc'.
    out = df.groupby(["location", "month"])["revenue"].sum().reset_index()
    return out


def compare_to_targets(monthly):
    targets = pd.read_csv(DATA / "location_targets.tsv", sep="\t")
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
