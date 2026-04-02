// modules/soft_mask/main.nf
//
// Soft-masks the genome at repeat coordinates produced by MERGE_REPEATS,
// producing an output FASTA where repeat regions are lower-cased.
//
// Both the bed (from MERGE_REPEATS) and the original genome (from
// PREPARE_GENOME emit: original) have been back-swapped to original contig
// names by the merge scripts, so bedtools maskfasta can match them directly.
//
// Mirrors Stage 8.5 in the legacy earlGrey bash script.

process SOFT_MASK {

    tag "${meta.id}"
    label 'process_low'

    // container 'docker://dfam/tetools:latest'

    input:
    tuple val(meta), path(original_genome)  // original-named genome from PREPARE_GENOME emit: original
    tuple val(meta), path(bed)              // filteredRepeats.bed from MERGE_REPEATS (original names)

    output:
    tuple val(meta), path("${meta.id}.softmasked.fasta"), emit: softmasked

    shell:
    '''
    set -euo pipefail

    bedtools maskfasta \
        -fi "!{original_genome}" \
        -bed "!{bed}" \
        -fo "!{meta.id}.softmasked.fasta" \
        -soft
    '''
}
