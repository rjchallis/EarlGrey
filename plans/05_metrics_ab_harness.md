# 05 — Metrics & AB-testing harness

Purpose

- Standardize metrics emitted by steps and provide a minimal harness to run alternate variants, collect metrics, and compare results quantitatively.

Metrics schema (per-process `metrics.json`)

- `process`: string
- `variant`: string
- `walltime_seconds`: number
- `cpu_seconds`: number
- `max_rss_mb`: number
- `exit_code`: int
- `stdout_lines`: int (optional)
- `stderr_lines`: int (optional)
- `notes`: freeform
- `disk_io_bytes`: number (optional)
- `stdout_checksum`: string (optional)
- `accuracy_metrics`: object (optional) — e.g., `{ "precision": 0.9, "recall": 0.85 }`

Reproducibility

- Processes that have stochastic behaviour should accept a `--seed` argument (or use Nextflow's `params.seed`) and record the seed value in `metrics.json` as `seed` (int).

Harness design

1. `variants.json` describes available variants (id, process, command template, container).
2. Nextflow `main.nf` accepts `params.variant` or `params.variants_list`.
3. Each process writes `metrics.json` near its outputs.
4. `metrics/collector.py` aggregates metrics across runs into `metrics/aggregate.csv` and produces a short HTML summary with plots for walltime and memory.

AB testing flow

- For each candidate variant:
  - Run pipeline with `nextflow run main.nf -params-file variants.json` where variants.json lists the variant to test.
  - Collect `metrics/aggregate.csv` and `reports/ab_summary.html` with comparisons.

Deliverables

- `plans/05_metrics_ab_harness.md` (this file)
- template `variants.json` (under `conf/` or `tests/`)
- `metrics/collector.py` (small script to merge JSON -> CSV + simple plots)

Next steps

- I can scaffold a minimal `metrics/collector.py` and example `variants.json` now unless you prefer to iterate on schema first.
