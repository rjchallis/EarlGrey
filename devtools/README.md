# devtools — Development utilities

This directory contains development-only helper scripts and utilities. Files here are not part of the main pipeline and are intended for interactive use by developers (e.g., baseline runs, quick tests, one-off helpers).

Current helper:

- `baseline_submit.py` — fetches an assembly (remote URL if needed) and submits a parameterised EarlGrey baseline job to an LSF cluster via SSH.

Prerequisites

- Python 3.8+ (local machine) with `PyYAML` installed (`pip install pyyaml`) to run `baseline_submit.py`.
- An SSH host alias configured in `~/.ssh/config` for the cluster login node (no credentials in `config/baseline_config.yaml`).
- The `earlGrey` command available on the remote cluster (e.g., a conda env named `earlgrey`). The job script tries to `conda activate earlgrey` on the remote side — customise if your site uses a different shell or activation method.

Quickstart

1. Copy and edit the example config into the devtools config location (do NOT commit your edited config):

```bash
cp config/baseline_config.yaml.example devtools/config/baseline_config.yaml
# edit devtools/config/baseline_config.yaml and set `ssh_host`, remote paths, etc.
```

2. Dry-run (prints planned actions and job script):

```bash
./devtools/baseline_submit.py --config config/baseline_config.yaml --id yeast_R64 --dry-run
```

3. Submit the job:

```bash
./devtools/baseline_submit.py --config config/baseline_config.yaml --id yeast_R64
```

## Makefile usage

A lightweight Makefile wraps the helper scripts for convenience. Use the Makefile from the repository root with `-C devtools` to run targets in the `devtools/` folder.

**Available Makefile targets:**

- `help` — show all targets and variables
- `dry-run` — preview baseline job (prints config and job script without submitting)
- `submit` — submit baseline job to remote cluster
- `chmod` — make scripts executable (one-off)
- `nextflow-dry-run` — preview Nextflow runner job
- `nextflow-submit` — submit Nextflow runner job
- `extract-chr1` — extract first sequence locally from a remote URL
- `extract-chr1-remote` — extract first sequence **on the remote cluster** (recommended)
- `collect-metrics` — compare metrics from baseline and current run

## Metrics collection and profiling

### Overview

Each baseline run automatically collects detailed performance metrics using `/usr/bin/time -v`. These metrics are captured to `earlgrey_metrics.txt` in the output directory and can be compared between runs to identify performance improvements or regressions.

**Captured metrics include:**

- Wallclock time (elapsed)
- User and system CPU time
- Peak resident set size (memory)
- CPU utilization percentage
- Major and minor page faults
- File system I/O operations

### Workflow

1. **Run baseline:** Submit a job normally with `make submit ID=yeast_R64 OUT_DIR=my_run_001`
2. **Wait for completion:** Monitor via `ssh` or check `bjobs` on farm
3. **Collect metrics:** `make collect-metrics BASELINE_RUN=<baseline_dir> CURRENT_RUN=<current_dir>`

### Example: Compare two runs

```bash
# Initial baseline run (already completed)
baseline_dir=/path/to/remote/work/yeast_R64

# New run to compare
make submit ID=yeast_R64 OUT_DIR=yeast_R64_baseline_iter_001

# Wait for job to finish, then collect metrics
make collect-metrics \
  BASELINE_RUN=$baseline_dir \
  CURRENT_RUN=/path/to/remote/work/yeast_R64_baseline_iter_001
```

This produces a comparison table and saves detailed metrics to `metrics_comparison.json`.

### Instrumented wrapper (optional)

An alternative instrumented wrapper script (`earlgrey_instrumented.py`) is available for local runs with richer per-step metrics collection (parsing earlGrey logs for per-component timing). It is not currently integrated into the remote job submission flow but can be used for local testing:

```bash
python3 devtools/earlgrey_instrumented.py -g <genome.fna> -s <species> -o <output> --metrics-file metrics.json
```

**Makefile variables:**

| Variable  | Default                       | Purpose                                                   |
| --------- | ----------------------------- | --------------------------------------------------------- |
| `ID`      | `yeast_R64`                   | Assembly id from config (must exist in `assemblies` list) |
| `OUT_DIR` | (empty)                       | Override output directory (useful for multiple test runs) |
| `CONFIG`  | `config/baseline_config.yaml` | Config file path                                          |
| `PY`      | `python3`                     | Python executable                                         |
| `URL`     | (required for `extract-chr1`) | Remote FASTA URL to download                              |
| `OUTPUT`  | (required for `extract-chr1`) | Local output filename                                     |

**Basic usage:**

```bash
# Show all targets and variables
make -C devtools help

# Dry-run baseline on yeast_R64
make -C devtools dry-run ID=yeast_R64

# Submit baseline on yeast
make -C devtools submit ID=yeast_R64

# Dry-run with a custom output directory
make -C devtools dry-run ID=yeast_R64_chr1 OUT_DIR=yeast_R64_chr1_test_run_001

# Submit with custom output directory (keeps output separate from subsequent runs)
make -C devtools submit ID=yeast_R64_chr1 OUT_DIR=yeast_R64_chr1_test_run_001
```

**Multiple test runs** (without overwriting previous results):

```bash
# Run 1
make -C devtools submit ID=yeast_R64_chr1 OUT_DIR=yeast_R64_chr1_iter_001

# Run 2 (output goes to a different directory)
make -C devtools submit ID=yeast_R64_chr1 OUT_DIR=yeast_R64_chr1_iter_002

# Run 3
make -C devtools submit ID=yeast_R64_chr1 OUT_DIR=yeast_R64_chr1_iter_003
```

The Makefile is a thin wrapper — the heavy logic remains in the helper scripts.

Notes and tips

- If you already have the assembly locally and prefer to upload it directly, use `rsync` to copy it to the remote data directory before running the submit script:

```bash
rsync -avP ./GCF_000146045.2_R64_genomic.fna.gz mycluster:/scratch/team301/data/yeast_R64/
```

- The script fetches the assembly on the remote host if it is not present; this avoids transferring large files from your laptop.
- To change resource requests (cores/memory/queue) edit `config/baseline_config.yaml` or pass overrides to the script (`--threads`, `--mem`).
- Make the script executable if needed:

```bash
chmod +x devtools/baseline_submit.py
```

Nextflow helper

- `nextflow_submit.py` — builds and submits a small LSF job script that runs Nextflow on the remote cluster. This is intentionally separate from the baseline submit: it does not run `earlGrey` itself unless your Nextflow pipeline (`nextflow/main.nf`) invokes it.

Makefile targets added:

- `nextflow-dry-run`: preview the Nextflow job script without submitting.
- `nextflow-submit`: upload and submit the Nextflow job (uses `--debug-remote` by default via the Makefile target).

Examples:

```bash
# Dry-run the nextflow wrapper
make -C devtools nextflow-dry-run ID=yeast_R64

# Submit the nextflow wrapper (remote submit with debug tracing)
make -C devtools nextflow-submit ID=yeast_R64
```

Testing helper: extract first chromosome

- `extract_chr1.py` — extracts the first sequence from a FASTA file (local or remote URL) and saves locally for fast iteration.
- `--extract-chr1-from ID` (option in `baseline_submit.py`) — extracts the first chromosome **on the remote cluster** to avoid large file transfers. Prints a ready-to-use config entry for the chr1 variant.

Remote extraction (recommended):

```bash
# Extract chr1 from yeast_R64 on the remote cluster
make -C devtools extract-chr1-remote ID=yeast_R64

# Or use directly:
./devtools/baseline_submit.py --config config/baseline_config.yaml --extract-chr1-from yeast_R64
```

The command will output:

```
✓ Chr1 extraction complete!

Add this entry to your devtools/config/baseline_config.yaml under 'assemblies':

  - id: yeast_R64_chr1
    filename: yeast_R64_chr1.fna.gz
    species: yeast_R64
    threads: 4

Remote path: /lustre/.../yeast_R64_chr1.fna.gz
```

Then submit a quick baseline run on just chr1:

```bash
# First test run with default output dir
make -C devtools dry-run ID=yeast_R64_chr1
make -C devtools submit ID=yeast_R64_chr1

# Or multiple test runs with unique output directories (no overwrites):
make -C devtools submit ID=yeast_R64_chr1 OUT_DIR=yeast_R64_chr1_test_001
make -C devtools submit ID=yeast_R64_chr1 OUT_DIR=yeast_R64_chr1_test_002
```

This gives you fast iteration on a small (~230 kb) test genome before running full genome analysis (12 Mb).

Local extraction (for local testing):

```bash
# Extract from remote URL and save locally (gzip-compressed by default for .gz output)
make -C devtools extract-chr1 URL=https://ftp.ncbi.nlm.nih.gov/.../GCF_000146045.2_R64_genomic.fna.gz OUTPUT=yeast_R64_chr1.fna.gz

# Or use the script directly
./devtools/extract_chr1.py --url <URL> --output yeast_R64_chr1.fna.gz
```

Security

- Do not store passwords or private keys in `config/baseline_config.yaml`. Use an SSH alias (via `~/.ssh/config`) or SSH agent forwarding.
- Keep `config/baseline_config.yaml` local/private; only the example file is intended to be committed.

Extending devtools

- Add other experimental helper scripts here. Keep dev-only utilities out of `scripts/` which is reserved for pipeline-facing helpers.

Questions or follow-ups

- Want me to add a short CI-excluded check that ensures `devtools/` files are not run in CI? Or add a small `devtools/Makefile` with helper targets? Let me know which you prefer.
