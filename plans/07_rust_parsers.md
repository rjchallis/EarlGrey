# 07 — Rust: IO & parser crates (first crate)

Purpose

- Implement a small, well-tested Rust crate providing streaming FASTA and GFF parsing, interval operations, and Python bindings for the most-used helper functions.
- Make a minimal `earlgrey-io` crate that can be imported from Python via `pyo3`/`maturin` or `pyo3-pack`.

Scope & responsibilities

- Streaming FASTA reader with minimal allocations and `SeqRecord` struct with header, seq, and optional metadata.
- GFF parser capable of streaming GFF3 entries preserving attributes and exact ordering and providing fast line-based parsing.
- Interval set operations: merge, subtract, join.
- Expose a small Python-friendly API `read_fasta(path) -> iterator`, `read_gff(path) -> iterator`, `merge_intervals(iterable) -> list`.

Design notes

- Use `nom` or `bstr` for fast parsing where appropriate; avoid full in-memory representation.
- Provide tests using the example dataset from `scripts/repeatCraft/example/`.
- Document edge cases (missing attributes, non-standard GFF lines).
- Recommended starting point: use the `rust-py-template` (for example `../../genomehubs/rust-py-template`) as a packaging/bindings scaffold (pyo3/maturin), adapting where necessary.

Deliverables

- `crates/earlgrey-io/` with `Cargo.toml`, lib, README, and `bindings/` examples.
- `python-bindings/earlgrey_io` example project using `maturin` to build a wheel.
- Tests and benchmarks comparing current Python parsing speed to Rust implementation.

Acceptance criteria

- Rust crate builds on CI and exposes the basic API via Python.
- Benchmarks show memory usage improvement and moderate speedups on target files.

Next steps

- Scaffold `crates/earlgrey-io` with `cargo new --lib` and example `pyo3` bindings.
