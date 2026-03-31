# 06 — Alternate external tools: evaluation and reimplementation candidates

Goal

- Identify external tools worth swapping or reimplementing; provide criteria and a small experiment plan to compare alternatives.

High-level guidance

- Keep canonical domain tools containerised and treated as black boxes when they are complex and well-maintained (e.g., RepeatMasker, RepeatModeler, MAFFT).
- Prefer swapping variants where alternative tools exist with similar input/output semantics (e.g., RMBlast vs BLAST+, mmseqs2 for clustering) and measure both runtime and quality impacts.
- Reimplement only where the current code is doing heavy IO or format-specific merging/parsing that is easy to replace with a fast Rust library.

Candidate swaps & notes

- Clustering & sequence-level deduplication:
  - Current: `cd-hit` (or similar) → Alternatives: `mmseqs2` (faster, better scaling) and `vsearch` (open-source).
  - Evaluation: speed, memory, cluster quality (percent identity), ease of integrating into wrappers.

- Local similarity search:
  - Current: RMBlast/BLAST wrappers → Alternatives: `mmseqs2` or `DIAMOND` (if protein steps exist).
  - Evaluation: sensitivity vs runtime; for DNA, mmseqs2 nucleotide mode; check false-negative rates on known benchmarks.

- Tandem repeat finder:
  - Current: `TRF` → Alternatives: `mreps` or specialized k-mer-based detectors.
  - Evaluation: output comparability and downstream effect on TE calling.

- Sequence alignment (MAFFT):
  - Keep MAFFT for alignment-based consensus; alternative is `muscle` or `kalign` only if MAFFT becomes a bottleneck.

- Repeat modeler / identification front-ends:
  - Typically heavy domain tools; keep containerised and wrap.

Evaluation plan

1. Pick 1–2 candidate substitutions (prefer mmseqs2 for clustering/search and vsearch for dnadup).
2. Prepare `variants.json` entries describing commands and containers for each variant.
3. Run AB tests on the example dataset with `-profile dev` collecting `metrics.json`.
4. Evaluate both runtime and quality: for quality, run an alignment-based comparison or simple recall/precision against expected TE labels if available.

Acceptance criteria for swapping

- Runtime: at least 2x speedup on the candidate step or notable parallel scaling improvements.
- Memory: equal or lower memory footprint.
- Quality: no more than a small, documented drop in recall/precision (user-defined threshold, e.g., <2% absolute loss), or provide a clear rationale.
- Integration: container available or easy to build; command-line outputs map to existing wrappers with minimal changes.

Reimplementation candidates (Rust)

- GFF/FASTA streaming and parsing utilities (strong candidate)
- Interval merging/defragmentation (strong candidate — deterministic semantics)
- Divergence calculation utilities (good candidate if Python code is IO-bound)

Deliverables

- `plans/06_alternate_tools.md` (this file)
- example `variants.json` entries for 2 candidate swaps
- small `tests/` script showing how to run the AB test for a single step

Notes

- Keep domain-specific heavy tools containerised and pinned by version.
- Use AB testing results to decide whether to reimplement or keep a wrapped containerised tool.
