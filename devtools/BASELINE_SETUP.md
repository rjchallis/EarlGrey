# Baseline Configuration Guide

## Overview

This guide explains how to run EarlGrey baselines on multiple genome sizes using the Nextflow pipeline with configurable features like soft masking.

## Key Changes

### Smart Fetch Behavior (Fixed)

Previously, you had to manually set `skip_fetch: true` or change the config between runs. **Now:**

- The system **always checks** if a file exists on the remote side first
- If it exists and is valid (>1000 bytes), it reuses it
- Only fetches from the URL if the file doesn't exist or is corrupted
- You can leave URLs in the config permanently and run multiple times without changes

**No configuration changes needed between first and subsequent runs.**

### Optional Features

The pipeline now supports feature flags in the config:

```yaml
soft_mask: true # Generate soft-masked genome (lowercase repeats)
heliano: true # Run HELIANO Helitron detector (requires 'heliano' in PATH)
```

These are passed automatically to the Nextflow pipeline when submitted.

## Running Baselines

### Nextflow Pipeline (Recommended for New Features)

Use `nextflow_submit.py` to submit the Nextflow DSL2 pipeline:

```bash
# Dry run (preview what will happen)
make nextflow-dry-run ID=yeast_R64

# Submit the job
make nextflow-submit ID=yeast_R64

# Submit with overrides
./devtools/nextflow_submit.py --config config/baseline_config.yaml --id yeast_R64 --threads 32
```

The Nextflow pipeline supports:

- ✅ soft_mask (soft-masked genome in final outputs)
- ✅ heliano (Helitron detection with optional merging)
- ✅ Divergence calculation
- ✅ Custom library clustering
- ✅ Initial masking (repeat_species or custom_lib)

### Legacy EarlGrey (Old Bash Script)

Use `baseline_submit.py` for the original bash-based earlGrey:

```bash
./devtools/baseline_submit.py --config config/baseline_config.yaml --id yeast_R64
```

Note: This uses the legacy script and does **not** support the new Nextflow features.

## Configuration

Edit `config/baseline_config.yaml`:

### Assembly Entry Template

```yaml
- id: example_genome
  # NCBI URL for direct download (can be commented if file is pre-loaded on cluster)
  # url: https://ftp.ncbi.nlm.nih.gov/genomes/...
  filename: GCF_example_genomic.fna.gz
  species: Example_species
  out_dir: example_genome
  threads: 16 # Nextflow worker threads
  repeat_term: eukarya # RepeatMasker taxon for initial masking (optional)
  soft_mask: true # (Nextflow only) Generate soft-masked genome
  heliano: false # (Nextflow only) Run HELIANO detector
```

### Current Assemblies

1. **yeast_R64** (12 MB, ~5-10 min baseline)
   - Full _Saccharomyces cerevisiae_ R64
   - Already exists on cluster; URL commented but fetch will be skipped
   - **soft_mask: true** for testing masking output

2. **yeast_R64_chr1** (200 kb, <1 min baseline)
   - Extracted chromosome 1 for quick testing
   - Extract using:
     ```bash
     ./devtools/baseline_submit.py --extract-chr1-from yeast_R64
     ```

3. **thaliana_col_cvi** (~125 MB, 1-2h estimate)
   - Placeholder entry; fill in URL with actual NCBI accession
   - soft_mask enabled

4. **danio_rerio** (~1.4 GB, 4-8h estimate)
   - Placeholder entry; fill in URL with actual NCBI accession
   - soft_mask enabled

## Workflow

### First Run of a New Genome

1. **Find the genome accession** on NCBI and add to config:

   ```yaml
   - id: my_genome
     url: https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/.../GCF_*_genomic.fna.gz
     filename: GCF_*_genomic.fna.gz
     species: My_species
     out_dir: my_genome
     threads: 16
     soft_mask: true
   ```

2. **Submit the job:**

   ```bash
   make nextflow-submit ID=my_genome
   ```

   On first run:
   - File is fetched to the remote cluster if not already present
   - Decompressed automatically (.fna.gz → .fna)
   - Pipeline runs end-to-end

### Subsequent Runs (Resume/Retry)

3. **Resubmit without any config changes:**

   ```bash
   make nextflow-submit ID=my_genome
   ```

   On retry:
   - Existing files are automatically detected and reused
   - `-resume` flag is added automatically to reuse cached steps
   - No need to edit the config or set skip_fetch

### Resource Scaling Guidance

The config includes threading for worker jobs (`threads: 16`). For larger genomes:

| Genome Size        | Threads | Estimate  | Notes                                  |
| ------------------ | ------- | --------- | -------------------------------------- |
| <50 MB (yeast)     | 16      | 5-10 min  | Quick baseline                         |
| ~125 MB (thaliana) | 16-32   | 1-2 hours | CLASSIFY_REPEATS may dominate          |
| ~1 GB (danio)      | 32-64   | 4-8 hours | Parallelize RepeatModeler & clustering |

Increase `threads` for larger genomes; the platform scales proportionally.

## Troubleshooting

### File fetch fails on first run

- Check the URL is correct and accessible
- Check network access from the remote cluster
- Try manually cuddling the file to the remote data directory:
  ```bash
  scp genome.fna.gz farm:/lustre/scratch.../earlgrey/data/my_genome/
  ```

### Pipeline hangs or fails

- Check Nextflow logs on the remote:
  ```bash
  ssh farm "tail -f /lustre/scratch.../earlgrey/work/my_genome_nextflow/.nextflow.log"
  ```
- Use `--debug-remote` flag for verbose output:
  ```bash
  make nextflow-dry-run ID=my_genome
  make nextflow-submit ID=my_genome NF_PROFILES=hpc DEBUG=--debug-remote
  ```

### OOM (Out of Memory) on CLASSIFY_REPEATS

- This step is memory-hungry for large genomes
- The config auto-scales based on `task.attempt`
- If retries still fail, the driver job might need more memory:
  ```bash
  make nextflow-submit ID=my_genome MEM=32000
  ```

## References

- [Nextflow documentation](https://www.nextflow.io/)
- [EarlGrey Nextflow pipeline](../nextflow/main.nf)
- [AGENTS.md](../AGENTS.md) for session logging conventions
