# EarlGrey Nextflow DSL2 Pipeline

Nextflow DSL2 implementation of the EarlGrey transposable element annotation and classification pipeline.

## Overview

This Nextflow workflow decomposes EarlGrey into modular processes that:

- ✅ Enable per-step resource configuration and metrics collection
- ✅ Support parallelization of independent steps (via Nextflow's task graph)
- ✅ Enable AB testing of tool variants through configuration profiles
- ✅ Standard Singularity containerization for reproducibility
- ✅ Follow nf-core conventions (DSL2, process naming, input/output specs)

## Quick Start

### Basic usage

```bash
# Development mode (local execution, 2 CPUs)
nextflow run ./nextflow/main.nf --genome input.fa --species "Species name" -profile dev

# HPC submission (Sanger LSF, Singularity)
nextflow run ./nextflow/main.nf --genome input.fa --species "Species name" -profile hpc,singularity

# Help & parameter reference
nextflow run ./nextflow/main.nf --help
```

### Parameters

**Required:**

- `--genome` — Path to input genome FASTA
- `--species` — Species/strain name (for RepeatModeler database)

**Optional:**

- `--outdir` — Output directory (default: `results`)
- `--threads` — CPU threads per process (default: 4)
- `--memory` — Memory per process (default: 16 GB)
- `--repeat_type` — Repeat database: `eukarya`, `bacteria`, `archaea` (default: `eukarya`)
- `--variant` — AB testing profile (default: `default`)
- `--skip_repeatmodeler` — Skip de novo discovery (Dfam masking only)
- `--skip_divergence` — Skip divergence calculation

### Profiles

**Execution:**

- `-profile dev` — Local development (2 CPUs, 4 GB memory)
- `-profile hpc` — HPC cluster (LSF) with Singularity
- `-profile sanger` — Sanger-specific LSF/Docker configuration
- `-profile test` — CI/CD test profile

**Containerization:**

- `-profile singularity` — Enable Singularity (recommended for HPC)
- `-profile docker` — Enable Docker (development/local)
- `-profile conda` — Use Conda environments (alternative to containers)

Profiles can be combined: `-profile hpc,singularity`

### AB Testing (Variants)

Predefined profiles for comparing different tool configurations:

```bash
# Test RepeatMasker v4.0 (legacy)
nextflow run ./nextflow/main.nf --genome input.fa --species "Species" --variant repeatmasker_v4_0 -profile hpc

# Fast RepeatModeler (1 round)
nextflow run ./nextflow/main.nf --genome input.fa --species "Species" --variant repeatmodeler_fast -profile hpc

# Thorough RepeatModeler (5 rounds)
nextflow run ./nextflow/main.nf --genome input.fa --species "Species" --variant repeatmodeler_thorough -profile hpc

# Dfam masking only (no de novo)
nextflow run ./nextflow/main.nf --genome input.fa --species "Species" --variant no_denovo -profile hpc
```

See `conf/variants.config` for all available variants and instructions to add custom ones.

## Workflow Structure

### Main Components

**`main.nf`** — Entry point and orchestration

- Parameter validation and help system
- Workflow composition (defines process order)
- Nextflow reporting (trace, timeline, DAG)

**`nextflow.config`** — Configuration (nf-core style)

- Process resource defaults (CPU, memory, time)
- Execution profiles (dev, hpc, singularity, etc.)
- Trace/metrics collection settings
- Resource limit functions

**`conf/variants.config`** — AB testing profiles

- Tool version specifications
- Parameter overrides per variant
- Resource adjustments for specific variants

### Module Structure

Modules are organized by function under `./modules/`:

```
modules/
├── prepare/               # Genome preparation
│   └── main.nf           # PREPARE_GENOME process
├── repeat_mask/           # RepeatMasker invocation
│   └── main.nf           # REPEAT_MASK_INITIAL, REPEAT_MASK_FINAL
├── database/              # RepeatModeler database setup
│   └── main.nf           # BUILD_DATABASE process
├── de_novo/               # De novo repeat discovery
│   └── main.nf           # DE_NOVO_ROUNDX (multi-round wrapper)
├── classify/              # Repeat classification
│   └── main.nf           # CLASSIFY_REPEATS process
├── merge/                 # Library merging
│   └── main.nf           # MERGE_REPEATS process
├── divergence/            # Sequence divergence analysis
│   └── main.nf           # CALCULATE_DIVERGENCE process
└── summary/               # Final reporting
    └── main.nf           # GENERATE_SUMMARY process
```

### Process List

| Process              | Purpose                                      | Tool                                   | Time         | Parallelizable    |
| -------------------- | -------------------------------------------- | -------------------------------------- | ------------ | ----------------- |
| PREPARE_GENOME       | Decompress, validate, index genome           | samtools                               | ~1 min       | No                |
| REPEAT_MASK_INITIAL  | Mask repetitive sequences (Dfam library)     | RepeatMasker 4.1+                      | 1-8 hrs      | Yes (via threads) |
| BUILD_DATABASE       | Create RepeatModeler database                | RepeatModeler                          | ~1 min       | No                |
| DE_NOVO_ROUNDX       | Discover novel repeat families (multi-round) | RepeatModeler, TRF, RECON, RepeatScout | 1-48+ hrs    | Yes (via threads) |
| CLASSIFY_REPEATS     | Classify discovered families                 | RepeatClassifier                       | 10 min—2 hrs | Partial           |
| MERGE_REPEATS        | Combine novel + database libraries           | Custom script                          | 1-5 min      | No                |
| REPEAT_MASK_FINAL    | Re-mask genome with merged library           | RepeatMasker + novel libs              | 1-8 hrs      | Yes (via threads) |
| CALCULATE_DIVERGENCE | Analyze age/divergence of repeats            | divsum (in-house)                      | 10 min—1 hr  | No                |
| GENERATE_SUMMARY     | Create final report & statistics             | Custom scripts                         | 5-10 min     | No                |

## Development: Adding a New Process

### 1. Create a module file

Create `modules/<function>/main.nf`:

```nextflow
nextflow.enable.dsl = 2

process MY_NEW_PROCESS {
    tag "${meta.id}"
    label 'process_single'  // Recommended: use labels for resource scaling

    // Input: workflow will supply from upstream processes
    input:
    tuple val(meta), path(input_file)

    // Output:
    output:
    tuple val(meta), path('output.txt'), emit: result

    // Script: wrap external tool or Python/Rust code
    script:
    """
    my_tool --input '${input_file}' --output output.txt --threads ${task.cpus}
    """
}

// Optional: export a workflow-level helper function for re-use
workflow MY_NEW_PROCESS {
    take:
    input_ch

    main:
    MY_NEW_PROCESS(input_ch)

    emit:
    result = MY_NEW_PROCESS.out.result
}
```

### 2. Follow nf-core conventions

**Process naming:** `PROCESS_NAME` (all caps, underscores)

**Input/output:** Structured tuples with metadata:

```nextflow
input:
tuple val(meta), path(files)  // meta = map with run_id, species, etc.

output:
tuple val(meta), path(results), emit: result_type
```

**Labels for resource management:**

```nextflow
label 'process_single'      // Single-threaded
label 'process_low'         // Low resource
label 'process_medium'      // Medium resource
label 'process_high'        // High resource (multi-threaded)
label 'process_long'        // Long-running (adjust time limits)
```

Defines labels in `nextflow.config`:

```groovy
process {
    withLabel: 'process_high' {
        cpus = { check_max( params.threads, 'cpus' ) }
        memory = { check_max( 16.GB * task.attempt, 'memory' ) }
    }
}
```

### 3. Include in main workflow

In `main.nf`, add an include statement:

```nextflow
include { MY_NEW_PROCESS } from './modules/myfunction/main.nf'
```

Integrate into workflow DAG:

```nextflow
workflow {
    input_ch = ...
    MY_NEW_PROCESS(input_ch)
    output_ch = MY_NEW_PROCESS.out.result
}
```

### 4. Test the module

```bash
# Dry-run (preview task graph)
nextflow run ./nextflow/main.nf --genome test.fa --species test -profile dev -n

# Execute with trace for debugging
nextflow run ./nextflow/main.nf --genome test.fa --species test -profile dev -with-trace
```

## Metrics & Performance Profiling

### Automatic Metrics Collection

Each Nextflow run produces:

- **`pipeline_info/execution_trace.txt`** — Per-task CSV with walltime, memory, CPU, I/O
- **`pipeline_info/execution_report.html`** — Interactive HTML report
- **`pipeline_info/execution_timeline.html`** — Visual timeline of task execution
- **`pipeline_info/pipeline_dag.svg`** — Directed task graph

### Comparing Variants (AB Testing)

```bash
# Run variant A
nextflow run ./nextflow/main.nf --genome test.fa --species S --variant default --outdir results_default

# Run variant B
nextflow run ./nextflow/main.nf --genome test.fa --species S --variant repeatmodeler_thorough --outdir results_thorough

# Compare metrics
diff results_default/pipeline_info/execution_trace.txt results_thorough/pipeline_info/execution_trace.txt
```

Trace CSV includes: `task_id`, `name`, `duration`, `realtime`, `%cpu`, `rss` (RSS memory), etc.

## nf-core Integration

This workflow follows nf-core conventions but is **not** a full nf-core pipeline (to avoid overhead). Key alignments:

✅ **Adopted:**

- DSL2 with structured processes
- nf-core naming conventions (CAPS process names, `meta` tuple pattern)
- Resource labels and dynamic CPU scaling
- Trace/report/timeline collection
- Configuration profiles and `check_max()` pattern

❌ **Intentionally skipped (for now):**

- Full nf-core schema validation (`nextflow_schema.json`)
- nf-core plugin integration
- AWS Batch/Kubernetes profiles (can be added per site)

**Future:** As the workflow matures, converting to full nf-core compliance is straightforward (mainly schema additions).

## Known Limitations & Roadmap

### Phase 3a (Current): Scaffold & Structure ✓

- [x] Main workflow DSL2 structure
- [x] nf-core-style configuration
- [x] AB testing variant framework
- [ ] Individual process implementations (pending)

### Phase 3b: Module Implementation

- [ ] Implement `PREPARE_GENOME` process
- [ ] Implement `REPEAT_MASK_*` processes (RepeatMasker wrapper)
- [ ] Implement `BUILD_DATABASE` & `DE_NOVO_ROUNDX` (RepeatModeler wrapper)
- [ ] Implement `CLASSIFY_REPEATS`, `MERGE_REPEATS`, `CALCULATE_DIVERGENCE`, etc.
- [ ] Integration tests & validation

### Phase 3c: Advanced Features

- [ ] Multi-genome batching (process multiple genomes in parallel)
- [ ] Caching & resumable workflows (`-resume` flag)
- [ ] AWS/Kubernetes profiles (if needed)
- [ ] Metrics aggregation for large-scale runs

## Contributing

When adding new processes or features:

1. Follow nf-core process conventions (uppercase names, meta tuples)
2. Add labels for resource management
3. Include error handling and graceful failures
4. Document inputs/outputs in the process comments
5. Add tests in `tests/` (if applicable)
6. Update this README with new processes

## References

- **Nextflow DSL2 documentation:** https://www.nextflow.io/docs/latest/dsl2.html
- **nf-core guidelines:** https://nf-co.re/guidelines
- **EarlGrey main repo:** https://github.com/TobyBaril/EarlGrey
- **Nextflow best practices:** https://www.nextflow.io/docs/latest/sharing.html#guidelines
