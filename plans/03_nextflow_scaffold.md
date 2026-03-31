# 03 — Nextflow DSL2 scaffold (dev-mode)

Purpose

- Provide a minimal Nextflow DSL2 skeleton for iterative development, dev-mode testing, and future nf-core alignment.
- Keep the scaffold small: `main.nf`, a `modules/` folder with 2–3 example modules, `conf/` for local and HPC profiles, and `scripts/nextflow-wrappers/` for per-process thin wrappers.

Design principles

- Dev-mode must be easy: `-profile dev` runs with locally available containers and small inputs.
- Keep processes idempotent and produce `metrics.json` for AB testing.
- Expose process inputs/outputs and allow simple `params.variant` to switch implementations.

Recommended layout

- `main.nf` — pipeline graph and top-level params
- `modules/` — DSL2 modules (e.g., `prepare`, `de_novo`, `strainer`, `postprocess`)
- `conf/` — `nextflow.config`, `conf/dev.config`, `conf/hpc.config`
- `scripts/nextflow-wrappers/` — thin bash/python wrappers for each process
- `docs/` — developer notes for adding new variants/processes

Minimal `main.nf` example

```groovy
nextflow.enable.dsl=2
include { prepare } from './modules/prepare/main.nf'
include { deNovo } from './modules/de_novo/main.nf'

workflow {
  params.variant = params.variant ?: 'default'

  prepare()
  deNovo()
}
```

Variant switching pattern

- Use `params.variant` or `params.variants.json` to choose which implementation to run for each step.
- Each module checks `params.variant` and branches to the appropriate implementation or wrapper.

Process outputs & metrics

- Each process writes a `metrics.json` alongside its outputs containing: walltime, cpu, memory, command, version, and a `variant_id`.
- Provide a small `metrics/collector.py` script (later) to gather metrics across runs for AB analysis.

Dev-mode profile (`conf/dev.config`)

- Use Singularity/Docker images that are lightweight or mocked.
- Keep default resource requests small (1–2 cpus, 2–4 GB memory).

Acceptance criteria

- Running `nextflow run main.nf -profile dev` executes the scaffold on example data producing sample outputs and `metrics.json` files.
- `modules/` contains at least `prepare` and `de_novo` example modules with working wrappers.

Next steps

- I can scaffold `main.nf`, two modules, `conf/dev.config`, and example wrappers under `scripts/nextflow-wrappers/` if you want me to generate the files now.
