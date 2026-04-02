// modules/build_database/main.nf
//
// Builds a RepeatModeler/BLAST database from the (optionally pre-masked) genome
// using BuildDatabase from the RepeatModeler package.
//
// Mirrors buildDB() in the legacy earlGrey bash script.

process BUILD_DATABASE {

    tag "${meta.id}"
    label 'process_low'

    // container 'docker://dfam/tetools:latest'

    input:
    tuple val(meta), path(genome)

    output:
    tuple val(meta), path("db/"), emit: db

    shell:
    '''
    set -euo pipefail

    mkdir -p db
    cd db

    BuildDatabase -name "!{meta.id}" "../!{genome}"

    # Verify at least one index file was created
    if ! ls "!{meta.id}".* 1>/dev/null 2>&1; then
        echo "ERROR: BuildDatabase produced no output files" >&2
        exit 1
    fi
    '''
}
