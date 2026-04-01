# 07 — Rust: IO & parser crates (first crate)

Purpose

- Implement a small, well-tested Rust crate providing streaming FASTA and GFF parsing, interval operations, and Python bindings for the most-used helper functions.
- Make a minimal `earlgrey-io` crate that can be imported from Python via `pyo3`/`maturin`.

## blobtk reuse analysis

Before writing any IO or FASTA code, check what `blobtk` (at `../../blobtoolkit/blobtk/rust`) already provides. Add it as a Cargo path dependency to avoid reimplementing shared utilities:

```toml
# crates/earlgrey-io/Cargo.toml
[dependencies]
blobtk = { path = "../../../../blobtoolkit/blobtk/rust" }
needletail = "0.5"
```

### Ready to use today — no new blobtk code required

| Function                                    | Location in blobtk         | What it gives EarlGrey                                                                                                                                 |
| ------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `io::file_reader(path)`                     | `src/io.rs:329`            | Location- and compression-agnostic `Box<dyn BufRead>`: handles local plain/`.gz`, `http(s)://`, `ssh://host:path`. Auto-decompresses `.gz` via flate2. |
| `io::get_writer(path)`                      | `src/io.rs:159`            | Writes to file (or stdout if path is `-`); auto-compresses if path ends in `.gz`.                                                                      |
| `io::get_file_writer(path, append)`         | `src/io.rs:128`            | Creates directories, returns buffered gz or plain writer.                                                                                              |
| `io::get_csv_reader()` / `get_csv_writer()` | `src/io.rs`                | Delimiter-aware CSV/TSV reader/writer wrapping the same writers above.                                                                                 |
| FASTA / FASTQ streaming                     | `src/fastq.rs::open_fastx` | Wraps `needletail::parse_fastx_file` — handles FASTA and FASTQ, plain or gzipped.                                                                      |
| `blobtk.filter.fastx` (Python)              | `src/python/filter.rs`     | Exposed via `pip install blobtk`. Filters FASTA/FASTQ by a sequence-ID list. Useful for TEstrainer FASTA subsetting steps.                             |

**Practical implication:** do not reimplement `file_reader` or `get_writer` in `earlgrey-io`. Call them directly from the blobtk crate, or at most re-export thin wrappers.

### Needs minor additions to blobtk (small effort)

The current `blobtk` Python bindings only expose `filter.fastx` (subsample), not a general FASTA iterator. For the divergence pipeline EarlGrey needs to stream all records. Two options:

1. **Preferred (keep concerns separate):** implement `read_fasta(path: &str) -> Vec<FastaRecord>` as a PyO3 function in `earlgrey-bindings`, using `needletail` directly. This is ~30 lines of Rust; no changes to blobtk needed.
2. **Alternative:** add a `blobtk.fasta.parse(path) -> list[dict]` binding in blobtk and re-export from `earlgrey-bindings`. Only worthwhile if BlobToolKit itself also needs that binding.

### Must write fresh in earlgrey-io

- **GFF3 parser:** blobtk has no GFF support. Implement a streaming line-based GFF3 parser that preserves attributes dictionary, handles `##` directives, and emits a `GffRecord` struct. Use a plain `BufReader` from `file_reader()` and split on `\t` — avoid `nom` overhead for a well-structured tabular format unless benchmarks show otherwise.
- **Interval operations:** `merge_intervals`, `subtract_intervals`, `overlap_join`. These are new. Consider the `bio` crate (`bio::data_structures::interval_tree`) for indexed queries; for simple merge-and-sort operations a manual sorted-sweep implementation is cleaner and avoids a heavy dep.

Scope & responsibilities

- Streaming FASTA reader using `needletail` (via direct dep or re-exported from blobtk).
- GFF3 parser: streaming, line-based, preserving attributes with a `GffRecord` struct.
- Interval set operations: merge, subtract, join.
- Expose a small Python-friendly API: `read_fasta(path) -> list[SeqRecord]`, `read_gff(path) -> list[GffRecord]`, `merge_intervals(iterable) -> list`.
- `file_reader` / `get_writer`: delegate to blobtk — do not reimplement.

Design notes

- For GFF parsing, a simple hand-written splitter is faster and less fragile than a `nom` combinator for this format. Validate the 9-column structure and return errors for malformed lines rather than panicking.
- Provide tests using the example dataset from `scripts/repeatCraft/example/`.
- Document edge cases: missing attributes, empty attribute fields, non-standard `#` comment lines (RepeatMasker outputs have irregular header comments).
- The `earlgrey-bindings` crate already uses `maturin` / `pyo3`; extend it for EarlGrey-specific bindings rather than creating a separate wheel.

Python bindings gap summary

| Needed                   | Already available via `pip install blobtk` | Needs new Rust code                            |
| ------------------------ | ------------------------------------------ | ---------------------------------------------- |
| Streaming FASTA          | No (only subsample by list)                | Yes — `read_fasta()` in earlgrey-bindings      |
| GFF reading              | No                                         | Yes — `read_gff()` in earlgrey-bindings        |
| Interval merge           | No                                         | Yes — `merge_intervals()` in earlgrey-bindings |
| FASTA subsetting by list | Yes — `blobtk.filter.fastx`                | No                                             |

Deliverables

- `crates/earlgrey-io/` updated with `Cargo.toml` (blobtk path dep), GFF3 parser, interval ops, lib, README.
- New PyO3 bindings in `crates/earlgrey-bindings/` for `read_fasta`, `read_gff`, `merge_intervals`.
- Tests against `scripts/repeatCraft/example/` and benchmarks comparing vs Python parsing.

Acceptance criteria

- `crates/earlgrey-io` builds with `blobtk` as path dep; `file_reader()` used for all file opens.
- `read_gff` correctly parses RepeatMasker GFF3 output including attribute dict.
- Benchmarks show ≥2× throughput and measurable memory reduction on target files.

Next steps

1. Add `blobtk` path dep to `crates/earlgrey-io/Cargo.toml`.
2. Implement GFF3 `stream_gff(reader: Box<dyn BufRead>) -> impl Iterator<Item=GffRecord>` in `src/core/gff.rs`.
3. Implement interval ops in `src/core/intervals.rs`.
4. Wire PyO3 bindings in `crates/earlgrey-bindings/src/lib.rs`.
