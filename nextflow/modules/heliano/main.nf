// modules/heliano/main.nf
//
// Runs HELIANO to detect RC/Helitron transposable elements, then converts the
// representative BED output to GFF2 format for use by MERGE_REPEATS.
//
// Mirrors heliano_optional() in the legacy earlGrey bash script.
// Output GFF is passed as an optional -e argument to rcMergeRepeatsLoose /
// rcMergeRepeats so that Helitron annotations replace overlapping RepeatMasker
// annotations in the merged output.

process HELIANO {

    tag "${meta.id}"
    label 'process_high'

    // container 'docker://dfam/tetools:latest'

    input:
    tuple val(meta), path(genome)

    output:
    tuple val(meta), path("${meta.id}.helitrons.gff"), emit: gff

    shell:
    '''
    set -euo pipefail

    GENOME="$(realpath "!{meta.id}.prep.fa")"

    # ── Run HELIANO ───────────────────────────────────────────────────────────
    # Run from a dedicated subdirectory so HELIANO output files don't collide
    mkdir -p heliano_out
    heliano \
        -g "!{genome}" \
        --nearest \
        -dn 6000 \
        -flank_sim 0.5 \
        -o heliano_out/HEL \
        -w 10000 \
        -n !{task.cpus}

    # ── Convert RC.representative.bed → GFF2 ─────────────────────────────────
    # Legacy awk: col 1=seqname, source=HELIANO, feature=RC/Helitron,
    # start=$2+1 (BED is 0-based), end=$3, score=$5, strand=$6, frame=.
    # attributes = ID={name}_{status};shortTE=F
    RC_BED="heliano_out/HEL/RC.representative.bed"

    if [ -s "${RC_BED}" ]; then
        awk '{OFS="\\t"}{print $1, "HELIANO", "RC/Helitron", $2+1, $3, $5, $6, ".", "ID="$9"_"$11";shortTE=F"}' \
            "${RC_BED}" > "!{meta.id}.helitrons.gff"
    else
        # Produce an empty GFF so the NO_FILE sentinel is not needed
        touch "!{meta.id}.helitrons.gff"
    fi
    '''
}
