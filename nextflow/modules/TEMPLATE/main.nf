// modules/TEMPLATE/main.nf
//
// Template for creating new processes in the EarlGrey Nextflow pipeline.
// Copy this file to a new module directory and customize for your process.
//
// Usage:
//   cp modules/TEMPLATE/main.nf modules/my_new_tool/main.nf
//   # Edit ...
//   include { MY_NEW_PROCESS } from './modules/my_new_tool/main.nf'

nextflow.enable.dsl = 2

// ============================================================================
// Process definition (following nf-core conventions)
// ============================================================================

process MY_NEW_PROCESS {
    /*
    Brief description of what this process does.

    External tools used: list any external tools/commands invoked
    Inputs: describe what the process expects
    Outputs: describe what the process produces
    */

    tag "${meta.id}"  // Tag for log display (usually species/sample ID)
    label 'process_single'  // Resource label (see nextflow.config for definitions)

    // Container specification (uncomment and customize when image is ready)
    // container 'nf-core/earlgrey:VERSION'
    // Alternative: use Singularity image
    // singularity: 'docker://nf-core/earlgrey:VERSION'
    // Conda: conda 'bioconda::tool=1.0'

    // ========================================================================
    // Input: structured tuples with metadata following nf-core pattern
    // ========================================================================
    input:
    tuple val(meta), path(input_file)  // meta = map with id, species, etc.

    // Add additional parameters as needed:
    // val(threads)
    // val(params_string)

    // ========================================================================
    // Output: all files → work dir, emit specific paths for downstream use
    // ========================================================================
    output:
    tuple val(meta), path('output.txt'), emit: result
    // Add additional outputs as needed:
    // tuple val(meta), path('*.log'),     emit: logs
    // tuple val(meta), path('*.stats'),   emit: stats

    // ========================================================================
    // Metrics and logging (captured by Nextflow trace)
    // ========================================================================
    // Metrics automatically collected: cpus, memory, time, status, exit_code
    // Additional metrics can be emitted via JSON:
    // publishDir "${params.outdir}/${meta.id}/metrics", mode: 'copy', pattern: '*.json'

    // ========================================================================
    // Error handling
    // ========================================================================
    // errorStrategy = { task.exitStatus in ((130..145) + 104) ? 'retry' : 'finish' }
    // maxRetries = 2

    shell:
    '''
    #!/bin/bash
    set -euo pipefail

    # Start logging
    echo "Starting MY_NEW_PROCESS on !{meta.id}"
    echo "Input file: !{input_file}"
    echo "CPUs available: ${task.cpus}"
    echo "Memory available: ${task.memory}"

    # Run external tool
    # Example: my_tool --input input_file --output output.txt --threads ${task.cpus}

    # Or invoke Python/Rust code:
    python3 << 'PYTHON_EOF'
    import sys
    print(f"Processing {sys.argv[1]}")
    # ... your Python logic here
    PYTHON_EOF

    # Or Bash commands:
    # gunzip -c input_file > decompressed.txt
    # process_cmd --input decompressed.txt --output output.txt

    echo "MY_NEW_PROCESS completed for !{meta.id}"
    '''
}

// ============================================================================
// Workflow-level wrapper (optional, for re-use in sub-workflows)
// ============================================================================

workflow MY_NEW_PROCESS_WF {
    /*
    Wrapper allowing this process to be used inside other workflows.
    Not always necessary, but useful for complex multi-step operations.

    Usage:
      include { MY_NEW_PROCESS_WF } from './modules/my_tool/main.nf'
      result = MY_NEW_PROCESS_WF(input_ch)
    */

    take:
    input_ch  // Channel with (meta, input_file) tuples

    main:
    // Apply process
    MY_NEW_PROCESS(input_ch)

    // Optional: post-processing or aggregation
    // result = MY_NEW_PROCESS.out.result.collectFile(...)

    emit:
    result = MY_NEW_PROCESS.out.result
}

// ============================================================================
// Best Practices Checklist
// ============================================================================
//
// ✅ Process naming: Use UPPERCASE with underscores (MY_NEW_PROCESS)
// ✅ Input/output: Use meta tuple pattern for structured metadata
// ✅ Labels: Assign a label for resource configuration (process_single, process_high, etc.)
// ✅ Container: Specify singularity/docker/conda image (comment out until ready)
// ✅ Tagging: Use ${meta.id} for task identification in logs
// ✅ Error handling: Define errorStrategy and maxRetries as appropriate
// ✅ Shell script: Use set -euo pipefail for robustness
// ✅ Logging: Print informative messages for debugging
// ✅ Documentation: Comment inputs/outputs and key logic
// ✅ Testing: Create a test workflow to validate before integration
//
// ============================================================================
// Testing Template
// ============================================================================
//
// To test this module standalone:
//
//   nextflow run -resume modules/my_new_tool/main.nf \
//     --input test_input.fa \
//     --species "test_species" \
//     -profile dev \
//     --outdir test_output
//
// Or create a minimal test workflow in tests/nf/test_my_tool.nf:
//
//   workflow test_my_tool {
//       input_ch = channel.fromPath('tests/data/input.fa').map { file ->
//           [[ id: 'test', species: 'Homo_sapiens' ], file]
//       }
//       MY_NEW_PROCESS(input_ch)
//       MY_NEW_PROCESS.out.result.view { meta, file ->
//           "Result: $file"
//       }
//   }
//
// Run: nextflow run tests/nf/test_my_tool.nf -profile dev
//
// ============================================================================
