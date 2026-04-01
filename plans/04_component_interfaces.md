# 04 — Component interfaces & contracts

Goal

- Define stable, minimal interfaces for components that will be reimplemented in Rust or replaced. These interfaces are intended to be thin and well-documented so Nextflow can plug in alternate implementations for AB testing.

Interfaces (suggested)

1. `io` / streaming crate (Rust):
   - Functions: `stream_fasta(path) -> Stream<SeqRecord>`, `stream_gff(path) -> Stream<GffRecord>`, `write_fasta(stream, path)`, `write_gff(stream, path)`
   - Behaviour: streaming; minimal memory; preserve comments/attributes; provide fast interval queries.
   - **blobtk coverage:** `file_reader(path)` in `blobtk::io` satisfies the location/compression-agnostic opening for all of the above. FASTA streaming is satisfied by `needletail` (already a blobtk dep). GFF streaming must be implemented in `earlgrey-io` — no blobtk equivalent. Add blobtk as a path dep rather than reimplementing the reader layer.

2. `intervals` crate (Rust):
   - API: `merge_intervals(iterable)`, `subtract_intervals(a, b)`, `overlap_join(a, b)`
   - Behavior: deterministic ordering, stable output, option to choose inclusive/exclusive coordinates.

3. `merging` / defragmentation service (Rust):
   - Input: GFF entries + overlap rules
   - Output: merged GFF; decisions encoded in a stable config file

4. `divergence` module (Rust/Python):
   - Responsibilities: compute divergence estimates given alignments and return summary stats for plots.

5. `variant` descriptor (JSON)
   - `variants.json` describing alternate process implementations with fields: `id`, `process_name`, `command_template`, `container`, `expected_outputs`, `notes`.

Contract principles

- Processes produce `metrics.json` with unified schema: `{ "process": "name", "variant": "id", "walltime": secs, "cpu": secs, "max_rss_mb": n, "return_code": 0 }`.
- All IO functions must be deterministic and documented.
- Keep CLI wrappers thin: they should accept input paths and write outputs and `metrics.json`.

Deliverables

- `design/component_contracts.md` (this file)
- `variants.json` example template for AB testing

Next steps

- If you want, I can generate `variants.json` and a minimal `component_contracts.md` under `design/` now.
