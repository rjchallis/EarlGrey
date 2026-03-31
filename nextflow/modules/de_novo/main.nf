nextflow.enable.dsl=2

process DENOVO {
    output:
    path 'de_novo'
    script:
    """
    mkdir -p de_novo
    echo 'de novo' > de_novo/info.txt
    """
}

def deNovo() {
    DENOVO()
}
