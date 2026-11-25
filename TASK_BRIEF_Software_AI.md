# Practical Assessment — Software Developer, AI & Business Automation

**Candidate:** _______________________  **Date:** ___________  **Time allowed: 60 minutes**

You may use **any AI model or coding assistant** (Claude Code, Copilot, Cursor, ChatGPT, etc.), the internet, and any language/tooling you prefer (the starter is Python, but you may justify another stack). We are evaluating **how you work with an existing system under real constraints** — reading unfamiliar code, debugging methodically, automating a messy data task, and using Git/GitHub properly — **not** whether you can generate code from scratch.

**Narrate as you go.** A reviewer will watch part of your session. We care as much about your *process* (how you isolate a bug, how you validate AI output) as about the final numbers.

---

## The scenario
**LankaFresh** is a distribution company with **6 outlets** (Colombo, Kandy, Galle, Jaffna, Kurunegala, Matara). You are handed **5 years of daily sales data (2021–2025)** and an **existing analytics pipeline that produces wrong numbers and has failing tests**. Management wants reliable monthly performance-vs-target reporting and anomaly flagging — and they want it **automated**, not re-done by hand each month.

The data is deliberately messy and spread across three files in **three different formats** (comma CSV, semicolon CSV with a different column order, and an Excel file with a note row above the header). Expect inconsistent date formats, mixed-case/whitespace location names, duplicates, missing values, negative data-entry errors, and outliers. **Part of the task is to discover these yourself** — the README does not list them all.

Everything is in `starter_repo/` and `data/`. Read `starter_repo/README.md` first.

---

## What to do (core → stretch)

### 1. Set up & orient (first ~5 min)
- Get the repo running, run `pytest -q` (several tests fail), and **state out loud what the pipeline is supposed to do** after reading the code. We want to see you understand an existing system before changing it.

### 2. Debug systematically (core)
- Make the failing tests pass **by fixing the pipeline, not by weakening the tests.** There are several bugs; at least one real bug is **not** directly covered by a test — finding it earns credit.
- For each fix, briefly say: *what was wrong, how you found it, why your fix is correct.* Show your debugging steps (prints, breakpoints, isolating inputs) — don't just paste an AI patch.
- **Validate AI output:** if an assistant suggests a fix, explain how you confirmed it is correct and didn't break anything else (regression). This is explicitly scored.

### 3. Build the automation (core)
Turn the cleaned data into a repeatable report. At minimum:
- A robust **ingest + clean** step that handles all three file formats and the data-quality issues.
- **Monthly revenue per outlet vs target**, where revenue = `(units_sold − returns) × unit_price`.
- An **anomaly / data-quality report** (e.g. rows dropped and why, outliers flagged, outlets under target).
- Make it **re-runnable with one command** and output a file (CSV/Excel/simple dashboard). Think "runs every month unattended."

### 4. Gather the inputs it needs (approach)
- Decide what inputs/parameters the automation should take (e.g. target file path, month to report, thresholds) and how you'd obtain them in a real deployment. Note any assumptions.

### 5. Git/GitHub (required)
- Work in **Git from the start**. Commit in **logical steps with clear messages** (not one giant commit at the end).
- If you have internet and an account, **push to a GitHub repo** and share the link; use a branch and open a Pull Request describing your changes. If offline, show your local commit history (`git log`). Using GitHub Actions / a simple CI check is a bonus.

### 6. AI-assisted improvement (stretch)
- Propose and, if time allows, prototype **one** AI-powered enhancement (e.g. natural-language query over the sales data, automated anomaly explanations, a forecast). Keep it realistic and show you understand its limits.

---

## Deliverables
- The fixed, runnable repo (pushed to GitHub if possible).
- The generated monthly report + anomaly report (as files).
- A 3–4 line note of what you changed, what you'd do with more time, and where you used AI and how you checked it.

## How you'll be scored
See `../Evaluation_Rubrics.md` (Section 2). In short: **Process & debugging 25 · Creativity 15 · Approach & systems thinking 20 · Robustness & correctness 25 · Git/workflow & AI validation 15.**

> **The point:** anyone can ask AI to write code. We are hiring someone who can understand an existing system, change it safely, prove it still works, and automate reliably. Show us that.
