# 08 — Rust: Merge/defragmentation crate

Purpose

- Implement the defragmentation and merging logic in Rust as a dedicated crate with deterministic rules and a test-suite.

## blobtk / dependency notes

blobtk has no interval merging code. This crate is entirely new work. For the interval data structure:

- **For merge-and-sort operations** (the typical GFF defragmentation pattern): a plain sorted-sweep implementation in `src/core/intervals.rs` is simpler and avoids extra dependencies. Sort by `(seqid, start)`, then a single pass to merge overlapping records.
- **For indexed queries** (e.g., "find all records overlapping a given region"): consider the `bio` crate (`bio::data_structures::interval_tree`). Only add this if the merge step needs random-access lookups; do not add it speculatively.
- **File IO:** delegate completely to `blobtk::io::file_reader` and `get_writer` via the `earlgrey-io` path dep.

## Legacy algorithm summary (`rcMergeRepeats` / RepeatCraft helpers)

Before implementing, audit the actual merge rules in `scripts/rcMergeRepeats` and `scripts/repeatCraft/helper/repeatcraftHelper.py`:

- `fuseltr()` — groups adjacent LTR entries within a configurable flank distance into an LTR group, tagging records with a `LTRgroup` attribute.
- `filtershortTE()` — marks or filters entries below a per-class minimum length threshold.
- `reformat()` — rewrites the attribute field to a normalised format, adding `Tstart`/`Tend` from the `.out` file.

Capture these as explicit, data-driven rules in a config struct rather than hard-coded thresholds. See `Design notes` below.

Scope

- Input: sorted GFF entries or interval records (parsed via `earlgrey-io::stream_gff`).
- Output: merged/defragmented GFF entries according to configurable heuristics (e.g., allowed gap, min overlap, label precedence).
- Include CLI utility `earlgrey-merge` and Python bindings for scripting.

Design notes

- Make merging rules explicit and data-driven: a `MergeConfig` struct (serialisable to/from TOML or JSON) holding per-class thresholds for gap tolerance and minimum length. This replaces the hard-coded defaults in `rcMergeRepeats`.
- Prefer a streaming architecture: read records into a small in-memory window keyed by `(seqid, strand)`, apply merge rules, emit merged records. Window size is bounded by the longest allowable merge gap — keeps memory proportional to gap size, not file size.
- An equivalence test against `rcMergeRepeats` binary output is mandatory before replacing the legacy step.

Deliverables

- `crates/earlgrey-merge/src/core/intervals.rs` — sorted-sweep merge logic.
- `crates/earlgrey-merge/src/core/config.rs` — `MergeConfig` struct and defaults matching current `rcMergeRepeats` behaviour.
- `crates/earlgrey-merge/src/main.rs` — `earlgrey-merge` binary.
- Python bindings in `earlgrey-bindings`: `merge_gff(path, config) -> list[GffRecord]`.
- Equivalence test in `tests/validation/` comparing output to `rcMergeRepeats` on example data.

Acceptance criteria

- Outputs match current merged outputs on example data (document any intentional differences).
- Runs faster with similar or lower memory on the example corpus.
- `MergeConfig` default values reproduce legacy behaviour exactly; deviations are documented.

Next steps

1. Audit `scripts/rcMergeRepeats` and `scripts/repeatCraft/helper/repeatcraftHelper.py` to extract all merge threshold values into a candidate `MergeConfig` default.
2. Implement sorted-sweep merge in `src/core/intervals.rs` with unit tests.
3. Wire Python bindings and run equivalence test against legacy binary.
