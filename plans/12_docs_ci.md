# 12 — Docs & CI for incremental development

Goal

- Keep developer docs and CI minimal but useful to onboard contributors and validate changes.

Docs

- `docs/developer.md` — high-level iteration guide with Nextflow dev-mode, building containers, and running baseline profiles.
- `docs/architecture.md` — component diagrams and contract descriptions.

CI

- Quick checks on PRs:
  - Lint Python files, run small unit tests, build the `earlgrey-io` crate if present in a matrix (no heavy containers), and run static checks.
  - **maturin build step:** the `earlgrey-bindings` Python extension must be rebuilt with `maturin develop --features extension-module` any time `crates/earlgrey-bindings/` or `crates/earlgrey-io/` changes. Add this as an explicit CI step before running `pytest tests/python/`. On CI, use `maturin build --release --features extension-module` and install the wheel, rather than `develop`, to avoid needing the Rust toolchain at test time.
  - Include `cargo fmt --check`, `cargo clippy -- -D warnings`, and `cargo test` in the Rust CI job.
  - Include `pyright` strict-mode check on `crates/earlgrey-bindings/python/` and `tests/python/`.
  - **blobtk path dep:** the CI runner must check out `../../blobtoolkit/blobtk` (or pin a git dep in `Cargo.toml`) so the path dependency resolves. Document this in `docs/developer.md` and add a check to the CI config.
- Optional: provide a nightly job that builds containers and runs a small end-to-end smoke test on example data.

Deliverables

- `plans/12_docs_ci.md` (this file)
- example GitHub Actions `ci/` workflow templates for lint and smoke tests.

Next steps

- I can scaffold `docs/developer.md` and a basic `ci/lint-and-smoke.yml` if you want me to generate them now.
