**Step 1 — Nextflow & Devtools (Complete)**

Summary

- Implemented a minimal Nextflow DSL2 scaffold to host the future orchestration.
- Implemented developer helpers so baseline runs and Nextflow runner jobs can be submitted to LSF via SSH from the repository.

Key artifacts

- Nextflow scaffold: `nextflow/main.nf`, `nextflow/nextflow.config`, `nextflow/modules/README.md`
- Devtools helpers: `devtools/baseline_submit.py` (fetch + submit `earlGrey`), `devtools/nextflow_submit.py` (submit Nextflow runner)
- Makefile targets: `devtools/Makefile` — `dry-run`, `submit`, `nextflow-dry-run`, `nextflow-submit`
- Docs: `devtools/README.md` (usage) and `agent-logs/2026-04-01_001_step1_nextflow-devtools.md`

Reproduction (how to reproduce what I ran)

1. Prepare a local dev config (copy and update):

```bash
cp devtools/config/baseline_config.yaml.example devtools/config/baseline_config.yaml
# edit devtools/config/baseline_config.yaml to set `ssh_host`, remote paths and `remote.init`
```

2. Dry-run the baseline submit (prints job script preview):

```bash
make -C devtools dry-run ID=yeast_R64
```

3. Dry-run the Nextflow wrapper:

```bash
make -C devtools nextflow-dry-run ID=nextflow_test_out
```

4. Submit Nextflow wrapper (debug trace on remote by default):

```bash
make -C devtools nextflow-submit ID=nextflow_test_out
```

Notes & constraints

- The Nextflow scaffold is minimal and will not run `earlGrey` until you implement
  the necessary processes in `nextflow/main.nf` or call the baseline job from
  within a process.
- `devtools/baseline_submit.py` remains the canonical developer helper for
  launching single baseline `earlGrey` jobs; `nextflow_submit.py` is a wrapper
  to run Nextflow as an LSF job.
- No changes were made to the main `README.md`; all progress notes are stored
  under `docs/refactor/` and `agent-logs/` per your request.

Next steps (step 2)

- Implement Nextflow processes that run the same work as `baseline_submit.py`,
  producing outputs compatible with the baseline job for equivalence testing.
- Create pytest-based equivalence tests and fixtures to compare baseline vs
  Nextflow outputs on a small example genome.
