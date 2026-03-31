nextflow.enable.dsl=2

include { prepare } from './modules/prepare/main.nf'
include { deNovo } from './modules/de_novo/main.nf'

workflow {
    params.variant = params.variant ?: 'default'

    prepare()
    deNovo()
}
