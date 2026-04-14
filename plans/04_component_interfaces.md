# 04 — Component interfaces & single-step iteration

## Goal

- Define stable, minimal interfaces for each pipeline process so that:
  1. Individual steps can be run in isolation against fixture data (no full pipeline rerun needed)
  2. Alternate implementations can be swapped in for one step at a time (AB testing)
  3. The interfaces are thin enough that Rust reimplementations can satisfy them without changing the surrounding pipeline

---

## Status (2026-04-13): harness design — not yet implemented

---

## The core problem: `-resume` is not enough for iteration

Nextflow's `-resume` reuses cached work from a specific `.nf_work/` directory on
the cluster. It has two important limitations for iterative development:

- **Cache invalidation cascades.** Changing MERGE_REPEATS invalidates the cache
  for it and all downstream processes. On a large genome this still means waiting
  for CALCULATE_DIVERGENCE + GENERATE_SUMMARY to rerun.
- **Tied to a single work directory.** Iterating on a module requires the original
  run's work dir to still be present and intact on the cluster.

The approach in this plan replaces reliance on `-resume` for iteration with a
**fixture capture + named entry point** pattern.

---

## Part A — Fixture capture

### What fixtures are

After a clean end-to-end pipeline run, the inputs and outputs of each process
exist inside `.nf_work/<hash>/`. A fixture is a stable copy of those files stored
in `tests/fixtures/<assembly_id>/<process_name>/` so they can be used as inputs
to single-step runs.

### Capture script

`devtools/capture_fixtures.py` (to be implemented):

```
usage: capture_fixtures.py --work-dir <remote .nf_work path>
                            --assembly <id>
                            --processes [MERGE_REPEATS CLASSIFY_REPEATS ...]
                            --out-dir tests/fixtures/
```

- Reads Nextflow's `trace.txt` to find the work dir hash for each process.
- Copies inputs + outputs via `rsync` from the cluster to `tests/fixtures/<assembly>/<process>/`.
- Writes a `manifest.json` recording process name, assembly, genome size, and file checksums.

### Priority processes to capture

These are the processes most likely to be iterated on or replaced:

| Process                | Reason                                    |
| ---------------------- | ----------------------------------------- |
| `MERGE_REPEATS`        | Core defrag logic; Rust candidate         |
| `CLASSIFY_REPEATS`     | TEstrainer; memory-bound; may be replaced |
| `CALCULATE_DIVERGENCE` | Python script; Rust candidate             |
| `GENERATE_SUMMARY`     | R scripts; format-sensitive               |

Build in capture of all intermediate processes — later captures cost nothing if
the fixtures directory is already populated.

---

## Part B — Named entry points for single-step runs

### Nextflow `-entry` mechanism

Nextflow DSL2 supports multiple named workflow blocks. A file
`nextflow/test/steps.nf` defines one named workflow per process:

```groovy
workflow test_MERGE_REPEATS {
    genome_ch  = Channel.fromPath("${params.fixture_dir}/genome/*")
                        .map { f -> [ [id: params.assembly], f ] }
    out_ch     = Channel.fromPath("${params.fixture_dir}/repeat_out/*")
                        .map { f -> [ [id: params.assembly], f ] }
    // ... other inputs from fixture_dir
    MERGE_REPEATS(genome_ch, out_ch, tbl_ch, dict_ch, heliano_ch)
}
```

Run a single step against fixtures:

```bash
nextflow run nextflow/test/steps.nf \
    -entry test_MERGE_REPEATS \
    -profile hpc \
    --fixture_dir tests/fixtures/yeast_R64 \
    --assembly yeast_R64 \
    --outdir test_out/merge_repeats_001/
```

This is entirely decoupled from any previous pipeline run's work directory.

### Makefile target to add

```makefile
# Run a single pipeline step using fixture data
step-run:
	cd nextflow && nextflow run test/steps.nf \
	    -entry test_$(MODULE) \
	    -profile $(PROFILES) \
	    --fixture_dir ../tests/fixtures/$(FIXTURE) \
	    --assembly $(FIXTURE) \
	    --outdir ../test_out/$(MODULE)_$(RUN_ID)/
```

Usage: `make step-run MODULE=MERGE_REPEATS FIXTURE=yeast_R64 RUN_ID=001`

---

## Part C — Interface contracts (feeds Rust reimplementations)

Each process has a minimal interface contract defined by its inputs, outputs, and
an acceptance test against the fixture. The contract is what a Rust replacement
must satisfy — not the internal implementation.

| Process                | Key inputs                                          | Key outputs                         | Acceptance test                                        |
| ---------------------- | --------------------------------------------------- | ----------------------------------- | ------------------------------------------------------ |
| `MERGE_REPEATS`        | genome, repeat.out, repeat.tbl, dict, [heliano.gff] | filteredRepeats.gff, .bed, .summary | GFF row count ±5%, BED coords identical to ref fixture |
| `CLASSIFY_REPEATS`     | de-novo families FASTA, prep genome                 | strained library FASTA              | Library sequence count ±10%                            |
| `CALCULATE_DIVERGENCE` | prep genome, filtered GFF, RM library               | divergence GFF + summary            | Kimura bins within ±1% of fixture                      |
| `GENERATE_SUMMARY`     | filtered GFF, summary, RM tbl                       | pie chart SVG + count tables        | Count table values identical                           |

Contracts are enforced by `tests/fixtures/<assembly>/<process>/expected/` — the
expected outputs from the baseline run. The single-step test workflow writes to
`--outdir` and a comparison script diffs against expected.

### Rust interface targets (lower priority — after harness is built)

These are the crates planned once the single-step harness exists to test against:

1. **`earlgrey-merge`** — re-implements MERGE_REPEATS merge logic.
   - Input interface: GFF stream + overlap rules
   - Output interface: merged GFF stream
   - Validated by: `make step-run MODULE=MERGE_REPEATS` with `--variant rust_merge`

2. **`earlgrey-divergence`** — re-implements divergence calculation.
   - Input: genome FASTA + GFF
   - Output: per-element Kimura distance table
   - Validated by: `make step-run MODULE=CALCULATE_DIVERGENCE --variant rust_divergence`

3. **`earlgrey-io`** — streaming FASTA/GFF parsers.
   - Used internally by the above; not a standalone process.
   - Blobtk `file_reader()` covers location/compression; needletail covers FASTA streaming.
   - GFF parsing must be written fresh — no blobtk equivalent.

---

## Part D — AB testing with single-step harness

The single-step entry points are also the AB testing mechanism. To compare a
new implementation against the canonical one:

1. **Capture baseline fixture** from a known-good run.
2. **Run canonical:** `make step-run MODULE=MERGE_REPEATS FIXTURE=yeast_R64 RUN_ID=canonical`
3. **Run candidate:** `make step-run MODULE=MERGE_REPEATS FIXTURE=yeast_R64 RUN_ID=rust_merge --variant rust_merge`
4. **Compare:** `devtools/compare_step_outputs.py canonical/ rust_merge/` — diffs output
   file structure, row counts, key metrics; writes `comparison.json`.

This is faster than running the full pipeline twice, and doesn't require the two
variants to coexist inside a running Nextflow execution.

Full-pipeline AB testing (using `params.variant` to swap a process inside a complete
run) remains useful for integration validation — see `05_metrics_ab_harness.md` —
but single-step iteration comes first.

---

## Deliverables (ordered)

1. `devtools/capture_fixtures.py` — fixture capture from a completed run's work dir
2. `nextflow/test/steps.nf` — named entry points for all iteratable processes
3. `Makefile` targets: `capture-fixtures`, `step-run`
4. `tests/fixtures/yeast_R64/` — first fixture set (from yeast baseline run, once complete)
5. `devtools/compare_step_outputs.py` — diff two step output directories, write comparison.json
6. Rust crates (`earlgrey-merge`, `earlgrey-divergence`, `earlgrey-io`) — after harness is in place

---

## Dependencies

- Step 3 (`03_nextflow_scaffold.md`): pipeline must produce a clean end-to-end run
  before fixtures can be captured. **Baselines are running as of 2026-04-13.**
- Step 5 (`05_metrics_ab_harness.md`): AB harness uses the same comparison infrastructure;
  `compare_step_outputs.py` feeds into `metrics/collector.py`.
