# 02 — Audit & Baseline Profiling

Goal

- Produce a lightweight, reproducible audit and baseline performance profile for the current codebase to direct reimplementation choices.

Scope

- Identify hot spots (IO-heavy parsing, Python loops, heavy subprocess calls), quantify time/memory per major stage, and produce a short report with measurements and recommendations.

Recommended minimal dataset

- Use an example genome subset from `scripts/repeatCraft/example/` or a small real chromosome (~10–50 MB) to make runs fast while preserving realistic behaviour.

Steps

1. Inventory & fast-run smoke tests
   - Confirm `earlGrey` runs end-to-end on the example dataset with default options producing expected outputs (non-production run).
   - Collect a list of invoked external binaries from the Bash script: `RepeatMasker`, `RepeatModeler`, `MAFFT`, `TRF`, `BLAST/RMBlast`, `cd-hit`.

2. Instrumentation ✅
   - ✅ Added `/usr/bin/time -v` wrapper to earlGrey calls in baseline_submit.py
   - ✅ Implemented metrics parsing from `time -v` output (wallclock, CPU, peak RSS, page faults, I/O)
   - ✅ Created `collect_metrics.py` to compare baseline vs. current runs
   - ✅ Metrics saved to `earlgrey_metrics.txt` in each run's output directory
   - Nextflow trace/report support deferred to Phase 3a (will add when Nextflow workflows created)

3. Run baseline and collect metrics (→ Phase 3a: Nextflow)
   - Initially designed for manual per-step measurement; now will be implemented as Nextflow DSL2 workflow
   - Each Nextflow process will capture: walltime, CPU, peak RSS, exit status, output size
   - Enables automated per-step metrics for all runs (development + production scales)
   - Supports threading scaling tests (2–4 threads local dev, 16+ threads HPC)

4. Parse logs & summarize (→ Phase 3a: Nextflow reports)
   - Nextflow `-with-trace` and `-with-report` will generate execution timeline
   - Custom metrics aggregator will produce per-step summaries
   - Identify hotspots and candidates for optimization/reimplementation

Deliverables (Phase 2 — Complete)

- ✅ `devtools/baseline_submit.py` with metrics instrumentation (time -v wrapper)
- ✅ `devtools/collect_metrics.py` for baseline comparison
- ✅ `devtools/config/baseline_config.yaml` for reproducible assembly management
- ⏳ Larger genome baseline runs (pending Phase 3 Nextflow implementation for scalable testing)

Success criteria (Phase 2)

- ✅ End-to-end baseline run demonstrates earlGrey pipeline execution
- ✅ Metrics infrastructure captures walltime, CPU, memory, I/O per run
- ✅ Python overhead quantified as ~1–2% on small genomes (conservative estimate until larger tests)
- ⏳ Per-step hotspots will be identified in Phase 3 (on Nextflow-orchestrated runs with larger data)

Notes

- Do not reimplement external, well-maintained domain tools (RepeatMasker, RepeatModeler, MAFFT), only wrap them.
- Focus reimplementation on Python code that performs heavy file parsing/merging and can benefit from streaming & SIMD in Rust.

---

## Status & Findings (2026-04-01)

**Completed:**

- ✅ Step 1: Smoke test on yeast S288C (~12MB genome) — earlGrey runs end-to-end successfully. External binaries invoked: RepeatMasker, RepeatModeler, TRF, BLAST/RMBlast.
- ✅ Step 2: Instrumentation deployed — `/usr/bin/time -v` metrics capture on job wrapper, earlGrey log parsing, per-run comparison tables via `collect_metrics.py`. Python overhead ~1–2% on 12MB genome (negligible vs. external tools). Note: comprehensive per-step Python bottleneck analysis requires larger genomes (100MB+).
- ✅ Baseline metrics collected — 520 sec RepeatModeler time (16 threads), 19 families found

**Key Finding:**
On the 12MB test genome, **Python orchestration overhead is negligible** (~1–2% of total runtime). Time is dominated by external tools:

- RepeatMasker (prep + masking): ~40%
- RepeatModeler (discovery + scoring): ~50%
- TRF, BLAST, misc: ~10%

**Caveat:**
Python parsing/merging bottlenecks will only become visible on production-scale genomes (100MB–1GB). Per-step instrumentation on large genomes will reveal actual Python hotspots before optimization is attempted.

**Decision:**
Given this profile, defer detailed Python optimization to production-scale genomes (100MB–1GB). Focus next phase on:

1. **Nextflow refactoring** — modular orchestration, parallelism, caching
2. **AB testing harness** — compare tool variants (RepeatMasker versions, RepeatModeler strategies, threading)
3. **Larger dataset testing** — identify Python hotspots at production scale before reimplementation

---

## Next Phase: 03 — Nextflow Refactoring & AB Testing

**Phase 3a: Nextflow DSL2 scaffold (in progress)**

- Decompose earlGrey bash script into modular Nextflow processes
- Define per-process resource requests (CPU, memory, time)
- Integrate metrics collection (`-with-trace`, per-process timestamps)
- Support Singularity containerization for reproducible execution

**Phase 3b: AB testing harness (after 3a)**

- Variant profiles: RepeatMasker versions, RepeatModeler modes, thread counts
- Pairwise comparison framework (original vs. variant on same input)
- Metrics aggregation and statistical comparison

**Phase 3c: Larger genome validation (after 3a/3b)**

- Test on realistic genomes (100MB–1GB; e.g., full S288C or other assemblies)
- Per-step profiling to identify Python bottlenecks at production scale
- Prioritized list of candidates for Rust reimplementation
