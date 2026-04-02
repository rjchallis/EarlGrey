// modules/de_novo_repeat/main.nf
//
// Runs RepeatModeler2 de-novo TE discovery against the pre-built database.
// Falls back to smaller genome-sample sizes if RepeatModeler fails on the
// first attempt (matching the retry logic in deNovo1() of the legacy script).
//
// Mirrors deNovo1() in the legacy earlGrey bash script.

process DE_NOVO_REPEAT {

    tag "${meta.id}"
    label 'process_high'

    // container 'docker://dfam/tetools:latest'

    input:
    tuple val(meta), path(db_dir)

    output:
    tuple val(meta), path("${meta.id}-families.fa"), emit: families

    shell:
    '''
    set -euo pipefail

    DB_PREFIX="$(realpath !{db_dir})/!{meta.id}"

    # ── Attempt 1: standard run ───────────────────────────────────────────────
    RepeatModeler -threads !{task.cpus} -database "${DB_PREFIX}" || true

    # ── Attempt 2: cap genome sample at Round-5 size ─────────────────────────
    if [ ! -f "${DB_PREFIX}-families.fa" ]; then
        echo "RepeatModeler attempt 1 failed – retrying with genomeSampleSizeMax 81000000" >&2
        RepeatModeler \
            -threads !{task.cpus} \
            -database "${DB_PREFIX}" \
            -genomeSampleSizeMax 81000000 || true
    fi

    # ── Attempt 3: cap genome sample at Round-4 size ─────────────────────────
    if [ ! -f "${DB_PREFIX}-families.fa" ]; then
        echo "RepeatModeler attempt 2 failed – retrying with genomeSampleSizeMax 27000000" >&2
        RepeatModeler \
            -threads !{task.cpus} \
            -database "${DB_PREFIX}" \
            -genomeSampleSizeMax 27000000 || true
    fi

    if [ ! -f "${DB_PREFIX}-families.fa" ]; then
        echo "ERROR: RepeatModeler failed after all attempts" >&2
        exit 1
    fi

    # Stage the families file into the work directory with the expected name
    cp "${DB_PREFIX}-families.fa" "!{meta.id}-families.fa"
    '''
}
