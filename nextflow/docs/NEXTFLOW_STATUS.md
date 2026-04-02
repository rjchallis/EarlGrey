# Nextflow Implementation Status

Quick reference for what's done, what's to do, and how to run the Nextflow version with metrics collection.

---

## Status Summary

| Component                | Status        | Notes                                                                     |
| ------------------------ | ------------- | ------------------------------------------------------------------------- |
| **DSL2 Scaffold**        | ✅ Complete   | main.nf, nextflow.config, variants.config, README, TEMPLATE module        |
| **Process Modules**      | ❌ To do      | 9 processes need implementation                                           |
| **Metrics Collection**   | ✅ Configured | Automatic via Nextflow trace.txt, report.html, timeline.html, dag.svg     |
| **Baseline Python/Bash** | ✅ Working    | baseline_submit.py, collect_metrics.py (proven on HPC cluster)            |
| **Workflow Logic**       | ❌ To do      | Currently just a stub; needs process interconnection & channel management |
| **Testing Framework**    | ✅ Partial    | TEMPLATE/main.nf provides boilerplate; no integration tests yet           |

---

## What's Already Implemented

### 1. **Nextflow Configuration** (`nextflow.config`)

- ✅ All 6 execution profiles ready (dev, hpc, sanger, singularity, docker, conda, test)
- ✅ Resource presets for all 9 processes (CPU, memory, time limits per process)
- ✅ Error strategy & retry logic
- ✅ **Metrics collection ENABLED:**
  - `trace { file = "results/pipeline_info/execution_trace.txt" }` — Per-task timing, CPU, memory
  - `report { file = "results/pipeline_info/execution_report.html" }` — Interactive HTML summary
  - `timeline { file = "results/pipeline_info/execution_timeline.html" }` — Gantt chart of execution
  - `dag { file = "results/pipeline_info/pipeline_dag.svg" }` — Workflow graph visualization

### 2. **Main Workflow** (`main.nf`)

- ✅ Help system & parameter validation (requires --genome and --species)
- ✅ Variant loading logic (if --variant != 'default')
- ✅ Logging of configuration summary
- ❌ **Process orchestration:** Only a stub that prints a message and exits
  - Process imports are commented out (pending module implementations)
  - Workflow body is empty (no channel connections)

### 3. **AB Testing Framework** (`conf/variants.config`)

- ✅ 8 predefined variants: default, repeatmasker_v4_0, repeatmodeler_fast/thorough, high_sensitivity, no_denovo, minimal
- ✅ Each variant specifies rm*version, rmod_max_rounds, skip*\* flags
- ✅ Callable via `--variant <name>`
- ❌ Not yet testable (requires workflow implementation)

### 4. **Module Template** (`modules/TEMPLATE/main.nf`)

- ✅ DSL2 process boilerplate (inputs, outputs, script, labels, container specs)
- ✅ Best practices checklist (10 items)
- ✅ Testing instructions

### 5. **Documentation**

- ✅ `README.md` — Comprehensive guide (parameters, profiles, usage, module dev guide)
- ✅ `NFCore_Integration.md` — nf-core module survey, when to use vs. custom wrappers

---

## What Needs Implementation

### Phase 3b: Process Module Implementation (9 processes)

These are the blockers to running end-to-end:

1. **`PREPARE_GENOME`** ← **Start here** (easiest)
   - Decompress genome (if .gz)
   - Validate FASTA format
   - Index with samtools
   - Inputs: (meta, genome_path)
   - Outputs: (meta, genome_fasta), (meta, genome_fai)
   - Time: ~1 min | Resources: 2 CPUs, 4 GB
   - Template: `modules/TEMPLATE/main.nf`

2. **`REPEAT_MASK_INITIAL`**
   - Run RepeatMasker against Dfam (build-in library)
   - Inputs: (meta, genome), Dfam library per `params.repeat_type` (eukarya/bacteria/archaea)
   - Outputs: (meta, masked_genome), (meta, repeats_gff)
   - Time: 1–8 hrs | Resources: `params.threads` CPUs, 16 GB
   - Metrics: Use `/usr/bin/time -v` wrapper (same as baseline_submit.py)
   - Container: `docker://repeatmasker/repeatmasker:4.1.2` or Singularity equivalent

3. **`BUILD_DATABASE`**
   - Prepare RepeatModeler database from genome
   - Inputs: (meta, genome)
   - Outputs: (meta, db_path)
   - Time: 5–10 min | Resources: 2 CPUs, 8 GB
   - Container: `docker://dfam/tetools:latest`

4. **`DE_NOVO_ROUNDX`** (multi-round orchestration)
   - Run RepeatModeler iteratively (1–N rounds per `params.rmod_max_rounds`)
   - Needs workflow-level loop to chain rounds
   - Inputs: (meta, db_path, round_num)
   - Outputs: (meta, families_fasta)
   - Time: 10–500 hrs per round (depends on genome & rounds) | Resources: `params.threads` CPUs, 16 GB
   - Container: `docker://dfam/tetools:latest`
   - **Most complex**; see `AGENTS.md` "Testing reimplemented functions" for equivalence validation

5. **`CLASSIFY_REPEATS`**
   - Classify discovered families via BLAST/Dfam
   - Inputs: (meta, families_fasta), Dfam DB
   - Outputs: (meta, annotated_families)
   - Time: 1–5 hrs | Resources: 4 CPUs, 8 GB

6. **`MERGE_REPEATS`**
   - Merge Dfam (initial) + RepeatModeler (de novo) libraries
   - Inputs: (meta, dfam_repeats), (meta, modeler_repeats)
   - Outputs: (meta, merged_library)
   - Time: 10 min | Resources: 2 CPUs, 4 GB

7. **`REPEAT_MASK_FINAL`**
   - Run RepeatMasker against merged library (2nd pass)
   - Inputs: (meta, genome), (meta, merged_library)
   - Outputs: (meta, final_masked_genome), (meta, final_repeats_gff)
   - Time: 1–8 hrs | Resources: `params.threads` CPUs, 16 GB
   - Similar to `REPEAT_MASK_INITIAL` but uses custom library

8. **`CALCULATE_DIVERGENCE`**
   - Compute divergence metrics (Kimura, etc.)
   - Inputs: (meta, final_repeats_gff)
   - Outputs: (meta, divergence_table)
   - Time: 10 min | Resources: 2 CPUs, 4 GB

9. **`GENERATE_SUMMARY`**
   - Output final annotation summary (JSON, GFF, statistics)
   - Inputs: (meta, masked_genome), (meta, repeats_gff), (meta, divergence)
   - Outputs: all to `params.outdir/*`
   - Time: 5 min | Resources: 1 CPU, 2 GB

### Workflow Orchestration

Once processes are implemented:

1. Create channel inputs from `--genome` parameter
2. Chain processes in dependency order: PREPARE_GENOME → REPEAT_MASK_INITIAL → BUILD_DATABASE → DE_NOVO_ROUNDX (loop) → CLASSIFY_REPEATS → MERGE_REPEATS → REPEAT_MASK_FINAL → CALCULATE_DIVERGENCE → GENERATE_SUMMARY
3. Emit final outputs to `params.outdir`

Example skeleton (pseudocode):

```nextflow
workflow {
    // Read genome into channel
    genome_ch = Channel.fromPath(params.genome)
    meta = [id: '${genome_basename}']

    // Chain processes
    PREPARE_GENOME(genome_ch)
    REPEAT_MASK_INITIAL(PREPARE_GENOME.out.genome)
    BUILD_DATABASE(PREPARE_GENOME.out.genome)

    // Multi-round loop
    DE_NOVO_ROUNDX(BUILD_DATABASE.out.db, (1..params.rmod_max_rounds))

    // ... rest of chain
    GENERATE_SUMMARY(REPEAT_MASK_FINAL.out, CALCULATE_DIVERGENCE.out)
}
```

---

## How to Run & Collect Metrics (Once Processes Implemented)

### Quick Start

```bash
cd /Users/rchallis/projects/local/EarlGrey

# 1. Test workflow structure (help & param validation)
nextflow run nextflow/main.nf --help

# 2. Dry run to check DAG
nextflow run nextflow/main.nf --genome devtools/config/chr1/yeast_R64_chr1.fna --species "Saccharomyces cerevisiae" -profile dev -resume -latest

# 3. Actual run (after processes implemented)
nextflow run nextflow/main.nf \
    --genome devtools/config/chr1/yeast_R64_chr1.fna \
    --species "Saccharomyces cerevisiae" \
    --outdir results/nextflow_chr1_test \
    -profile dev,singularity \
    -resume
```

### Metrics Collection (Automatic)

After the run completes, metrics are automatically saved to:

```
results/nextflow_chr1_test/pipeline_info/
├── execution_trace.txt          ← CSV with per-task timing, CPU, memory, I/O
├── execution_report.html        ← Interactive HTML summary (best for overview)
├── execution_timeline.html      ← Gantt chart of task execution order
└── pipeline_dag.svg             ← Workflow DAG graph
```

**Key metrics in `execution_trace.txt`:**

- `name` — Process name
- `status` — Completed/failed/cached
- `submit` — Submission time
- `start` — Execution start
- `complete` — Execution end
- `duration` — Wall time (ms)
- `realtime` — Elapsed wall time (ms)
- `cpus` — CPUs assigned
- `peak_rss` — Peak RAM (bytes)
- `cpu_user` — User CPU time (s)
- `cpu_sys` — System CPU time (s)

### Comparing Baseline vs. Nextflow Metrics

Use `collect_metrics.py` to parse Nextflow trace.txt (it already supports CSV parsing):

```python
from devtools.collect_metrics import parse_trace_txt

# Parse Nextflow trace
trace_file = "results/nextflow_chr1_test/pipeline_info/execution_trace.txt"
metrics = parse_trace_txt(trace_file)

# Compare per-process timing
for process in metrics:
    print(f"{process['name']}: {process['duration']} ms, {process['peak_rss'] / 1024}MB")
```

Or manually generate a comparison CSV:

```bash
# Extract key columns from Nextflow trace
awk -F',' '{print $1, $9, $10, $11}' results/nextflow_chr1_test/pipeline_info/execution_trace.txt > metrics_nextflow.csv

# Compare to baseline (if using Python version)
diff metrics_baseline.csv metrics_nextflow.csv
```

---

## Implementation Order (Recommended)

1. **PREPARE_GENOME** (10 min) — Simplest; validates setup
2. **REPEAT_MASK_INITIAL** (30 min) — Core process; uses existing baseline_submit.py logic as reference
3. **BUILD_DATABASE** (20 min) — Simple wrapper
4. **DE_NOVO_ROUNDX** (1–2 hrs) — Most complex; multi-round orchestration
5. Remaining 5 processes (2–3 hrs total) — Mostly pipeline glue

**Total estimate:** 4–6 hrs to implement all 9 processes + integration testing.

Once done → test with `--profile dev` locally on chr1 (should complete in ~5 min) → collect metrics → validate vs. baseline → move to `--profile hpc` on full genome.

---

## Testing Checklist

- [ ] `nextflow run nextflow/main.nf --help` → Shows help message
- [ ] `nextflow run nextflow/main.nf --genome test.fa --species "Test" -profile dev` → Fails gracefully if modules not available (clear error message)
- [ ] Implement PREPARE_GENOME → Test in isolation with `nextflow run modules/prepare/test.nf`
- [ ] Implement REPEAT_MASK_INITIAL → Test in isolation with `--genome chr1.fa`
- [ ] Chain processes one by one in main.nf → Test workflow at each step
- [ ] Full workflow on chr1 with `--profile dev` → Verify DAG, metrics collection
- [ ] Full workflow on full genome with `--profile hpc,singularity` → Verify resource scaling

---

## Reference Materials

- **nf-core modules survey:** `docs/NFCore_Integration.md`
- **Module template & best practices:** `modules/TEMPLATE/main.nf`
- **Comprehensive Nextflow guide:** `docs/README.md`
- **Process resource presets:** `nextflow.config` (lines 59–107)
- **Variant profiles:** `conf/variants.config`
- **Baseline Python metrics:** `devtools/collect_metrics.py`

---

## Summary: From Here to Running Nextflow with Metrics

**Current state:**

- Scaffold complete ✅
- Metrics collection infrastructure ready ✅
- 9 processes need implementation ❌

**To run the Nextflow version:**

1. Implement 9 process modules (using TEMPLATE/main.nf)
2. Connect them in main.nf workflow (channel management)
3. Run: `nextflow run nextflow/main.nf --genome chr1.fa --species "..." -profile dev,singularity`
4. Metrics auto-collected to `results/pipeline_info/execution_{trace.txt,report.html,timeline.html,dag.svg}`
5. Parse trace.txt or view execution_report.html for per-process timings & resource usage

**Estimated effort:** 4–6 hrs implementation + testing → runnable end-to-end Nextflow pipeline with full metrics collection.

**Next action:** Start with PREPARE_GENOME (samtools indexing) to validate the setup, then work through the 9 processes in dependency order.
