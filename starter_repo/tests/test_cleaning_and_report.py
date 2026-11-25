"""Extra tests added with the fixes: cover the bugs the original suite did NOT catch."""
import pandas as pd
from src import pipeline as p
from src import report


def _clean():
    return p.add_revenue(p.clean(p.load_sales()))


def test_xlsx_header_row_detected():
    raw = p.load_sales()
    assert not any(c.startswith("unnamed") for c in raw.columns)
    assert set(raw["source_file"]) == {"sales_2021_2022.csv", "sales_2023_2024.csv", "sales_2025.xlsx"}


def test_one_row_per_day_outlet_category():
    df = _clean()
    assert not df.duplicated(["date", "location", "category"]).any()
    assert len(df) == 6 * 5 * 1826  # 6 outlets x 5 categories x 1826 days (2021-2025)


def test_no_missing_prices_or_nan_revenue():
    df = _clean()
    assert df["unit_price"].notna().all() and df["revenue_calc"].notna().all()


def test_outliers_reconciled():
    df = _clean()
    assert df["units_sold"].max() < 1000


def test_recomputed_revenue_matches_reported_revenue():
    """Independent check: the source files' own revenue column agrees with our formula."""
    df = _clean()
    ok = ((df["revenue_calc"] - df["revenue"]).abs() < 0.05).mean()
    assert ok > 0.9999, ok


def test_report_writes_files(tmp_path):
    assert report.main(["--month", "2025-06", "--out-dir", str(tmp_path)]) == 0
    for f in ["monthly_revenue_vs_target.csv", "anomaly_report.csv", "data_quality_report.csv",
              "data_quality_summary.csv", "lankafresh_report_2025-06.xlsx"]:
        assert (tmp_path / f).exists(), f
    monthly = pd.read_csv(tmp_path / "monthly_revenue_vs_target.csv")
    assert monthly["location"].nunique() == 6 and len(monthly) == 360


def test_explanations_are_grounded(tmp_path):
    from src import explain
    assert explain.main(["--out-dir", str(tmp_path)]) == 0
    df = pd.read_csv(tmp_path / "anomaly_explanations.csv")
    assert len(df) > 0 and df["explanation"].str.len().min() > 20
    assert set(df["source"]) == {"rules"}  # no API key in CI -> offline fallback
