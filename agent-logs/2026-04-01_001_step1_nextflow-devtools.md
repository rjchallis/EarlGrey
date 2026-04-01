---
date: 2026-04-01
branch: refactor/performance-optimisation
author: AI-agent
summary: Implement Step 1 — Nextflow scaffold and devtools remote submit utilities
---

What I did

- Scaffolded a minimal Nextflow DSL2 pipeline and configuration for `earlGrey` orchestration.
- Implemented a developer helper to submit Nextflow runner jobs on the LSF cluster (`devtools/nextflow_submit.py`).
- Hardened and iterated the baseline submit helper (`devtools/baseline_submit.py`) to support remote fetch, optional `.gz` decompression, login-shell SSH, `remote.init` module initialisation, debug tracing, and clearer dry-run output.
- Added Makefile targets to wrap the Nextflow helper (`devtools/Makefile`) and documented usage in `devtools/README.md`.

Files added/modified

- Added: `devtools/nextflow_submit.py`
- Modified: `devtools/baseline_submit.py` (iterative fixes during prior work)
- Modified: `devtools/Makefile` (targets `nextflow-dry-run`, `nextflow-submit`)
- Modified: `devtools/README.md` (documented new targets and helper)
- Added: `nextflow/main.nf`, `nextflow/nextflow.config`, `nextflow/modules/README.md` (minimal DSL2 scaffold)

Verification and commands run

- Dry-run of Nextflow submit:
  - `python3 devtools/nextflow_submit.py --outdir nextflow_test_out --dry-run`
  - `make -C devtools nextflow-dry-run ID=nextflow_test_out`
    Both printed the job-script preview and bsub header lines as expected.
- Remote submit (debug):
  - `python3 devtools/nextflow_submit.py --outdir nextflow_test_out --debug-remote`
  - Observed bsub output: `Job <150797> is submitted to queue <normal>.`

Acceptance criteria

- Dry-run prints a clear, inspectable job script preview.
- Remote submit returns a `bsub` job id (submission executed on configured `ssh_host`).
- No modifications were made to the main project `README.md` — refactor progress docs live under `docs/refactor/` and `agent-logs/`.

Notes, decisions and rationale

- `nextflow_submit.py` is intentionally independent from `baseline_submit.py`: it runs Nextflow, not `earlGrey`, unless you implement `earlGrey` invocation inside the Nextflow pipeline.
- Remote environment variability (login shell, modules) is handled via a `remote.init` block in the config and by invoking a login shell via SSH.
- `--debug-remote` provides remote script tracing (`set -x`) and prints remote stdout/stderr to aid debugging.

Next steps

1. Add Nextflow pipeline processes in `nextflow/main.nf` to call `earlGrey` steps (or call the existing baseline job) so Nextflow runs produce baseline-equivalent outputs.
2. Design and add an equivalence-test harness (pytest + fixtures) to compare outputs from baseline `earlGrey` runs vs Nextflow-driven runs.
3. Begin reimplementing performance-critical components in Rust under `crates/` with pyo3 bindings and add equivalence tests per AGENTS.md requirements.
