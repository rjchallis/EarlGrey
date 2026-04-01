# 09 — Rust: Divergence & summary stats

Goal

- Move heavy divergence calculation code paths to Rust where they are CPU/IO bound and benefit from parallelism.

## Current algorithm (`divergence_calc.py`) — stage by stage

Understanding which stages to port is critical before writing any Rust:

1. **GFF parse** (`pd.read_table`) — reads the RepeatMasker/EarlGrey GFF, filters by tool and class, extracts `repeat_family` from the attribute column. CPU-cheap but allocates a full in-memory DataFrame. **→ Replace with `earlgrey-io::stream_gff()` in Rust.** Saves significant memory for large GFFs.

2. **Library split** (`splitter()`) — reads the repeat library FASTA and writes one file per family into a temp directory. Currently uses `Bio.SeqIO`. **→ Replace with a streaming `needletail` loop** writing per-family files via `blobtk::io::get_writer`. No new algorithm, just faster IO.

3. **Sequence extraction per GFF row** — for each GFF record, calls `pybedtools.BedTool.sequence()` which shells out to `samtools faidx`. The multiprocessing `outer_func` runs this concurrently over chunked DataFrames. **This is the dominant walltime bottleneck.** Options:
   - Keep `samtools faidx` subprocess but parallelise more efficiently in Rust using Rayon — spawn one thread per GFF record, write extracted FASTA to temp files. Requires `rust-htslib` (already a blobtk dep) to call the CRAM/FASTA index directly without subprocess overhead.
   - Alternatively: pre-load the genome into an in-memory index (`.fai`-based) using a Rust FASTA index reader, avoiding subprocess entirely. This is the higher-reward path.

4. **Pairwise alignment** (`matcher` subprocess, EMBOSS) — run `matcher query subject -aformat fasta`. This stays as a subprocess call; Rust can only improve concurrency management (bounded worker pool with Rayon and a configurable timeout).

5. **Kimura80 calculation** — ~20 lines of pure math on the alignment strings. Currently pure Python per record. **→ Straightforward Rust port.** The formula is: $K = -\frac{1}{2}\ln\left[(1 - 2p - q)\sqrt{1-2q}\right]$ where $p$ = transition fraction, $q$ = transversion fraction. Add a unit test against the Python values from `divergence_calc.py`.

6. **Aggregation** — sum/mean per family. Trivial; keep in Python or Rust, no performance concern.

### Recommended Rust scope (highest ROI)

| Stage                 | Port to Rust?                 | Reason                               |
| --------------------- | ----------------------------- | ------------------------------------ |
| GFF parse             | Yes — via `earlgrey-io`       | Memory; already being built          |
| Library split (FASTA) | Yes — needletail loop         | IO; trivial to port                  |
| Sequence extraction   | Yes — rust-htslib FASTA index | Eliminates subprocess overhead       |
| Alignment (matcher)   | No — keep subprocess          | Complex domain tool                  |
| Kimura80              | Yes                           | CPU-bound per-record math; easy port |
| Aggregation           | Optional                      | Negligible cost                      |

**blobtk note:** `rust-htslib` is already a blobtk dep (`Cargo.toml`). EarlGrey can re-use it via the blobtk path dep or add it directly. No new blobtk code is needed.

Responsibilities

- Streaming GFF parse using `earlgrey-io`.
- FASTA library splitter using `needletail` + `blobtk::io::get_writer`.
- Parallel sequence extraction using rust-htslib FASTA index (coordinate-based fetch), with a Rayon thread pool sized to the `--cores` argument.
- Kimura80 distance function in `src/core/kimura.rs`.
- Aggregate divergence summary stats per family.
- Provide a CLI and Python bindings to run the full divergence pipeline or just the Kimura calc.

Design notes

- Reuse the `earlgrey-io` crate for GFF/FASTA parsing inputs.
- Use Rayon for parallelism; expose `--cores` / `--threads` analogous to the current `-t` flag.
- Keep the `matcher` subprocess call but manage it in Rust with a timeout (Tokio or `std::process::Child` with a deadline).
- Emit a `metrics.json` alongside outputs: walltime, CPU, max RSS, per-family record counts.

Deliverables

- `crates/earlgrey-divergence/` with `src/core/kimura.rs`, `src/core/extract.rs`, `src/main.rs` CLI, and Rayon worker logic.
- Python bindings in `earlgrey-bindings`: `compute_divergence(gff_path, genome_path, library_path, cores) -> list[dict]`.
- Benchmarks vs `divergence_calc.py` on example dataset, measuring walltime and peak RSS.

Acceptance criteria

- Kimura80 values match `divergence_calc.py` output to within floating-point precision (unit test with known input).
- End-to-end divergence output matches current output on example data within documented tolerance.
- Performance improvements demonstrated for the sequence extraction + Kimura stages on a realistic GFF (≥1000 records).
