// modules/repeat_mask_final/main.nf
//
// Definitive RepeatMasker annotation using the species-specific library built
// by TEstrainer (and optionally combined with the initial Dfam/custom library
// from REPEAT_MASK_INITIAL).
//
// When an initial library was provided (assets/NO_FILE sentinel is absent),
// the two libraries are concatenated before masking.
//
// Mirrors novoMask() in the legacy earlGrey bash script.
//
// Optional-input sentinel: pass file("$projectDir/assets/NO_FILE") for
// initial_lib when no initial masking step was performed.

process REPEAT_MASK_FINAL {

    tag "${meta.id}"
    label 'process_high'

    // container 'docker://dfam/tetools:latest'

    input:
    tuple val(meta), path(genome)
    tuple val(meta), path(strained_lib)
    path(initial_lib)   // assets/NO_FILE when no initial masking was done

    output:
    tuple val(meta), path("*.masked"),  emit: masked
    tuple val(meta), path("*.out"),     emit: repeat_out
    tuple val(meta), path("*.tbl"),     emit: repeat_tbl
    tuple val(meta), path("final.lib"), emit: library

    shell:
    '''
    set -euo pipefail

    RM_PA=$(( !{task.cpus} / 4 ))
    [ "${RM_PA}" -lt 1 ] && RM_PA=1

    # ── Assemble final library ────────────────────────────────────────────────
    if [ "$(basename !{initial_lib})" != "NO_FILE" ]; then
        cat "!{strained_lib}" "!{initial_lib}" > final.lib
    else
        cp "!{strained_lib}" final.lib
    fi

    # ── Run RepeatMasker with combined library ────────────────────────────────
    RepeatMasker \
        -lib final.lib \
        -no_is -lcambig -s -a \
        -pa ${RM_PA} \
        -dir . \
        "!{genome}"

    # ── Verify output ─────────────────────────────────────────────────────────
    if ! ls ./*.tbl 1>/dev/null 2>&1; then
        echo "ERROR: RepeatMasker (final pass) produced no .tbl output" >&2
        exit 1
    fi
    '''
}
