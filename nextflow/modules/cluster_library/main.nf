// modules/cluster_library/main.nf
//
// Optional step: clusters the TE consensus library with cd-hit-est at the
// Wicker 80-80-80 rule thresholds to reduce redundancy before the final mask.
//
// Enabled by --cluster_library in the main workflow.
//
// Mirrors clust() in the legacy earlGrey bash script.

process CLUSTER_LIBRARY {

    tag "${meta.id}"
    label 'process_medium'

    // container 'docker://biocontainers/cd-hit:v4.8.1_cv2'

    input:
    tuple val(meta), path(library)

    output:
    tuple val(meta), path("${meta.id}.clustered.lib"), emit: library

    shell:
    '''
    set -euo pipefail

    cd-hit-est \
        -d 0 \
        -aS 0.8 \
        -c  0.8 \
        -G  0 \
        -g  1 \
        -b  500 \
        -r  1 \
        -T  !{task.cpus} \
        -i  "!{library}" \
        -o  "!{meta.id}.clustered.lib"
    '''
}
