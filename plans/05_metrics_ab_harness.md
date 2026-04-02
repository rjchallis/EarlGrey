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

---

## 5a — Resource scaling calibration (genome-size model)

**Goal:** Derive per-process memory scaling coefficients from real trace data so
`nextflow.config` can set sensible defaults without over-requesting, while retry
escalation covers the tail.

### Why

Repeat content and therefore peak memory for CLASSIFY_REPEATS and MERGE_REPEATS
correlates with genome size. Two data points (e.g. yeast 12 MB and a ~500 MB
invertebrate) are enough to fit a linear model `mem = base + k * genome_bytes`.

### Data collection

For each completed run collect from `trace.txt`:

- `peak_rss` (MB) for CLASSIFY_REPEATS, MERGE_REPEATS, CALCULATE_DIVERGENCE
- `realtime` for all processes
- genome size in bytes (available from `genome.size()` in Nextflow or `stat`)

Record in a simple table:

| genome    | size (MB) | CLASSIFY peak_rss (GB) | MERGE peak_rss (GB) | CLASSIFY realtime |
| --------- | --------- | ---------------------- | ------------------- | ----------------- |
| yeast R64 | 12        | 5.7                    | ?                   | 18m 55s           |
| _(next)_  |           |                        |                     |                   |

Target: at least 3 genomes spanning 10 MB → 1 GB to fit the model.
Candidate genomes to add to `baseline_config.yaml`: a small insect (~200 MB),
a plant or fish (~500 MB–1 GB).

### Action

1. After each successful Nextflow run, run `make nextflow-collect-metrics` and
   append the relevant rows to the table above.
2. Once ≥3 data points exist, fit `mem = base + k * genome_size` for
   CLASSIFY_REPEATS and MERGE_REPEATS.
3. Update `nextflow.config` resource blocks to use the fitted model:
   ```groovy
   // Example — tune base and k from real data
   withName: 'CLASSIFY_REPEATS' {
       memory = { check_max( (8.GB + (long)(genome.size() * 450)) * task.attempt, 'memory' ) }
   }
   ```
4. Keep retry escalation (`task.attempt` multiplier) as the safety net for
   outlier genomes.
