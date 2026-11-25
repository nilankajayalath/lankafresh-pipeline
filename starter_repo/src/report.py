"""
One-command monthly report for LankaFresh.

    python -m src.report                      # latest month in the data
    python -m src.report --month 2025-11      # a specific month
    python -m src.report --data-dir /path --out-dir /path/out --under-target 0.9

Outputs (in --out-dir, default ./output):
    monthly_revenue_vs_target.csv   all months x outlets (same columns as pipeline.run())
    anomaly_report.csv              under-target outlets + revenue spikes/drops
    data_quality_report.csv         one row per data-quality action (what / which row / what we did)
    data_quality_summary.csv        counts per issue
    lankafresh_report_<YYYY-MM>.xlsx  all of the above + selected-month summary in one workbook
"""
import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd

from src import pipeline as p


def robust_z(s):
    med = s.median()
    mad = (s - med).abs().median()
    return (s - med) / (1.4826 * mad) if mad else pd.Series(0.0, index=s.index)


def build_anomalies(result, month, under_target, z_threshold):
    rows = []
    sel = result[result["month"] == month]
    for _, r in sel[sel["pct_of_target"] < under_target].iterrows():
        rows.append({"type": "under_target", "month": str(month), "location": r["location"],
                     "value": round(r["pct_of_target"], 4),
                     "detail": f"revenue {r['revenue']:,.0f} vs target {r['monthly_revenue_target_LKR']:,.0f}"})
    # unusual months for an outlet, judged against that outlet's own history (median/MAD)
    tmp = result.copy()
    tmp["z"] = tmp.groupby("location")["revenue"].transform(robust_z)
    for _, r in tmp[tmp["z"].abs() > z_threshold].iterrows():
        rows.append({"type": "revenue_spike" if r["z"] > 0 else "revenue_drop", "month": str(r["month"]),
                     "location": r["location"], "value": round(r["z"], 2),
                     "detail": f"revenue {r['revenue']:,.0f} (robust z={r['z']:.1f})"})
    return pd.DataFrame(rows, columns=["type", "month", "location", "value", "detail"])


def main(argv=None):
    ap = argparse.ArgumentParser(description="LankaFresh monthly revenue-vs-target report")
    ap.add_argument("--month", help="YYYY-MM to report on (default: latest month in the data)")
    ap.add_argument("--data-dir", help="folder with the sales files + location_targets.tsv "
                                       "(default: ../data or $LANKAFRESH_DATA)")
    ap.add_argument("--out-dir", default="output", help="where to write the reports (default ./output)")
    ap.add_argument("--under-target", type=float, default=1.0,
                    help="flag outlets whose revenue is below this fraction of target (default 1.0)")
    ap.add_argument("--z-threshold", type=float, default=3.0, help="robust z-score for spike/drop flags")
    ap.add_argument("--outlier-factor", type=float, default=p.OUTLIER_FACTOR,
                    help="units_sold > factor x category median = outlier")
    args = ap.parse_args(argv)

    if args.data_dir:
        p.DATA = Path(args.data_dir)
    p.OUTLIER_FACTOR = args.outlier_factor
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    result = p.run()
    events = p.LAST_QUALITY["events"]
    summary = p.LAST_QUALITY["summary"]

    month = pd.Period(args.month, "M") if args.month else result["month"].max()
    if month not in set(result["month"]):
        raise SystemExit(f"No data for month {month}. Available: {result['month'].min()} .. {result['month'].max()}")

    result = result.sort_values(["month", "location"]).reset_index(drop=True)
    result["status"] = np.where(result["pct_of_target"] >= 1, "on/above target", "below target")
    anomalies = build_anomalies(result, month, args.under_target, args.z_threshold)

    # reconciliation check: our recomputed revenue vs the revenue column in the source files
    clean_df = p.add_revenue(p.clean(p.load_sales()))
    mism = clean_df[(clean_df["revenue_calc"] - clean_df["revenue"]).abs() > 0.05]
    if len(mism):
        extra = mism[["source_file", "date", "location", "category", "units_sold", "unit_price", "returns", "revenue"]].copy()
        extra.insert(0, "note", "recomputed revenue differs from revenue reported in source file")
        extra.insert(0, "action", "flagged (recomputed value used)")
        extra.insert(0, "issue", "reported_revenue_mismatch")
        events = pd.concat([events, extra], ignore_index=True)

    ev_summary = (events.groupby(["issue", "action"]).size().rename("rows").reset_index()
                  if len(events) else pd.DataFrame(columns=["issue", "action", "rows"]))
    meta = pd.DataFrame([{"issue": "(rows loaded from 3 files)", "action": "", "rows": summary["rows_loaded"]},
                         {"issue": "(rows after cleaning)", "action": "", "rows": summary["rows_after_cleaning"]},
                         {"issue": "missing_stock_on_hand", "action": "reported only (unused for revenue)",
                          "rows": summary["missing_stock_on_hand"]}])
    ev_summary = pd.concat([meta, ev_summary], ignore_index=True)

    month_view = result[result["month"] == month].drop(columns=[]).copy()
    for df in (result, month_view, anomalies):
        if "month" in df:
            df["month"] = df["month"].astype(str)

    result.to_csv(out / "monthly_revenue_vs_target.csv", index=False)
    anomalies.to_csv(out / "anomaly_report.csv", index=False)
    events.to_csv(out / "data_quality_report.csv", index=False)
    ev_summary.to_csv(out / "data_quality_summary.csv", index=False)
    xlsx = out / f"lankafresh_report_{month}.xlsx"
    with pd.ExcelWriter(xlsx) as xw:
        month_view.to_excel(xw, f"Summary {month}", index=False)
        result.to_excel(xw, "All months", index=False)
        anomalies.to_excel(xw, "Anomalies", index=False)
        ev_summary.to_excel(xw, "DQ summary", index=False)
        events.to_excel(xw, "DQ row log", index=False)

    print(f"Report month: {month}")
    print(month_view[["location", "revenue", "monthly_revenue_target_LKR", "pct_of_target", "status"]]
          .to_string(index=False, formatters={"revenue": "{:,.0f}".format,
                                              "monthly_revenue_target_LKR": "{:,.0f}".format,
                                              "pct_of_target": "{:.1%}".format}))
    print(f"\nAnomalies flagged: {len(anomalies)} | DQ actions logged: {len(events)}")
    print(f"Written to: {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
