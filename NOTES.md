# Hand-over note (LankaFresh pipeline)

**What I changed:** fixed the 6 seeded bugs + 4 untested ones (xlsx note-row header, 219 duplicate rows incl. sign-flipped
duplicates, 823 missing `unit_price` that silently under-summed revenue, 15 outliers where units were typed x50), added
`src/report.py` (one command -> monthly report, anomaly report, data-quality report), 6 extra tests, and CI. Public functions and
output columns are unchanged; the 4 originally-passing tests still pass (14/14 now).

**How each fix was validated:** the source files contain their own `revenue` column = (units - returns) x price, so I used it as an
independent oracle: after cleaning, recomputed revenue matches the reported one on 54,779 / 54,780 rows (the 1 mismatch is flagged in
the DQ report). Row count after cleaning = 6 outlets x 5 categories x 1,826 days exactly, which proves the dedupe is right.

**Inputs the automation takes:** `--month` (default latest), `--data-dir` / `$LANKAFRESH_DATA`, `--out-dir`, `--under-target`,
`--z-threshold`, `--outlier-factor`. In production: cron/Task Scheduler on the 1st of each month, files dropped in a shared folder
or pulled from the ERP/SFTP; targets owned by finance in `location_targets.tsv`.

**Assumptions / findings to raise:** dates in the 2023-24 file are DD/MM/YYYY (day > 12 appears); negative units are sign errors
(abs() reproduces reported revenue); every outlet is only ~14-30% of its monthly target in every month - the targets look
mis-scaled or in a different basis, confirm with management before using "under target" for decisions.

**With more time:** schema validation (pandera), alerts by email/Slack, per-category targets, unit tests on tiny fixtures, packaging.

**AI use:** AI drafted code; I checked it by (1) running the tests, (2) reconciling against the reported revenue column,
(3) checking exact row-count and uniqueness invariants. Proposed AI enhancement (not built): an LLM that explains each flagged
anomaly from the DQ log + MoM numbers; limitation = it can hallucinate causes, so it must only cite numbers passed in.
