// modules/merge_repeats/main.nf
//
// Defragments RepeatMasker annotations using rcMergeRepeatsLoose, with
// automatic fallback to the stricter rcMergeRepeats if the loose merge fails.
// Both scripts have a hardcoded SCRIPT_DIR that is patched via sed before use.
//
// Mirrors mergeRep() in the legacy earlGrey bash script.

process MERGE_REPEATS {

    tag "${meta.id}"
    label 'process_medium'

    // container 'docker://dfam/tetools:latest'

    input:
    tuple val(meta), path(genome)
    tuple val(meta), path(repeat_out)   // *.out from REPEAT_MASK_FINAL
    tuple val(meta), path(repeat_tbl)   // *.tbl from REPEAT_MASK_FINAL
    tuple val(meta), path(dict)         // header-swap dictionary from PREPARE_GENOME
    tuple val(meta), path(heliano_gff)  // HELIANO GFF (empty file or NO_FILE when not run)

    output:
    tuple val(meta), path("looseMerge/${meta.id}.filteredRepeats.gff"), emit: gff
    tuple val(meta), path("looseMerge/${meta.id}.filteredRepeats.bed"), emit: bed
    tuple val(meta), path("looseMerge/${meta.id}.filteredRepeats.summary"), emit: summary

    shell:
    '''
    set -euo pipefail

    SCRIPT_DIR="!{params.script_dir}"
    MARGIN="!{params.remove_short}"

    # Resolve all inputs to absolute paths before the merge scripts cd away
    WORKDIR="$(pwd)"
    GENOME="$(realpath "!{genome}")"
    REPEAT_OUT="$(realpath "!{repeat_out}")"
    REPEAT_TBL="$(realpath "!{repeat_tbl}")"
    DICT="$(realpath "!{dict}")"
    HELIANO_GFF="$(realpath "!{heliano_gff}")"
    LOOSE_DIR="${WORKDIR}/looseMerge"

    # Build optional -e flag for HELIANO GFF (only if the file is non-empty)
    HELI_FLAG=""
    if [ -s "${HELIANO_GFF}" ]; then HELI_FLAG="-e ${HELIANO_GFF}"; fi

    # ── Patch hardcoded SCRIPT_DIR in merge scripts ───────────────────────────
    for SCRIPT in rcMergeRepeatsLoose rcMergeRepeats; do
        sed "s|SCRIPT_DIR=.*|SCRIPT_DIR=${SCRIPT_DIR}|" \
            "${SCRIPT_DIR}/${SCRIPT}" > "./${SCRIPT}"
        chmod +x "./${SCRIPT}"
    done

    mkdir -p looseMerge

    # ── Attempt 1: loose merge ────────────────────────────────────────────────
    ./rcMergeRepeatsLoose \
        -f "${GENOME}" \
        -s "!{meta.id}" \
        -d "${LOOSE_DIR}" \
        -u "${REPEAT_OUT}" \
        -q "${REPEAT_TBL}" \
        -t !{task.cpus} \
        -b "${DICT}" \
        -m "${MARGIN}" \
        ${HELI_FLAG} || true

    # Fix GFF attribute capitalisation (match legacy behaviour)
    if [ -f "${LOOSE_DIR}/!{meta.id}.filteredRepeats.bed" ]; then
        awk '{OFS="\\t"}{print $1, $2, $3, $4, $5, $6, $7, $8, toupper($9)}' \
            "${LOOSE_DIR}/!{meta.id}.filteredRepeats.gff" \
            > "${LOOSE_DIR}/!{meta.id}.filteredRepeats.gff.1" \
            && mv "${LOOSE_DIR}/!{meta.id}.filteredRepeats.gff"{.1,}
    fi

    # ── Fallback: strict merge ────────────────────────────────────────────────
    if [ ! -f "${LOOSE_DIR}/!{meta.id}.filteredRepeats.bed" ]; then
        echo "Loose merge failed – attempting strict merge" >&2
        ./rcMergeRepeats \
            -f "${GENOME}" \
            -s "!{meta.id}" \
            -d "${WORKDIR}" \
            -u "${REPEAT_OUT}" \
            -q "${REPEAT_TBL}" \
            -t !{task.cpus} \
            -b "${DICT}" \
            -m "${MARGIN}" \
            ${HELI_FLAG} || true

        if [ ! -f "!{meta.id}.filteredRepeats.bed" ]; then
            echo "ERROR: both loose and strict merge failed" >&2
            exit 1
        fi

        # Move strict-merge outputs into looseMerge/ so downstream is uniform
        mv "!{meta.id}.filteredRepeats.bed"     looseMerge/
        mv "!{meta.id}.filteredRepeats.gff"     looseMerge/
        mv "!{meta.id}.filteredRepeats.summary" looseMerge/
    fi
    '''
}
