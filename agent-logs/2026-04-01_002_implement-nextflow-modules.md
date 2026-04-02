# Agent Log: Implement Nextflow Process Modules

**Date:** 2026-04-01
**Sequence:** 002
**Branch:** refactor/performance-optimisation

---

## Summary

Implemented all 10 Nextflow DSL2 process modules and wired the full end-to-end
workflow in `nextflow/main.nf`. The scaffold from session 001 had process
imports commented out and a stub workflow body; this session replaced both with
working implementations faithful to the legacy `earlGrey` bash script.

---

## Changes Made

### New module files (10 processes)

| File                                   | Process                | Mirrors legacy function                                           |
| -------------------------------------- | ---------------------- | ----------------------------------------------------------------- |
| `modules/prepare_genome/main.nf`       | `PREPARE_GENOME`       | `prepGenome()`                                                    |
| `modules/repeat_mask_initial/main.nf`  | `REPEAT_MASK_INITIAL`  | `getRepeatMaskerFasta()` + `firstMask()` / `firstMaskCustomLib()` |
| `modules/build_database/main.nf`       | `BUILD_DATABASE`       | `buildDB()`                                                       |
| `modules/de_novo_repeat/main.nf`       | `DE_NOVO_REPEAT`       | `deNovo1()`                                                       |
| `modules/classify_repeats/main.nf`     | `CLASSIFY_REPEATS`     | `strainer()`                                                      |
| `modules/cluster_library/main.nf`      | `CLUSTER_LIBRARY`      | `clust()`                                                         |
| `modules/repeat_mask_final/main.nf`    | `REPEAT_MASK_FINAL`    | `novoMask()`                                                      |
| `modules/merge_repeats/main.nf`        | `MERGE_REPEATS`        | `mergeRep()`                                                      |
| `modules/calculate_divergence/main.nf` | `CALCULATE_DIVERGENCE` | `calcDivRL()`                                                     |
| `modules/generate_summary/main.nf`     | `GENERATE_SUMMARY`     | `charts()`                                                        |

### Modified files

- **`nextflow/main.nf`** — Uncommented module imports, replaced stub workflow with
  full channel-wired DSL2 workflow, rewrote help/validation sections, added
  new `params` (repeat_species, custom_lib, TEstrainer tuning, cluster_library,
  remove_short, soft_mask, skip_divergence).
- **`nextflow/nextflow.config`** — Renamed `DE_NOVO_ROUNDX` → `DE_NOVO_REPEAT` in
  `withName` resource block; added `CLUSTER_LIBRARY` resource preset; added all
  new pipeline params with defaults and inline documentation; added `script_dir`
  param pointing to `${projectDir}/../scripts`.

### New asset

- **`nextflow/assets/NO_FILE`** — Empty sentinel file used as a placeholder for
  optional `path` process inputs (pattern from nf-core).

---

## Design Decisions

### Hardcoded `SCRIPT_DIR` in legacy scripts

Three scripts (`rcMergeRepeatsLoose`, `rcMergeRepeats`,
`TEstrainer_for_earlGrey.sh`) contain a hardcoded
`SCRIPT_DIR=/data/toby/EarlGrey/scripts/` (the original author's dev path).
Since modifying these scripts is out of scope, each affected module creates a
patched copy of the script in its work directory using `sed`:

```bash
sed "s|SCRIPT_DIR=.*|SCRIPT_DIR=${SCRIPT_DIR}|" \
    "${SCRIPT_DIR}/rcMergeRepeatsLoose" > ./rcMergeRepeatsLoose
chmod +x ./rcMergeRepeatsLoose
```

`params.script_dir` defaults to `${projectDir}/../scripts` and can be
overridden via `--script_dir` for non-standard installs. The same approach
applies to `STRAIN_SCRIPTS` in TEstrainer (`CLASSIFY_REPEATS` module).

### Optional initial masking

The `-r` (Dfam species) and `-l` (custom library) flags in the legacy script
are optional and mutually exclusive. In the Nextflow workflow, both are checked
at startup (`if (params.repeat_species && params.custom_lib) exit 1`) and the
optional `REPEAT_MASK_INITIAL` process is skipped entirely when neither is set.
The `NO_FILE` sentinel pattern allows `REPEAT_MASK_FINAL` to accept an optional
third `path` input without changing its process signature.

### RepeatModeler fallback retry logic

The legacy script retries RepeatModeler with progressively smaller
`genomeSampleSizeMax` values (81 M → 27 M) if the first attempt fails.
`DE_NOVO_REPEAT` replicates this using `|| true` to suppress exit codes after
each attempt, followed by an explicit check for the output file.

### MERGE_REPEATS strict-merge fallback

If `rcMergeRepeatsLoose` fails to produce output, the module falls back to the
stricter `rcMergeRepeats` and moves its output into `looseMerge/` so all
downstream outputs use a consistent path.

### GENERATE_SUMMARY: bypasses autoPie.sh

`autoPie.sh` also contains a hardcoded `SCRIPT_DIR` and is a thin wrapper
around `autoPie.R`. Rather than patching it again, `GENERATE_SUMMARY` inlines
the genome-size extraction and calls `autoPie.R` directly with positional
arguments, matching the original call convention.

---

## Workflow DAG

```
genome_ch
    │
PREPARE_GENOME ──────────────────────────────────────────────────┐ dict
    │ genome                                                      │
    ├─── (optional) REPEAT_MASK_INITIAL ──┐ initial.lib          │
    │         masked ──────────────┐      │                      │
    │ (or genome if no init mask)  │      │                      │
BUILD_DATABASE ◄──────────────────┘      │                      │
    │ db/                                 │                      │
DE_NOVO_REPEAT                           │                      │
    │ *-families.fa                       │                      │
CLASSIFY_REPEATS ◄── genome              │                      │
    │ *.strained                          │                      │
    ├── (optional) CLUSTER_LIBRARY        │                      │
    │ final lib                           │                      │
REPEAT_MASK_FINAL ◄─── initial.lib ◄─────┘                      │
    │ *.out  *.tbl  final.lib             │                      │
MERGE_REPEATS ◄──────── dict ◄───────────┴──────────────────────┘
    │ gff  bed  summary
CALCULATE_DIVERGENCE ◄── genome  ◄── final.lib   (optional)
    │ gff (with Kimura values)
GENERATE_SUMMARY ◄── summary  ◄── tbl
    │ summaryPie.pdf  highLevelCount.txt
```

---

## Acceptance Criteria / Equivalence Testing

**Not yet run** — the Nextflow pipeline has not been executed against a test
genome. Acceptance testing plan:

1. Run `nextflow run nextflow/main.nf --genome assets/yeast_R64_chr1.fna --species "Saccharomyces cerevisiae" -profile dev` on the cluster.
2. Compare key outputs to the existing baseline runs (`yeast_R64_baseline_iter_001/002`):
   - Number of TE families identified by RepeatModeler.
   - Total repeat content (%) from `*.highLevelCount.txt`.
   - GFF annotation file line count (within ±5% of baseline).
3. Compare per-step wall times from Nextflow `execution_trace.txt` to the
   `earlgrey_metrics.txt` from baseline runs.

Tolerances for floating-point/ordering differences will be documented in
`tests/validation/` once the first Nextflow run completes.

---

## Metrics Collection (Automatic)

Nextflow will automatically write after the run completes:

```
results/pipeline_info/
├── execution_trace.txt     ← per-task: duration, peak_rss, cpu_user, cpu_sys
├── execution_report.html   ← interactive summary (open in browser)
├── execution_timeline.html ← Gantt chart
└── pipeline_dag.svg        ← workflow graph
```

---

## Known Limitations / Follow-up

- **HELIANO** (Helitron detection, `-e yes` in legacy) is not implemented.
  Add as `DETECT_HELITRONS` module when needed.
- **Soft-masked genome output** (`--soft_mask`) is declared as a param but not
  yet wired into the workflow. Add a `SOFTMASK_GENOME` step after `MERGE_REPEATS`.
- **Container images** are commented out in all modules; uncomment and test with
  `dfam/tetools:latest` (RepeatModeler/Masker) before enabling `-profile singularity`.
- **earlGreyAnnotationOnly** (annotation-only mode, no de-novo) is not
  implemented; add a `--skip_denovo` fast path that feeds a user library
  directly to `REPEAT_MASK_FINAL`.
