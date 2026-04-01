#!/usr/bin/env nextflow

// Minimal Nextflow (DSL2) pipeline stub for EarlGrey
// Usage example:
// nextflow run ./nextflow/main.nf --genome /path/to/genome.fasta --outdir /path/to/out -profile hpc,singularity

params.genome = ''
params.species = ''
params.outdir = ''
params.threads = 4
params.memory = '16 GB'

process runEarlGrey {
    tag "${params.species}"
    cpus params.threads
    memory params.memory
    time '48h'

    script:
    """
    echo "Starting EarlGrey on ${params.genome}"
    earlGrey -g '${params.genome}' -s '${params.species}' -o '${params.outdir}' -t ${task.cpus}
    """
}

workflow {
    runEarlGrey()
}
nextflow.enable.dsl=2

include { prepare } from './modules/prepare/main.nf'
include { deNovo } from './modules/de_novo/main.nf'

workflow {
    params.variant = params.variant ?: 'default'

    prepare()
    deNovo()
}
