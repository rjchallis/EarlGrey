# EarlGrey Reimplementation — Plans Overview

Purpose: record detailed sub-steps for each major task, list dependencies and logical order so work proceeds safely and testably.

Logical order (recommended) and dependencies:

1. HPC SSH/LSF execution setup
   - Dependencies: SSH access to cluster, Nextflow & Java on login node, Singularity (or equivalent) on compute nodes, and a shared storage area for images/data.
   - Rationale: required early so baseline profiling and iterative runs can exercise real HPC resources and scheduler behaviour.

2. Audit & baseline profiling
   - Dependencies: HPC setup (1) for realistic runs; local dev environment for small quick tests.
   - Rationale: provides baseline performance and identifies hotspots; influences prioritisation and variant selection.

3. Scaffold Nextflow pipeline
   - Dependencies: outcomes from (1) and (2) to prioritise processes and choose variants; container image policy defined.
   - Rationale: provides modular orchestration and experiment harness for AB testing; keep DSL2 layout for easy nf-core migration.

4. Define component interfaces
   - Dependencies: (2) skeleton; knowledge of inputs/outputs from (2) and (1).
   - Rationale: ensures swap-in/out of variants without breaking pipeline.

5. Implement metrics & AB harness
   - Dependencies: (2) and (3). Needed to run and compare variants.

6. Evaluate alternate external tools & reimplementation candidates
   - Dependencies: (1) baseline metrics; (3) interfaces to insert variants.
   - Rationale: decide wrap vs reimplement based on measured tradeoffs.

7. Rust reimplementations — parsers
   - Dependencies: stable component interfaces (4), benchmarks (2), and AB harness (5).
   - Rationale: implement high-throughput, low-memory GFF/FASTA parsers in Rust with stable Python bindings. Add unit tests and an automated equivalence test (see `tests/validation/`) before replacing the Python implementation.

8. Rust reimplementations — merging
   - Dependencies: stable component interfaces (4), parsers (7), benchmarks (2), and AB harness (5).
   - Rationale: implement repeat merging / defragmentation and interval operations in Rust to reduce memory and CPU overhead; include equivalence tests and microbenchmarks.

9. Rust reimplementations — divergence
   - Dependencies: stable component interfaces (4), parsers (7), merging (8), benchmarks (2), and AB harness (5).
   - Rationale: reimplement divergence calculations (`divergence_calc.py`) focusing on memory efficiency and parallelism; validate results with equivalence tests and end-to-end metrics.

10. Containerize modules & images

- Dependencies: packaging of wrapped tools and Rust artifacts (7-9); follow container image policy (completed).

11. Validation & AB experiments

- Dependencies: (4), (6), (7-9) to compare performance and accuracy across variants.

12. Documentation & CI tests

- Dependencies: stable pipeline and artifacts; add tests and nf-core alignment once interfaces stable.

Notes:

- Several steps are iterative — e.g., (5) may feed back into (2)/(3) as new variants are explored.
- Keep processes idempotent and file-based for reproducibility.

Next: per-step plan files with sub-steps and acceptance criteria.

File mappings (extracted from previous ITERATION_PLAN.md)

- Orchestration: `earlGrey` -> replace with Nextflow `main.nf` (pipeline entrypoint).
- RepeatCraft helpers: `scripts/repeatCraft/helper/repeatcraftHelper.py` and related helper scripts -> prime Rust targets (parsing/merging).
- TEstrainer scripts: `scripts/TEstrainer/scripts/TEtrim.py`, `scripts/TEstrainer/scripts/initial_mafft_setup.py` -> orchestration remains in Nextflow; heavy IO/compute parts are candidates for Rust reimplementation.
- Divergence: `scripts/divergenceCalc/divergence_calc.py` -> candidate for Rust reimplementation.
- Examples/tests: `scripts/repeatCraft/example/` -> small test corpus for CI and profiling.
- Container & build: `Docker/Dockerfile`, `Docker/getFiles.sh`, `conda/meta.yaml` -> containerisation and build references.
