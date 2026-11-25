"""
AI-assisted anomaly explanations (stretch feature).

    python -m src.explain [--month YYYY-MM]            # rule-based, works offline
    ANTHROPIC_API_KEY=... python -m src.explain --llm  # LLM rewrites the facts as plain English

Design (the important part): the LLM is NEVER asked to find causes. Python first builds a
small set of verified FACTS for each anomaly (numbers from the pipeline + data-quality
events touching that outlet-month). The LLM may only rephrase those facts; it is told to use
no other numbers. With no API key / on any API error we fall back to the rule-based text, so
the monthly job never fails because of the AI step.

Limits: it explains WHAT the data shows, not WHY the business changed (promotions, stock-outs,
holidays are not in the data). Output must be reviewed by a human before it is sent to anyone.
"""
import argparse
import json
import os
from pathlib import Path

import pandas as pd

from src import pipeline as p
from src import report


def build_facts(anomaly, monthly, events):
    """Verified facts for one anomaly row (all numbers come from the pipeline)."""
    loc, month = anomaly["location"], pd.Period(anomaly["month"], "M")
    hist = monthly[monthly["location"] == loc]["revenue"]
    row = monthly[(monthly["location"] == loc) & (monthly["month"] == month)].iloc[0]
    facts = {"type": anomaly["type"], "location": loc, "month": str(month),
             "revenue_LKR": round(float(row["revenue"])),
             "target_LKR": round(float(row["monthly_revenue_target_LKR"])),
             "pct_of_target": round(float(row["pct_of_target"]), 3),
             "outlet_median_monthly_revenue_LKR": round(float(hist.median()))}
    if len(events) and "date" in events:
        ev = events[(events["location"] == loc) &
                    (pd.to_datetime(events["date"], errors="coerce").dt.to_period("M") == month)]
        facts["data_corrections_in_month"] = ev.groupby("issue").size().to_dict()
    return facts


def rule_text(f):
    t = f["type"]
    if t == "under_target":
        gap = f["target_LKR"] - f["revenue_LKR"]
        s = (f"{f['location']} reached {f['pct_of_target']:.1%} of its {f['month']} target "
             f"(shortfall LKR {gap:,}).")
    else:
        word = "above" if t == "revenue_spike" else "below"
        s = (f"{f['location']} revenue in {f['month']} (LKR {f['revenue_LKR']:,}) was unusually "
             f"{word} its typical month (median LKR {f['outlet_median_monthly_revenue_LKR']:,}).")
    fixes = f.get("data_corrections_in_month")
    if fixes:
        s += " Note: data corrections touched this outlet-month: " + ", ".join(f"{k}={v}" for k, v in fixes.items()) + "."
    return s


def llm_text(f):
    """Rephrase the facts with an LLM. Returns None on any problem (caller falls back)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=os.environ.get("LANKAFRESH_LLM_MODEL", "claude-sonnet-5-5"), max_tokens=200,
            messages=[{"role": "user", "content":
                       "Write 2 plain sentences for a sales manager explaining this flagged item. "
                       "Use ONLY the numbers in the JSON. Do not guess causes (promotions, weather, etc.). "
                       "If you are unsure, say the data does not show why.\n" + json.dumps(f)}])
        return msg.content[0].text.strip()
    except Exception:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--month")
    ap.add_argument("--out-dir", default="output")
    ap.add_argument("--llm", action="store_true", help="use an LLM to phrase the explanations")
    args = ap.parse_args(argv)

    monthly = p.run()
    events = p.LAST_QUALITY["events"]
    month = pd.Period(args.month, "M") if args.month else monthly["month"].max()
    anomalies = report.build_anomalies(monthly, month, 1.0, 3.0)
    anomalies["month"] = anomalies["month"].astype(str)

    rows = []
    for _, a in anomalies.iterrows():
        f = build_facts(a, monthly, events)
        text = llm_text(f) if args.llm else None
        source = "llm" if text else "rules"
        rows.append({**{k: v for k, v in f.items() if k != "data_corrections_in_month"},
                     "explanation": text or rule_text(f), "source": source})
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / "anomaly_explanations.csv", index=False)
    for t in df["explanation"]:
        print("-", t)
    print(f"Written to {out.resolve() / 'anomaly_explanations.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
