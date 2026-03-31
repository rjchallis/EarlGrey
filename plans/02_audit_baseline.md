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

2. Instrumentation
   - Add `time` and `/usr/bin/time -v` wrappers around heavy calls (where possible) to capture wallclock, CPU, and peak-resident set size (RSS).
   - Add `-with-trace trace.txt -with-report report.html` to Nextflow runs (when available) — for now use wrapper scripts that write `metrics.json` per step.

3. Run baseline and collect metrics
   - For each major step (prepGenome, firstMask, buildDB, deNovo1, strainer, clust, novoMask, mergeRep, charts, calcDivRL, sweepUp), capture:
     - walltime, CPU time, peak RSS, exit status, and output size.
     - number of subprocess calls and average call latency for that step.
   - Run baseline with `-t` (threads) matching typical local dev (2–4) and one run with higher parallelism (e.g., 16) to see scaling behaviour.

4. Parse logs & summarize
   - Aggregate `metrics.json` or `/usr/bin/time` outputs into a CSV.
   - Produce a short `profiles/` report with top 10 hot spots by walltime and memory.

Deliverables

- `profiles/baseline_metrics.csv` (per-step metrics)
- `profiles/README.md` with instructions to reproduce the profiling runs and brief recommendations

Success criteria

- Hotspots identified with reproducible commands to reproduce their timings.
- A small prioritized list of candidates for Rust reimplementation (parsing, interval merging, divergence calculations).

Notes

- Do not reimplement external, well-maintained domain tools (RepeatMasker, RepeatModeler, MAFFT), only wrap them.
- Focus reimplementation on Python code that performs heavy file parsing/merging and can benefit from streaming & SIMD in Rust.
