# 03 — Nextflow DSL2 scaffold

## Purpose

Provide a full Nextflow DSL2 pipeline that faithfully mirrors the legacy `earlGrey` bash script, is testable on the Sanger HPC cluster, and becomes the platform for AB testing Rust reimplementations.

---

## Status (2026-04-02): functionally complete, validation in progress

### What is implemented

| Module                 | Process                | Legacy function mirrored                                          |
| ---------------------- | ---------------------- | ----------------------------------------------------------------- |
| `prepare_genome`       | `PREPARE_GENOME`       | `prepGenome()`                                                    |
| `repeat_mask_initial`  | `REPEAT_MASK_INITIAL`  | `getRepeatMaskerFasta()` + `firstMask()` / `firstMaskCustomLib()` |
| `build_database`       | `BUILD_DATABASE`       | `buildDB()`                                                       |
| `de_novo_repeat`       | `DE_NOVO_REPEAT`       | `deNovo1()` — 3-attempt fallback                                  |
| `classify_repeats`     | `CLASSIFY_REPEATS`     | `strainer()` — TEstrainer                                         |
| `cluster_library`      | `CLUSTER_LIBRARY`      | `clust()` — optional cd-hit-est step                              |
| `repeat_mask_final`    | `REPEAT_MASK_FINAL`    | `novoMask()`                                                      |
| `merge_repeats`        | `MERGE_REPEATS`        | `mergeRep()` — loose then strict fallback                         |
| `calculate_divergence` | `CALCULATE_DIVERGENCE` | `calcDivRL()`                                                     |
| `generate_summary`     | `GENERATE_SUMMARY`     | `charts()`                                                        |

`main.nf` wires all 10 processes with:

- Conditional `REPEAT_MASK_INITIAL` (when `--repeat_species` or `--custom_lib` supplied)
- Conditional `CLUSTER_LIBRARY` (when `--cluster_library` flag set)
- Conditional `CALCULATE_DIVERGENCE` (when `--skip_divergence` not set)
- `NO_FILE` sentinel pattern for optional `path` inputs
- `params.variant` / `conf/variants.config` AB testing hook

### Submission tooling

- `devtools/nextflow_submit.py` — rsyncs `nextflow/` + `scripts/` to cluster, builds bsub job script from `config/baseline_config.yaml`, submits
- `devtools/Makefile` targets: `nextflow-dry-run`, `nextflow-submit`, `nextflow-validate`, `nextflow-collect-metrics`, `nextflow-logs`

---

## Key implementation decisions

- **`shell:` not `script:`** — all process bodies use `shell:` so that `!{}` interpolation and `${}` shell variables coexist safely.
- **`\\n` / `\\t` in shell blocks** — Nextflow `shell:` triple-single-quoted strings do not process escape sequences; `\\n` is required to deliver `\n` to the shell/awk.
- **`SCRIPT_DIR` patching** — three legacy scripts hardcode `/data/toby/EarlGrey/scripts/`; each module patches this at runtime with `sed` before executing.
- **`params {}` in `nextflow.config` only** — Nextflow 25.x rejects `params {}` blocks inside `.nf` files; all parameter defaults live in `nextflow.config`.
- **`executor.perJobMemLimit = true`** (sanger profile) — required by the Sanger farm esub check that `-M` and `rusage[mem=]` must match.
- **`beforeScript` conda activation** (sanger profile) — temporary measure to put `BuildDatabase`, `RepeatMasker`, etc. in PATH on sub-jobs. Will be replaced by container images in step 10.

---

## Remaining steps

### 3a — Validate first end-to-end run

- `yeast_r64_nextflow_005` (full yeast_R64 genome) in progress 2026-04-02.
- On completion: `make nextflow-collect-metrics ID=yeast_R64 OUT_DIR=yeast_r64_nextflow_005`
- Compare per-process walltime and output files against `yeast_R64_baseline_iter_001`.
- Acceptance: all output files present; repeat count within ±5% of baseline.
- **Step 3 is not complete until this passes.**

---

### Gap analysis — legacy flags vs Nextflow pipeline

| Legacy flag | Description                             | Nextflow status                            |
| ----------- | --------------------------------------- | ------------------------------------------ |
| `-r`        | RepeatMasker species (initial mask)     | ✅ `--repeat_species`                      |
| `-l`        | Custom consensus library (initial mask) | ✅ `--custom_lib`                          |
| `-t`        | Threads                                 | ✅ `--threads`                             |
| `-i`        | BLAST iterations                        | ✅ `--blast_iterations`                    |
| `-f`        | Flanking bp                             | ✅ `--flank_bases`                         |
| `-n`        | Max consensus sequences                 | ✅ `--max_sequences`                       |
| `-a`        | Min consensus sequences                 | ✅ `--min_sequences`                       |
| `-c`        | Cluster library (cd-hit-est)            | ✅ `--cluster_library`                     |
| `-m`        | Remove short annotations <100bp         | ✅ `--remove_short`                        |
| `-d`        | Soft-mask genome at end                 | ⚠️ param exists, **no process** (3d below) |
| `-e`        | HELIANO Helitron detection              | ❌ **not implemented** (3g below)          |

**`sweepUp()`** (copy key files to summaryFiles/) — the legacy script does this as a
final collation step. Nextflow uses `publishDir` in each module instead; outputs
land in `results/` directly. Functionally equivalent — no separate process needed,
but the exact output directory structure should be verified against the legacy layout
during 3a validation.

---

### 3b — Stabilise component interfaces (feeds step 4)

- Document exact inputs/outputs for each module once a clean run exists.
- Ensure each process emits a `versions.yml` (nf-core convention) for reproducibility.

### 3d — Implement `--soft_mask` (missing feature)

- Legacy: after `sweepUp()`, runs:
  ```bash
  bedtools maskfasta -fi {original_genome} -bed {filteredRepeats.bed} \
      -fo {species}.softmasked.fasta -soft
  ```
  Uses the **original** (pre-prep) genome, not the ctg_N-swapped version.
- Nextflow plan:
  1. Add a `SOFT_MASK` process wrapping `bedtools maskfasta`.
  2. Inputs: original genome channel + `MERGE_REPEATS.out.bed` + `PREPARE_GENOME.out.dict`.
  3. Back-swap contig headers using `backSwap.py` so output has original names.
  4. Wire in `main.nf` conditional on `params.soft_mask == true`.
  5. `bedtools` is already present in the dfam/tetools image.

### 3e — Add `versions.yml` emission to all modules

- Each process should output `versions.yml` capturing tool versions (nf-core convention).
- Feed these into a `CUSTOM_DUMPSOFTWAREVERSIONS` collation step or equivalent.

### 3f — Resource scaling (feeds step 5a)

- CLASSIFY_REPEATS and MERGE_REPEATS are memory-sensitive; defaults are currently
  set conservatively with retry escalation as the safety net.
- Once trace data exists for ≥3 genome sizes, fit a linear scaling model and
  update `nextflow.config`. See `05_metrics_ab_harness.md § 5a` for the protocol.

### 3g — HELIANO optional step (missing feature)

- Legacy: `-e yes` runs `heliano` to detect Helitrons, producing a GFF passed
  as `-e $helitron_gff` to `rcMergeRepeatsLoose`/`rcMergeRepeats`.
- Low priority — specialised optional step, most genomes don't need it.
- Nextflow plan when ready:
  1. Add a `HELIANO` process: `heliano -g {genome} --nearest -dn 6000 ...`
  2. Convert RC.representative.bed → GFF (one-liner in legacy script).
  3. Pass resulting GFF as optional input to `MERGE_REPEATS` via `NO_FILE` sentinel.
  4. Add `--heliano` boolean param.

### 3c — Replace conda with containers (step 10 prerequisite)

- See `10_containerization.md` for the full plan.
- Short version: set `process.container = 'docker://dfam/tetools:latest'` in each module,
  remove `beforeScript`, set shared `singularity.cacheDir`.
- Verify cd-hit-est, R, Python, bedtools, heliano are all present or add a second image.

---

## Actual file layout (as built)

```
nextflow/
  main.nf                          # full DSL2 workflow
  nextflow.config                  # all params + resource presets + profiles
  assets/NO_FILE                   # sentinel for optional path inputs
  conf/
    dev.config
    variants.config                # AB testing variant definitions
  modules/
    prepare_genome/main.nf
    repeat_mask_initial/main.nf
    build_database/main.nf
    de_novo_repeat/main.nf
    classify_repeats/main.nf
    cluster_library/main.nf
    repeat_mask_final/main.nf
    merge_repeats/main.nf
    calculate_divergence/main.nf
    generate_summary/main.nf
devtools/
  nextflow_submit.py
  Makefile
  config/baseline_config.yaml      # ssh_host, paths, assemblies, bsub_defaults
```
