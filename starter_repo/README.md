# LankaFresh Sales Analytics — Starter Repo

A small, **deliberately buggy** data pipeline for a 6-outlet distribution company
(5 years of daily sales, 2021–2025). It is your starting point for the practical task.

## Business context
At present, the monthly "revenue vs target per outlet" report is **prepared by hand
each month** in a spreadsheet — a slow, error-prone manual process. Management wants
this **automated**, and the automation must **plug into this existing codebase without
breaking anything that already works**. Treat this repo as a live system other people
depend on: preserve the existing public interface (`run()`) and output structure, and
make sure every test that passes today still passes after your changes.

## What's here
```
starter_repo/
├── src/pipeline.py        # load → clean → revenue → monthly KPIs (has bugs)
├── tests/test_pipeline.py # regression tests — several FAIL on purpose
├── conftest.py            # makes `from src import pipeline` work
├── requirements.txt
└── README.md
data/                      # three messy source files + targets (one level up)
├── sales_2021_2022.csv    # comma-separated, ISO dates
├── sales_2023_2024.csv    # SEMICOLON-separated, DD/MM/YYYY, different column order
├── sales_2025.xlsx        # Excel, a note row above the header, DD-Mon-YYYY dates
└── location_targets.tsv   # monthly revenue target per outlet (tab-separated)
```

## Setup
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```bash
python -m src.pipeline      # prints monthly revenue vs target (currently WRONG)
pytest -q                   # several tests fail until you fix the pipeline
```

## The data is intentionally messy
Expect: three different date formats, inconsistent separators, a header note row,
mixed-case and whitespace-padded location names, duplicate rows, missing
`unit_price` / `stock_on_hand`, negative data-entry errors, and extreme outliers.
Part of the task is to find these yourself — this README does **not** list every issue.

See `../TASK_BRIEF_Software_AI.md` for exactly what to deliver.
