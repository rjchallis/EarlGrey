// modules/generate_summary/main.nf
//
// Produces the final summary outputs:
//   - Pie-chart PDF of repeat content by class (via autoPie.R)
//   - High-level repeat count table
//
// autoPie.sh has a hardcoded SCRIPT_DIR which is patched via sed.
// The genome size is extracted from RepeatMasker's .tbl file (line 4).
//
// Mirrors charts() in the legacy earlGrey bash script.

process GENERATE_SUMMARY {

    tag "${meta.id}"
    label 'process_low'

    publishDir "${params.outdir}/${meta.id}_summaryFiles", mode: 'copy'

    // container 'docker://dfam/tetools:latest'

    input:
    tuple val(meta), path(merged_summary)   // filteredRepeats.summary from MERGE_REPEATS
    tuple val(meta), path(merged_gff)       // filteredRepeats.gff from MERGE_REPEATS or CALCULATE_DIVERGENCE
    tuple val(meta), path(repeat_tbl)       // *.tbl from REPEAT_MASK_FINAL

    output:
    tuple val(meta), path("${meta.id}.summaryPie.pdf"),      emit: pie_chart
    tuple val(meta), path("${meta.id}.highLevelCount.txt"),  emit: count_table

    shell:
    '''
    set -euo pipefail

    SCRIPT_DIR="!{params.script_dir}"

    # ── Extract genome size from RepeatMasker table (line 4) ─────────────────
    GENOME_SIZE=$(sed -n '4p' "!{repeat_tbl}" \
        | rev | cut -f1 -d ':' | rev \
        | sed 's/ bp.*//g; s/ //g')

    # ── Generate pie chart and summary table ─────────────────────────────────
    Rscript "${SCRIPT_DIR}/autoPie.R" \
        "!{merged_summary}" \
        "!{merged_gff}" \
        "${GENOME_SIZE}" \
        "!{meta.id}.summaryPie.pdf" \
        "!{meta.id}.highLevelCount.txt"
    '''
}
