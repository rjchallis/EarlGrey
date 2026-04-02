// modules/prepare_genome/main.nf
//
// Cleans and normalises the input genome FASTA:
//   - Strips sequence descriptions from headers (keep only the first word)
//   - Removes blank lines
//   - Remaps headers to short ctg_N identifiers (saves dict for back-mapping)
//   - Converts ambiguous IUPAC bases DVHBPE → N
//
// Mirrors the prepGenome() function in the legacy earlGrey bash script.

process PREPARE_GENOME {

    tag "${meta.id}"
    label 'process_low'

    // container 'docker://dfam/tetools:latest'

    input:
    tuple val(meta), path(genome)

    output:
    tuple val(meta), path("${meta.id}.prep.fa"),      emit: genome
    tuple val(meta), path("${meta.id}.dict"),         emit: dict
    tuple val(meta), path("${meta.id}.stripped.fa"),  emit: original

    shell:
    '''
    set -euo pipefail

    # ── 1. Strip header descriptions & blank lines ───────────────────────────
    sed '/>/ s/[[:space:]].*//g; /^$/d' !{genome} > "!{meta.id}.stripped.fa"

    # ── 2. Build header dictionary  original_name → ctg_N ───────────────────
    grep "^>" "!{meta.id}.stripped.fa" \
        | awk '{printf("%s\\tctg_%d\\n", substr($0,2), NR)}' \
        > "!{meta.id}.dict"

    # ── 3. Swap headers using the project faswap.py ──────────────────────────
    python3 "!{params.script_dir}/faswap.py" "!{meta.id}.dict" "!{meta.id}.stripped.fa" \
        > "!{meta.id}.prep.fa"

    # ── 4. Convert ambiguous IUPAC bases on sequence lines ───────────────────
    sed -i '/^>/! s/[DVHBPE]/N/g' "!{meta.id}.prep.fa"
    '''
}
