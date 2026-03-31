# 12 — Docs & CI for incremental development

Goal

- Keep developer docs and CI minimal but useful to onboard contributors and validate changes.

Docs

- `docs/developer.md` — high-level iteration guide with Nextflow dev-mode, building containers, and running baseline profiles.
- `docs/architecture.md` — component diagrams and contract descriptions.

CI

- Quick checks on PRs:
  - Lint Python files, run small unit tests, build the `earlgrey-io` crate if present in a matrix (no heavy containers), and run static checks.
- Optional: provide a nightly job that builds containers and runs a small end-to-end smoke test on example data.

Deliverables

- `plans/12_docs_ci.md` (this file)
- example GitHub Actions `ci/` workflow templates for lint and smoke tests.

Next steps

- I can scaffold `docs/developer.md` and a basic `ci/lint-and-smoke.yml` if you want me to generate them now.
