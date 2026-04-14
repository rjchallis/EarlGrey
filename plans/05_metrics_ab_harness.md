# 05 — Full-pipeline metrics & integration AB testing

## Purpose

- After a Rust reimplementation or variant has been validated at the single-step level
  (via plan 04), run it end-to-end on the full pipeline to ensure it integrates
  without breaking downstream processes.
- Standardize metrics emitted by the full pipeline and provide a harness to compare
  canonical vs. alternate implementations across the entire workflow.
- Calibrate resource requests based on genome-size scaling from real trace data.

## When this applies

This plan is a **secondary** validation layer. The primary iteration loop is plan 04:

1. **Plan 04 (single-step):** Validate a new MERGE_REPEATS implementation against
   yeast fixture in isolation using `make step-run MODULE=MERGE_REPEATS --variant rust_merge`.
   Diffs with `compare_step_outputs.py` capture row counts, structural metrics.
2. **Plan 05 (full-pipeline):** Once step 1 passes, run the full pipeline with
   `--variant rust_merge` to check that downstream processes (CALCULATE_DIVERGENCE,
   GENERATE_SUMMARY) still work correctly with the alternate output format.
3. Return to step 1 to iterate. Only commit the Rust impl after both layers pass.

---

## Metrics schema (per-process `metrics.json`)

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

### Reproducibility

- Processes that have stochastic behaviour should accept a `--seed` argument (or use Nextflow's `params.seed`) and record the seed value in `metrics.json` as `seed` (int).

## Full-pipeline AB testing harness

1. **`conf/variants.config`** defines variant profiles with conditional logic:

   ```groovy
   profiles {
     rust_merge_v1 {
       // Swap MERGE_REPEATS for Rust variant
       process.container = 'localhost/earlgrey-rust:latest'
       params.merge_repeats_variant = 'rust_v1'
     }
   }
   ```

2. **`nextflow/main.nf`** checks `params.<process>_variant` and swaps modules:

   ```groovy
   if (params.merge_repeats_variant == 'rust_v1') {
     include { MERGE_REPEATS_RUST } from './modules/merge_repeats_rust/main.nf'
     merge_repeats_module = MERGE_REPEATS_RUST
   } else {
     include { MERGE_REPEATS } from './modules/merge_repeats/main.nf'
     merge_repeats_module = MERGE_REPEATS
   }
   ```

3. **Full-pipeline run with variant:**

   ```bash
   nextflow run main.nf \
       -profile hpc,rust_merge_v1 \
       --genome ... --species ... \
       --outdir results_rust_merge_v1/
   ```

4. **`metrics/collector.py`** aggregates `trace.txt` and per-process `metrics.json`
   from canonical and variant runs, producing `metrics/aggregate.csv` and HTML plots.

### Integration validation workflow

1. Variant has passed **single-step validation** (plan 04).
2. Submit canonical baseline:
   ```bash
   make nextflow-submit ID=yeast_R64 OUT_DIR=yeast_R64_canonical
   ```
3. Submit variant:
   ```bash
   make nextflow-submit ID=yeast_R64 OUT_DIR=yeast_R64_rust_merge_v1 \
       NF_PROFILES=hpc,rust_merge_v1
   ```
4. On completion, collect metrics:
   ```bash
   make nextflow-collect-metrics ID=yeast_R64 OUT_DIR=yeast_R64_canonical
   make nextflow-collect-metrics ID=yeast_R64 OUT_DIR=yeast_R64_rust_merge_v1
   ```
5. Compare with `devtools/compare_full_runs.py canonical/ rust_merge_v1/`:
   - Check walltime per process
   - Check peak memory per process
   - Structural metrics (row counts, output file sizes)
   - If acceptable: merge the Rust module into `modules/` and add as default.
   - If regression: iterate in plan 04 and try again

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

---

## Two-layer validation workflow (Plans 04 + 05 together)

**This plan (05)** is used **after** a variant module has been validated in isolation
via **plan 04** (Component interfaces & single-step iteration).

### Entry route

1. 👤 **Decide to reimplement** a module (e.g. MERGE_REPEATS) in Rust.
2. 🧪 **Plan 04 (single-step iteration):**
   - Capture fixture data from a canonical baseline run
   - Create a test entry point (`-entry test_MERGE_REPEATS`) in `nextflow/test/steps.nf`
   - Build Rust module and test against fixture in isolation
   - Use `compare_step_outputs.py` to verify row counts and metrics match
   - Iterate rapidly without rerunning the full pipeline
3. ✅ **Once single-step tests pass:**
   - Proceed to this plan (05)
   - Swap the module into main.nf via `variants.config`
   - Run full pipeline on canonical + variant
   - Use `compare_full_runs.py` to verify integration (walltime, memory, output structure)
   - If acceptable: merge into main and set as default
   - If not: iterate in plan 04 and repeat step 3

### Why two layers?

- **Plan 04** isolates the component, enabling 10-minute test cycles
- **Plan 05** verifies integration, detecting downstream effects only visible at pipeline scale
- Together: **Fast iteration + confidence in integration**

The fixture approach (plan 04) eliminates the `-resume` cascading problem entirely:
input data is stable, so changes to the module are always tested against the same
canonical inputs. No risk of invalidated chain reactions.

---

## Status (2026-04-13)

- ✅ Two-layer validation architecture documented
- ✅ Fixture capture approach detailed in plan 04
- ✅ Full-pipeline AB testing harness design laid out (this plan)
- ✅ Resource scaling calibration outlined
- ⏳ Implementation: waiting for baseline runs to complete so fixtures can be captured
