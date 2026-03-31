# 09 — Rust: Divergence & summary stats

Goal

- Move heavy divergence calculation code paths to Rust if they are CPU/IO bound and benefit from parallelism.

Responsibilities

- Fast parsing of alignments or pairwise data.
- Compute divergence metrics and summary statistics used in `divergence_plot.R`.
- Provide a CLI and Python bindings to compute divergence for a set of sequences.

Design notes

- Reuse the `earlgrey-io` crate for parsing inputs.
- Use Rayon for parallelism.

Deliverables

- `crates/earlgrey-divergence/` with CLI and Python bindings.
- Benchmarks showing speedup vs `divergence_calc.py` on example dataset.

Acceptance criteria

- Correctness validated against current outputs on example data.
- Performance improvements for CPU-bound sections.
