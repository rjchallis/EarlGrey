// modules/calculate_divergence/main.nf
//
// Computes Kimura-80 divergence estimates for each annotated TE copy using
// divergence_calc.py, then generates repeat-landscape plots with
// divergence_plot.R.  Attribute keys in the output GFF are normalised to
// lower-case to match downstream tools.
//
// Mirrors calcDivRL() in the legacy earlGrey bash script.

process CALCULATE_DIVERGENCE {

    tag "${meta.id}"
    label 'process_medium'

    // container 'docker://dfam/tetools:latest'

    input:
    tuple val(meta), path(genome)      // original (pre-prep) genome, or prep genome
    tuple val(meta), path(gff)         // filteredRepeats.gff from MERGE_REPEATS
    tuple val(meta), path(library)     // final TE consensus library

    output:
    tuple val(meta), path("${meta.id}.filteredRepeats.withDivergence.gff"), emit: gff
    tuple val(meta), path("*_summary_table.tsv"),                           emit: summary
    tuple val(meta), path("*.pdf"),                                         emit: plots

    shell:
    '''
    set -euo pipefail

    SCRIPT_DIR="!{params.script_dir}"

    # Python multiprocessing forkserver creates a Unix socket under TMPDIR.
    # Nextflow sets TMPDIR to the work dir (100+ chars), exceeding the 108-char
    # AF_UNIX path limit on Linux.  Reset to /tmp before spawning the pool.
    export TMPDIR=/tmp

    # ── Compute Kimura divergence ─────────────────────────────────────────────
    python3 "${SCRIPT_DIR}/divergenceCalc/divergence_calc.py" \
        -l "!{library}" \
        -g "!{genome}" \
        -i "!{gff}" \
        -o "!{meta.id}.filteredRepeats.withDivergence.gff" \
        -t !{task.cpus}

    # ── Plot repeat landscape ─────────────────────────────────────────────────
    Rscript "${SCRIPT_DIR}/divergenceCalc/divergence_plot.R" \
        -s "!{meta.species}" \
        -g "!{meta.id}.filteredRepeats.withDivergence.gff" \
        -o .

    # ── Normalise GFF attribute case (legacy compatibility) ───────────────────
    awk -F'\\t' 'BEGIN{OFS="\\t"} {
        gsub("NAME=",    "Name=",    $9)
        gsub("TSTART=",  "tstart=",  $9)
        gsub("TEND=",    "tend=",    $9)
        gsub("SHORTTE=", "shortte=", $9)
        gsub("TEGROUP=", "tegroup=", $9)
        gsub("KIMURA80=","kimura80=", $9)
        gsub("NESTED=",  "nested=",  $9)
        print
    }' "!{meta.id}.filteredRepeats.withDivergence.gff" \
        > "!{meta.id}.filteredRepeats.withDivergence.gff.1" \
    && mv "!{meta.id}.filteredRepeats.withDivergence.gff"{.1,}

    # Clean up temporary alignment files
    rm -rf tmp/
    '''
}
