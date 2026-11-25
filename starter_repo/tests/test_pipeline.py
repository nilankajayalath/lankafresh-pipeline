"""
Minimal regression tests. Several FAIL against the starter code on purpose.
Make them pass by fixing the pipeline (not by weakening the tests).
Run with:  pytest -q
"""
import pandas as pd
from src import pipeline as p


def test_locations_are_canonical():
    """After cleaning there must be exactly 6 outlets, correctly cased."""
    df = p.clean(p.load_sales())
    locs = set(df["location"].unique())
    expected = {"Colombo", "Kandy", "Galle", "Jaffna", "Kurunegala", "Matara"}
    assert locs == expected, f"Got {sorted(locs)}"


def test_all_dates_parsed():
    """No row should be dropped purely because its date format differed."""
    raw = p.load_sales()
    cleaned = p.clean(raw)
    # we tolerate a tiny loss, but not the ~70% lost by a single-format parse
    assert len(cleaned) >= 0.97 * len(raw), (len(cleaned), len(raw))


def test_no_negative_units():
    df = p.clean(p.load_sales())
    assert (df["units_sold"] >= 0).all()


def test_revenue_accounts_for_returns():
    df = p.add_revenue(p.clean(p.load_sales()))
    # pick a row where returns actually occurred, so the bug is visible
    row = df[df["returns"] > 0].iloc[0]
    expected = (row["units_sold"] - row["returns"]) * row["unit_price"]
    assert abs(row["revenue_calc"] - expected) < 1e-6


def test_monthly_uses_calculated_revenue():
    """Monthly totals must come from the recomputed revenue, not stale column."""
    df = p.add_revenue(p.clean(p.load_sales()))
    monthly = p.monthly_revenue_by_location(df)
    assert "revenue" in monthly.columns
    # a known location should have positive, finite revenue
    assert monthly["revenue"].sum() > 0
