// modules/classify_repeats/main.nf
//
// Runs TEstrainer (BLAST / Extract / Align / Trim) to refine de-novo consensus
// sequences and classify them against Dfam / structural annotations.
//
// TEstrainer_for_earlGrey.sh has a hardcoded STRAIN_SCRIPTS path.  This module
// patches that variable via sed so the script works from any installation root
// pointed to by params.script_dir.
//
// Mirrors strainer() in the legacy earlGrey bash script.

process CLASSIFY_REPEATS {

    tag "${meta.id}"
    label 'process_high'

    // container 'docker://dfam/tetools:latest'

    input:
    tuple val(meta), path(families)
    tuple val(meta), path(genome)

    output:
    tuple val(meta), path("${meta.id}-families.fa.strained"), emit: library

    shell:
    '''
    set -euo pipefail

    # TEstrainer mafft parallelism is 1/4 of total threads
    strain_threads=$(( !{task.cpus} / 4 ))
    [ "${strain_threads}" -lt 1 ] && strain_threads=1

    SCRIPT_DIR="!{params.script_dir}"

    # ── Patch the hardcoded STRAIN_SCRIPTS path ───────────────────────────────
    sed "s|STRAIN_SCRIPTS=.*|STRAIN_SCRIPTS=${SCRIPT_DIR}/TEstrainer/scripts/|" \
        "${SCRIPT_DIR}/TEstrainer/TEstrainer_for_earlGrey.sh" \
        > ./TEstrainer_run.sh
    chmod +x ./TEstrainer_run.sh

    # ── Run TEstrainer ────────────────────────────────────────────────────────
    ./TEstrainer_run.sh \
        -g  "!{genome}" \
        -l  "!{families}" \
        -t  ${strain_threads} \
        -f  !{params.flank_bases} \
        -r  !{params.blast_iterations} \
        -n  !{params.max_sequences} \
        -m  !{params.min_sequences} \
        -d  testrainer_out

    # ── Locate the strained output ────────────────────────────────────────────
    STRAINED="testrainer_out/$(basename !{families}).strained"
    if [ ! -s "${STRAINED}" ]; then
        echo "WARNING: TEstrainer produced an empty strained file; using original families" >&2
        cp "!{families}" "!{meta.id}-families.fa.strained"
    else
        cp "${STRAINED}" "!{meta.id}-families.fa.strained"
    fi
    '''
}
