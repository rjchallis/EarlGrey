# 2026-03-31_001 — Scaffold & Planning Summary

Author: GitHub Copilot (agent)
Date: 2026-03-31

Summary

- Completed a planning and scaffolding session to prepare EarlGrey for a
  staged reimplementation (Rust + Python bindings + Nextflow orchestration).
- Created the monorepo scaffold, copied/adapted configuration from the
  `genomehubs/rust-py-template`, and added developer tooling, CI stubs, and
  equivalence-testing scaffolding for transparent, test-driven reimplementation.

High-level actions performed

- Inventory & planning: converted the single `ITERATION_PLAN.md` into a set of
  focused `plans/00-12_*.md` files and updated `plans/00_overview.md`.
- Orchestration scaffold: added a minimal Nextflow DSL2 skeleton under
  `nextflow/` with `modules/`, `conf/dev.config`, `conf/hpc.config` and thin
  wrappers in `scripts/nextflow-wrappers/` that emit `metrics.json`.
- Rust workspace: created a top-level `Cargo.toml` workspace and initial crates:
  - `crates/earlgrey-io` (IO & interval ops)
  - `crates/earlgrey-merge` (merge/defragmentation)
  - `crates/earlgrey-divergence` (divergence computations)
  - `crates/earlgrey-bindings` (pyo3 bindings + maturin support)
- Template integration: pulled key config and developer files from
  `genomehubs/rust-py-template` and adapted them:
  - `.pre-commit-config.yaml`, `.vscode/settings.json`, `.github/workflows/ci.yml`,
    `.github/copilot-instructions.md`, `AGENTS.md`, `GETTING_STARTED.md`,
    `pyproject.toml` (bindings crate), and Python stubs under
    `crates/earlgrey-bindings/python/earlgrey_bindings/`.
- Packaging fixes: made `pyo3` optional and added an `extension-module`
  feature in `crates/earlgrey-bindings/Cargo.toml` so `maturin develop` works
  while `cargo test` can still link without libpython; copied top-level
  `LICENSE` into the bindings crate so maturin can read it.
- Tests & validation scaffolding:
  - Added a minimal pytest smoke test `tests/python/test_smoke.py` (1 passing test).
  - Added an equivalence-test template `tests/validation/test_equivalence_template.py`
    and `tests/validation/README.md` to guide reimplementation tests.
- Agent policy: updated `AGENTS.md` to require at least one automated equivalence
  test for any reimplemented function/component and documented expectations.

Representative files added/changed (non-exhaustive)

- `Cargo.toml` (workspace)
- `crates/earlgrey-*/` (initial crates and READMEs)
- `crates/earlgrey-bindings/` (Cargo.toml, pyproject.toml, src/lib.rs,
  python stubs, LICENSE)
- `nextflow/main.nf`, `nextflow/modules/*`, `nextflow/conf/dev.config`,
  `nextflow/conf/hpc.config`
- `scripts/nextflow-wrappers/prepare.sh`, `de_novo.sh`
- `plans/00_overview.md`, `plans/01_hpc_ssh_bsub.md`, … `plans/12_docs_ci.md`
- `.pre-commit-config.yaml`, `.vscode/settings.json`, `.github/workflows/ci.yml`
- `tests/python/test_smoke.py`, `tests/validation/test_equivalence_template.py`
- `AGENTS.md` (updated), `.github/copilot-instructions.md` (adapted)

Commands run / verification

- Ran `pytest tests/python/ -q` locally and observed `1 passed` for the smoke test.
- Verified `maturin develop` issues were resolvable by:
  - making `pyo3` optional and adding the `extension-module` feature,
  - copying `LICENSE` into the bindings crate, and
  - recommending use of a single active Python environment (venv or conda).

Rationale & decisions

- Use the `rust-py-template` config and stubs to enforce code style, CI, and
  testing conventions; adapt placeholders rather than instantiating a new repo
  so we can maintain history in-place while scaffolding.
- Keep heavy domain tools containerised; focus Rust reimplementation on
  I/O-bound parsing, interval merging, and divergence computations.
- Require equivalence tests to make reimplementation decisions measurable and
  auditable.

Next steps (recommended)

1. Run baseline profiling on small/medium example inputs (plans/02) to gather
   per-step metrics — enables wrap vs reimplement decisions.
2. Begin the first Rust reimplementation (`crates/earlgrey-io`) and add an
   equivalence test (use `tests/validation/` template).
3. Flesh out `nextflow/` modules and `variants.json` to begin AB experiments.
4. Add CI job to build and publish the bindings wheel (use `maturin build`) and
   add a test that imports the compiled extension in the integration step.

Notes & limitations

- This agent-log is a summary of local workspace changes only; it does not
  include any Git commits or pushes. Please create a commit/PR when ready.
- Some template placeholders remain (e.g., project-level metadata in template
  files); consider running `cargo generate` for a fresh instantiation if you
  prefer a separate new repository instead of an in-place scaffold.

If you want, I can now:

- commit these changes on a feature branch (I will not push remotely without
  your permission), or
- start the baseline profiling step and scaffold `metrics/collector.py` and
  `variants.json` next.
