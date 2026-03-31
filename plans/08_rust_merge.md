# 08 — Rust: Merge/defragmentation crate

Purpose

- Implement the defragmentation and merging logic in Rust as a dedicated crate with deterministic rules and a test-suite.

Scope

- Input: sorted GFF entries or interval records.
- Output: merged/defragmented GFF entries according to configurable heuristics (e.g., allowed gap, min overlap, label precedence).
- Include CLI utility `earlgrey-merge` and Python bindings for scripting.

Design notes

- Make merging rules explicit and data-driven (config file with precedence rules and thresholds).
- Prefer streaming architecture: read, operate via a small in-memory window, and emit merged records.

Deliverables

- `crates/earlgrey-merge/` with implementation and a `earlgrey-merge` binary.
- Python bindings example and test cases showing correctness vs current `rcMergeRepeats` outputs.

Acceptance criteria

- Outputs match or improve on current merged outputs on example data and run faster with similar memory usage.

Next steps

- Implement config-driven heuristics and a few canonical test cases from `scripts/repeatCraft/test/`.
