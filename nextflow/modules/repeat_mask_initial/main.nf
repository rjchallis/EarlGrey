// modules/repeat_mask_initial/main.nf
//
// Optional first-pass RepeatMasker run using either:
//   a) a Dfam species/taxon query (-r flag in earlGrey)
//   b) a user-supplied consensus library FASTA (-l flag in earlGrey)
//
// Also extracts the Dfam library subset as a FASTA so it can be merged with
// the de-novo library in REPEAT_MASK_FINAL.
//
// Mirrors getRepeatMaskerFasta() + firstMask() / firstMaskCustomLib() in the
// legacy earlGrey bash script.
//
// Optional-input sentinel: pass file("$projectDir/assets/NO_FILE") for
// custom_lib when running in Dfam-species mode.

process REPEAT_MASK_INITIAL {

    tag "${meta.id}"
    label 'process_high'

    // container 'docker://dfam/tetools:latest'

    input:
    tuple val(meta), path(genome)
    val(repeat_species)   // RepeatMasker species/taxon string, or '' for custom-lib mode
    path(custom_lib)      // User library FASTA, or assets/NO_FILE when using repeat_species

    output:
    tuple val(meta), path("*.masked"),    emit: masked
    tuple val(meta), path("initial.lib"), emit: library

    shell:
    '''
    set -euo pipefail

    RM_PA=$(( !{task.cpus} / 4 ))
    [ "${RM_PA}" -lt 1 ] && RM_PA=1
    GENOME_BASENAME=$(basename "!{genome}")

    if [ -n "!{repeat_species}" ]; then
        # ── Mode A: Dfam species/taxon query ─────────────────────────────────

        # Locate famdb directory (handles both conda and system installs)
        if [[ $(which RepeatMasker) == *"bin"* ]]; then
            LIBPATH="$(which RepeatMasker | sed 's|bin/RepeatMasker|share/RepeatMasker/Libraries/famdb/|')"
        else
            LIBPATH="$(dirname $(which RepeatMasker))/Libraries/famdb/"
        fi

        # Extract Dfam subset as FASTA for combining later
        famdb.py -i "$LIBPATH" families \
            -f fasta_name --include-class-in-name -a -d --curated \
            "!{repeat_species}" > initial.lib

        # Run RepeatMasker using Dfam species index (full database search)
        RepeatMasker \
            -species "!{repeat_species}" \
            -no_is -lcambig -s -a \
            -pa ${RM_PA} \
            -dir . \
            "!{genome}"

    else
        # ── Mode B: user-supplied consensus library ───────────────────────────
        cp "!{custom_lib}" initial.lib

        RepeatMasker \
            -lib "!{custom_lib}" \
            -no_is -lcambig -s -a \
            -pa ${RM_PA} \
            -dir . \
            "!{genome}"
    fi

    # ── Verify output ─────────────────────────────────────────────────────────
    if ! ls ./*.masked 1>/dev/null 2>&1; then
        echo "ERROR: RepeatMasker produced no .masked output" >&2
        exit 1
    fi
    '''
}
