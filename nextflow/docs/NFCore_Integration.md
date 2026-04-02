# nf-core Module Integration

This document surveys available nf-core modules for the tools used in EarlGrey, and recommends when to adopt vs. when to develop custom wrappers.

## Philosophy

- ✅ **Use nf-core modules** for well-supported bioinformatics tools (BLAST, MAFFT, samtools)
  - Vetted, well-tested, regularly updated
  - Pre-configured containers & resource requests
  - Standard input/output patterns

- ⚠️ **Reference nf-core patterns** for specialized tools (RepeatMasker, RepeatModeler, TRF)
  - Adopted tools may not have official nf-core modules
  - Custom wrappers following nf-core conventions achieve similar benefits
  - Easier to customize for project-specific needs

- ❌ **Don't force nf-core dependencies** for tight pipelines
  - nf-core modules are modular by design (loose coupling)
  - Full nf-core framework overhead is unnecessary for earlGrey
  - Custom DSL2 modules are sufficient and more lightweight

## Survey: Available nf-core Modules

### Widely Used Tools (Official nf-core Modules Available)

| Tool              | nf-core Module                     | Status         | Recommendation                                |
| ----------------- | ---------------------------------- | -------------- | --------------------------------------------- |
| **BLAST/RMBlast** | `nf-core/modules/bio/blast/blastn` | ✅ Available   | **Use nf-core module** for BLAST invocations  |
| **MAFFT**         | `nf-core/modules/bio/mafft`        | ✅ Available   | **Use nf-core module** if alignment needed    |
| **samtools**      | `nf-core/modules/bio/samtools/*`   | ✅ Available   | **Use nf-core modules** for indexing/stats    |
| **TRF**           | `nf-core/modules/bio/trf`          | ✅ Available   | **Reference** (custom wrapper may be simpler) |
| **RepeatMasker**  | Not in nf-core                     | ❌ Unavailable | Custom wrapper (see below)                    |
| **RepeatModeler** | Not in nf-core                     | ❌ Unavailable | Custom wrapper (see below)                    |
| **RepeatScout**   | Not in nf-core                     | ❌ Unavailable | Bundled in RepeatModeler                      |
| **RECON**         | Not in nf-core                     | ❌ Unavailable | Bundled in RepeatModeler                      |
| **cd-hit**        | `nf-core/modules/bio/cdhit/cdhit`  | ✅ Available   | **Reference** (may not be needed)             |

### How to Adopt nf-core Modules

**Option 1: Direct inclusion** (recommended for standard tasks)

```nextflow
// In your module file: modules/my_tool/main.nf
include { BLAST_BLASTN } from '../nf-core/modules/bio/blast/blastn'

process MY_BLAST_WRAPPER {
    input:
    tuple val(meta), path(query)
    val(db_path)

    output:
    tuple val(meta), path('*.txt')

    script:
    // ... wrapper logic
}
```

**Option 2: Reference for patterns** (recommended for specialized tools)

When adapting nf-core module code as a template for RepeatMasker, RepeatModeler, etc.:

```groovy
// Inspect nf-core module for best practices:
// https://github.com/nf-core/modules/blob/master/modules/bio/blast/blastn/main.nf

// Key patterns to replicate in custom modules:
// - Meta tuple input: tuple val(meta), path(files)
// - Resource labels: label 'process_high'
// - Container spec: singularity / docker / conda
// - Error handling: errorStrategy, maxRetries
// - Publish directive: publishDir for results
```

## Custom Module Strategy

### RepeatMasker Wrapper

**Why custom:** nf-core doesn't have a RepeatMasker module yet, and RepeatMasker's usage pattern is very specialized (iterative masking with custom libraries).

**Design:**

```nextflow
process REPEAT_MASK {
    tag "${meta.id}"
    label 'process_high'
    singularity 'docker://repeatmasker/repeatmasker:latest'

    input:
    tuple val(meta), path(genome)
    path(library)  // Either Dfam (built-in) or custom
    val(engine)    // 'rmblast', 'crossmatch', etc.

    output:
    tuple val(meta), path('*.masked'), emit: masked
    tuple val(meta), path('*.out'),    emit: repeats

    script:
    """
    RepeatMasker -pa ${task.cpus} -lib ${library} -engine ${engine} ${genome}
    """
}
```

**Containers:** Recommended to use:

- `docker://repeatmasker/repeatmasker:4.1.2` (official)
- Or Singularity from Biocontainers: `singularity://depot.galaxyproject.org/.../repeatmasker:4.1.2`

### RepeatModeler Wrapper

**Why custom:** Multi-round orchestration is complex; better handled as a custom workflow rather than a single monolithic module.

**Design:**

```nextflow
// Multi-process approach:
process REPEATMODELER_DB { ... }    // Build database
process REPEATMODELER_ROUND { ... } // Single round (will loop)
process REPEATMODELER_CLASSIFY { ... } // Classify results

// Orchestration in main workflow handles multi-round iteration
workflow DE_NOVO_ROUNDS {
    take:
    database_ch
    max_rounds

    main:
    results = []
    for (round in 1..max_rounds) {
        REPEATMODELER_ROUND(database_ch, round)
        results.add(REPEATMODELER_ROUND.out)
    }

    emit:
    families = results
}
```

**Container:**

- `docker://dfam/tetools:latest` (bundles RepeatModeler, TRF, RECON, etc.)
- Or build custom: `singularity://galaxy/.../tetools:1.0` w/ all dependencies

## Validation & Equivalence Testing

### When adopting an nf-core module

1. **Verify compatibility** with earlGrey's input/output format
2. **Test independently** with sample data
3. **Compare output** versus legacy earlGrey runs (record baseline metrics)
4. **Document configuration** (see `AGENTS.md` for equivalence testing protocol)

Example workflow:

```bash
# Test nf-core BLAST module
nextflow run tests/nf/test_blast_module.nf -profile dev --input test.fa

# Compare to legacy
diff <(nextflow run tests/nf/test_blast_module.nf ...) legacy_output.txt
```

## Recommendations for Phase 3b

### Immediate (use nf-core where applicable)

1. ✅ **BLAST invocation** → Use _`nf-core/modules/bio/blast/blastn`_ directly
   - Standard input/output, no customization needed
   - Well-tested, updated regularly

2. ✅ **samtools** (indexing, stats) → Use _`nf-core/modules/bio/samtools/*`_ as reference
   - Follow pattern for PREPARE_GENOME process

3. ⚠️ **MAFFT** (if alignment needed) → Reference _`nf-core/modules/bio/mafft`_
   - Check if actually needed in earlGrey pipeline (may not be critical)

### Custom wrappers (following nf-core patterns)

1. ✅ **RepeatMasker** → Custom process `REPEAT_MASK`
   - Use official container: `repeatmasker/repeatmasker:4.1.2`
   - Input/output: meta tuple, library path, engine setting

2. ✅ **RepeatModeler** → Custom multi-process workflow `DE_NOVO_ROUNDS`
   - Use bundled container: `dfam/tetools:latest`
   - Handle multi-round iteration in workflow logic

3. ✅ **TRF** → Reference nf-core pattern, custom wrapper
   - Often bundled with other tools (RepeatModeler)
   - Lightweight; stand-alone wrapper if needed

## Future: Contributing Modules Back to nf-core

If RepeatMasker and RepeatModeler modules prove robust, consider:

1. **Generalize** for nf-core compatibility (standard schemas, naming conventions)
2. **Submit PR** to nf-core/modules (requires peer review, ~2-4 weeks)
3. **Benefits:**
   - Broader adoption and feedback
   - Reduced maintenance burden (community-supported)
   - Integration with other TE pipelines

## References

- **nf-core modules browser:** https://nf-co.re/modules/
- **Module contributor guide:** https://nf-co.re/developers/modules
- **Official BLAST module:** https://github.com/nf-core/modules/tree/master/modules/bio/blast
- **Singularity containers (Biocontainers):** https://quay.io/organization/biocontainers
- **RepeatMasker Docker:** https://hub.docker.com/r/repeatmasker/repeatmasker
- **TETOOLS (Dfam Docker):** https://hub.docker.com/r/dfam/tetools

## Checklist for Phase 3b Implementation

- [ ] Adopt _`nf-core/modules/bio/blast/blastn`_ for BLAST calls
- [ ] Create custom _`REPEAT_MASK`_ process (template → `modules/repeat_mask/main.nf`)
- [ ] Create custom _`DE_NOVO_ROUNDS`_ workflow (template → `modules/de_novo/main.nf`)
- [ ] Test custom modules in isolation (`tests/nf/test_repeatmasker.nf`, etc.)
- [ ] Add equivalence tests vs. legacy earlGrey (validate output correctness)
- [ ] Document container versions in `nextflow.config` and module headers
- [ ] Create integration test for full pipeline (`tests/nf/full_pipeline_test.nf`)
