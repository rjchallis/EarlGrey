nextflow.enable.dsl=2

process PREPARE {
    output:
    path 'prepared'
    script:
    """
    mkdir -p prepared
    echo 'prepared' > prepared/info.txt
    """
}

def prepare() {
    PREPARE()
}
