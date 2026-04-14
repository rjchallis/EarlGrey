#!/usr/bin/env nextflow
/*
========================================================================================
    EarlGrey: Transposable Element Pipeline
    Nextflow DSL2 Workflow (refactor/performance-optimisation branch)
========================================================================================

    Usage:
        nextflow run ./nextflow/main.nf \
            --genome input.fasta \
            --species "Species name" \
            --outdir results \
            -profile hpc,singularity

    Run with --help for full parameter documentation.
========================================================================================
*/

nextflow.enable.dsl = 2

// ============================================================================
// Module imports
// ============================================================================

include { PREPARE_GENOME        } from './modules/prepare_genome/main.nf'
include { REPEAT_MASK_INITIAL   } from './modules/repeat_mask_initial/main.nf'
include { BUILD_DATABASE        } from './modules/build_database/main.nf'
include { DE_NOVO_REPEAT        } from './modules/de_novo_repeat/main.nf'
include { CLASSIFY_REPEATS      } from './modules/classify_repeats/main.nf'
include { CLUSTER_LIBRARY       } from './modules/cluster_library/main.nf'
include { REPEAT_MASK_FINAL     } from './modules/repeat_mask_final/main.nf'
include { HELIANO               } from './modules/heliano/main.nf'
include { MERGE_REPEATS         } from './modules/merge_repeats/main.nf'
include { CALCULATE_DIVERGENCE  } from './modules/calculate_divergence/main.nf'
include { GENERATE_SUMMARY      } from './modules/generate_summary/main.nf'
include { SOFT_MASK             } from './modules/soft_mask/main.nf'

// ============================================================================
// Default parameter values
// ============================================================================


// ============================================================================
// Help message
// ============================================================================

if (params.help) {
    log.info """
    =============================================================================
    EarlGrey — Transposable Element Annotation Pipeline
    =============================================================================

    Usage:
      nextflow run ./nextflow/main.nf --genome GENOME --species SPECIES [options]

    Mandatory:
      --genome STRING           Input genome FASTA (gzipped or plain)
      --species STRING          Species name for RepeatModeler

    Optional masking (pick at most one):
      --repeat_species STRING   RepeatMasker species/taxon for initial Dfam mask
      --custom_lib PATH         Custom consensus library for initial mask

    Other options:
      --outdir PATH             Output directory              [default: results]
      --threads INT             CPUs per process               [default: 4]
      --repeat_type STRING      eukarya | bacteria | archaea   [default: eukarya]
      --flank_bases INT         TEstrainer flanking bp          [default: 1000]
      --blast_iterations INT    TEstrainer BEAT iterations      [default: 10]
      --max_sequences INT       TEstrainer max seqs             [default: 20]
      --min_sequences INT       TEstrainer min seqs             [default: 3]
      --cluster_library         Cluster TE library (cd-hit-est 80-80-80)
      --remove_short yes|no     Remove <100 bp annotations      [default: no]
      --soft_mask               Generate soft-masked genome
      --heliano                 Run HELIANO Helitron detector (requires heliano in PATH)
      --skip_divergence         Skip divergence calculation
      --variant STRING          AB testing variant profile       [default: default]

    Profiles:
      -profile dev              Local (2 CPUs, 4 GB RAM)
      -profile hpc              HPC/LSF cluster
      -profile hpc,singularity  HPC + Singularity containers

    Examples:
      # Basic run
      nextflow run ./nextflow/main.nf --genome genome.fa --species "Homo sapiens"

      # With initial Dfam masking on HPC
      nextflow run ./nextflow/main.nf \\
          --genome genome.fa --species "Homo sapiens" \\
          --repeat_species eukarya \\
          -profile hpc,singularity

      # AB test: fast RepeatModeler
      nextflow run ./nextflow/main.nf \\
          --genome genome.fa --species "Homo sapiens" \\
          --variant repeatmodeler_fast -profile hpc,singularity
    =============================================================================
    """.stripIndent()
    exit 0
}

// ============================================================================
// Input validation
// ============================================================================

if (!params.genome) {
    log.error "ERROR: --genome is required. Run with --help for usage."
    exit 1
}
if (!params.species) {
    log.error "ERROR: --species is required. Run with --help for usage."
    exit 1
}
if (params.repeat_species && params.custom_lib) {
    log.error "ERROR: provide --repeat_species OR --custom_lib, not both."
    exit 1
}

// ============================================================================
// Load variant configuration if specified
// ============================================================================

if (params.variant != 'default' && file(params.variants_config).exists()) {
    includeConfig params.variants_config
}

// ============================================================================
// Workflow
// ============================================================================

workflow {

    log.info """
    =============================================================================
    EarlGrey Nextflow DSL2 Pipeline
    =============================================================================
    Genome          : ${params.genome}
    Species         : ${params.species}
    Output dir      : ${params.outdir}
    Threads         : ${params.threads}
    Variant         : ${params.variant}
    Initial masking : ${params.repeat_species ?: params.custom_lib ?: 'none'}
    Cluster library : ${params.cluster_library}
    Script dir      : ${params.script_dir}
    =============================================================================
    """.stripIndent()

    // ── Build input channel ──────────────────────────────────────────────────
    def genome_file = file(params.genome, checkIfExists: true)
    def meta = [
        id:      genome_file.baseName.replaceAll(/\.(fasta|fa|fna|fas)$/, ''),
        species: params.species
    ]
    genome_ch = Channel.of([ meta, genome_file ])

    // ── Step 1: Prepare genome ───────────────────────────────────────────────
    PREPARE_GENOME(genome_ch)

    // ── Step 2 (optional): Initial RepeatMasker pass ─────────────────────────
    def has_initial_mask = params.repeat_species || params.custom_lib
    if (has_initial_mask) {
        def custom_lib_file = params.custom_lib
            ? file(params.custom_lib, checkIfExists: true)
            : file("${projectDir}/assets/NO_FILE")

        REPEAT_MASK_INITIAL(
            PREPARE_GENOME.out.genome,
            params.repeat_species ?: '',
            custom_lib_file
        )
        db_input_ch   = REPEAT_MASK_INITIAL.out.masked
        initial_lib   = REPEAT_MASK_INITIAL.out.library.map { _meta, f -> f }
    } else {
        db_input_ch   = PREPARE_GENOME.out.genome
        initial_lib   = Channel.value(file("${projectDir}/assets/NO_FILE"))
    }

    // ── Step 3: Build RepeatModeler database ─────────────────────────────────
    BUILD_DATABASE(db_input_ch)

    // ── Step 4: De-novo repeat discovery ─────────────────────────────────────
    DE_NOVO_REPEAT(BUILD_DATABASE.out.db)

    // ── Step 5: Refine and classify de-novo library (TEstrainer) ─────────────
    CLASSIFY_REPEATS(
        DE_NOVO_REPEAT.out.families,
        PREPARE_GENOME.out.genome
    )

    // ── Step 6 (optional): Cluster library at 80-80-80 ───────────────────────
    strained_lib_ch = params.cluster_library
        ? CLUSTER_LIBRARY(CLASSIFY_REPEATS.out.library).library
        : CLASSIFY_REPEATS.out.library

    // ── Step 7: Final RepeatMasker annotation ────────────────────────────────
    REPEAT_MASK_FINAL(
        PREPARE_GENOME.out.genome,
        strained_lib_ch,
        initial_lib
    )

    // ── Step 7.5 (optional): HELIANO Helitron detection ──────────────────────
    if (params.heliano) {
        HELIANO(PREPARE_GENOME.out.genome)
        heliano_gff_ch = HELIANO.out.gff
    } else {
        heliano_gff_ch = PREPARE_GENOME.out.genome
            .map { m, _genome -> [ m, file("${projectDir}/assets/NO_FILE") ] }
    }

    // ── Step 8: Defragment repeat annotations ────────────────────────────────
    MERGE_REPEATS(
        PREPARE_GENOME.out.genome,
        REPEAT_MASK_FINAL.out.repeat_out,
        REPEAT_MASK_FINAL.out.repeat_tbl,
        PREPARE_GENOME.out.dict,
        heliano_gff_ch
    )

    // ── Step 9 (optional): Divergence estimates ───────────────────────────────
    if (!params.skip_divergence) {
        CALCULATE_DIVERGENCE(
            PREPARE_GENOME.out.genome,
            MERGE_REPEATS.out.gff,
            REPEAT_MASK_FINAL.out.library
        )
        summary_gff_ch = CALCULATE_DIVERGENCE.out.gff
    } else {
        summary_gff_ch = MERGE_REPEATS.out.gff
    }

    // ── Step 10: Summary pie chart and count tables ───────────────────────────
    GENERATE_SUMMARY(
        MERGE_REPEATS.out.summary,
        summary_gff_ch,
        REPEAT_MASK_FINAL.out.repeat_tbl
    )

    // ── Step 11 (optional): Soft-mask genome ─────────────────────────────────
    if (params.soft_mask) {
        SOFT_MASK(
            PREPARE_GENOME.out.original,
            MERGE_REPEATS.out.bed
        )
    }
}

// ============================================================================
// Completion handlers
// ============================================================================

workflow.onComplete {
    log.info """
    =============================================================================
    Pipeline complete
    =============================================================================
    Status       : ${workflow.success ? 'SUCCESS' : 'FAILED'}
    Completed at : ${workflow.complete}
    Duration     : ${workflow.duration}
    Work dir     : ${workflow.workDir}
    Results      : ${params.outdir}
    =============================================================================
    """.stripIndent()
}

workflow.onError {
    log.error """
    =============================================================================
    Pipeline failed
    =============================================================================
    Error   : ${workflow.errorMessage}
    Work dir: ${workflow.workDir}
    =============================================================================
    """.stripIndent()
}

