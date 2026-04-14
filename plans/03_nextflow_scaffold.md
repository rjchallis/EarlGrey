# 03 — Nextflow DSL2 scaffold

## Purpose

Provide a full Nextflow DSL2 pipeline that faithfully mirrors the legacy `earlGrey` bash script, is testable on the Sanger HPC cluster, and becomes the platform for AB testing Rust reimplementations.

---

## Status (2026-04-13): step 3 complete, baselines running

### What is implemented

| Module                 | Process                | Legacy function mirrored                                          |
| ---------------------- | ---------------------- | ----------------------------------------------------------------- |
| `prepare_genome`       | `PREPARE_GENOME`       | `prepGenome()` — _now emits original genome for soft_mask_        |
| `repeat_mask_initial`  | `REPEAT_MASK_INITIAL`  | `getRepeatMaskerFasta()` + `firstMask()` / `firstMaskCustomLib()` |
| `build_database`       | `BUILD_DATABASE`       | `buildDB()`                                                       |
| `de_novo_repeat`       | `DE_NOVO_REPEAT`       | `deNovo1()` — 3-attempt fallback                                  |
| `classify_repeats`     | `CLASSIFY_REPEATS`     | `strainer()` — TEstrainer                                         |
| `cluster_library`      | `CLUSTER_LIBRARY`      | `clust()` — optional cd-hit-est step                              |
| `repeat_mask_final`    | `REPEAT_MASK_FINAL`    | `novoMask()`                                                      |
| `heliano`              | `HELIANO`              | `heliano_optional()` — converts RC.representative.bed → GFF       |
| `merge_repeats`        | `MERGE_REPEATS`        | `mergeRep()` — accepts optional `-e` heliano GFF                  |
| `calculate_divergence` | `CALCULATE_DIVERGENCE` | `calcDivRL()`                                                     |
| `generate_summary`     | `GENERATE_SUMMARY`     | `charts()`                                                        |
| `soft_mask`            | `SOFT_MASK`            | Stage 8.5 — `bedtools maskfasta -soft` on original genome         |

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

---Completed in this session (2026-04-13)

### 3d — Soft-mask support ✅

- Added `SOFT_MASK` process wrapping `bedtools maskfasta -soft`.
- Modified `PREPARE_GENOME` to emit `original` output (original-named genome before ctg_N swapping).
- Wired into `main.nf` conditional on `params.soft_mask == true`.
- Baseline entries (`s_cerevisiae`, `a_thaliana`, `d_rerio`) have `soft_mask: true`.
- Output: soft-masked FASTA in `results/softmasked.fasta`.

### 3g — HELIANO support ✅

- Added `HELIANO` process: runs `heliano` and converts RC.representative.bed → GFF2.
- Produces empty GFF (not NO_FILE) if no Helitrons found, avoiding sentinel complexity.
- Modified `MERGE_REPEATS` to accept optional `heliano_gff` input and pass `-e` flag conditionally.
- Wired into `main.nf` with `--heliano` boolean param, mapped through NO_FILE sentinel when disabled.
- Updated `nextflow_submit.py` to read `heliano` and `soft_mask` flags from config and pass to Nextflow.

### 3a — Baseline runs launched

- **Yeast (s_cerevisiae_nextflow_001):** 12 MB test genome, soft_mask enabled.
- **Arabidopsis (a_thaliana_nextflow_001):** ~125 MB scaffold, soft_mask enabled.
- **Zebrafish (d_rerio_nextflow_001):** ~1.4 GB, soft_mask enabled.
- Fetch behavior: smart auto-detection (skip if file exists on remote, fetch if new).
- On completion of these runs, validate per-process walltime and output file counts. against `yeast_R64_baseline_iter_001`.
- Acceptance: all output files present; repeat count within ±5% of baseline.
- **Step 3 is not complete until this passes.**

---

### Gap analysis — legacy flags vs Nextflow pipeline

| Legacy flag | Description                             | Nextflow status                      |
| ----------- | --------------------------------------- | ------------------------------------ |
| `-r`        | RepeatMasker species (initial mask)     | ✅ `--repeat_species`                |
| `-l`        | Custom consensus library (initial mask) | ✅ `--custom_lib`                    |
| `-t`        | Threads                                 | ✅ `--threads`                       |
| `-i`        | BLAST iterations                        | ✅ `--blast_iterations`              |
| `-f`        | Flanking bp                             | ✅ `--flank_bases`                   |
| `-n`        | Max consensus sequences                 | ✅ `--max_sequences`                 |
| `-a`        | Min consensus sequences                 | ✅ `--min_sequences`                 |
| `-c`        | Cluster library (cd-hit-est)            | ✅ `--soft_mask` — SOFT_MASK process |
| `-e`        | HELIANO Helitron detection              | ✅ `--heliano` — HELIANO process     |

| Remaining steps

### 3e — Add `versions.yml` emission to all modules

- Each process should output `versions.yml` capturing tool versions (nf-core convention).
- Feed these into a `CUSTOM_DUMPSOFTWAREVERSIONS` collation step or equivalent.
- Lower priority; run baseline validation first to ensure reproducibility is acceptable.

### 3f — Resource scaling (feeds step 5a)

- CLASSIFY_REPEATS and MERGE_REPEATS are memory-sensitive; defaults are currently
  set conservatively with retry escalation as the safety net.
- Once trace data exists for all three genome sizes (s_cerevisiae, a_thaliana, d_rerio),
  fit a linear scaling model and update `nextflow.config`. See `05_metrics_ab_harness.md § 5a` for the protocol.
- Collect metrics using: `make nextflow-collect-metrics ID=<assembly> OUT_DIR=<run_dir>`ep 5a)

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
  modules/ with soft_mask and heliano wiring
  nextflow.config                  # all params + resource presets + profiles
  assets/NO_FILE                   # sentinel for optional path inputs
  conf/
    dev.config
    variants.config                # AB testing variant definitions
  modules/
    prepare_genome/main.nf          # now emits: genome, dict, original
    repeat_mask_initial/main.nf
    build_database/main.nf
    de_novo_repeat/main.nf
    classify_repeats/main.nf
    cluster_library/main.nf
    repeat_mask_final/main.nf
    heliano/main.nf                # ✅ NEW: Helitron detection
    merge_repeats/main.nf           # now accepts optional heliano_gff input
    calculate_divergence/main.nf
    generate_summary/main.nf
    soft_mask/main.nf              # ✅ NEW: bedtools maskfasta on original genome
devtools/
  nextflow_submit.py               # now fetches genome and passes soft_mask/heliano flags
  Makefile
  config/baseline_config.yaml      # ssh_host, paths, assemblies with URLs + soft_mask flags
  BASELINE_SETUP.md                # guide to smart fetch and baseline configuration
```
