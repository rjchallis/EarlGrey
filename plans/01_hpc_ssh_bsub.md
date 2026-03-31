# 01 — HPC: SSH + bsub (LSF) execution setup

Purpose

- Enable local development with the ability to run and test pipeline steps on HPC via SSH and `bsub` (LSF).
- Provide repeatable Nextflow `hpc` profile and quick wrapper submission options for iterative testing.

Overview — recommended workflows

1. Deploy-and-run (recommended): push/rsync the repo to the HPC login node, SSH in, and run Nextflow on the cluster (Nextflow will submit jobs to LSF). This gives full pipeline behaviour and uses the cluster scheduler correctly.
2. Wrapper-submission (fast tests): run individual wrapper scripts for single processes and submit them with `bsub` for quicker iteration on specific stages.

Prerequisites on HPC

- Java (11+), Nextflow installed on the login node (or available via module).
- Singularity (or Shifter) installed for running containers on compute nodes — prefer Singularity for HPC.
- Git or a shared filesystem where code is available.
- Access to Docker registry or prebuilt SIF images in a central location (or push SIFs to a shared storage path).
- SSH key access from your dev machine to the HPC (passwordless if automation desired).

Security note

- Do not commit secrets or credentials into the repo. Use environment variables, CI secrets, or the HPC credential manager.

Detailed setup steps

A. SSH & deployment setup

1. Create an SSH key (if you don't have one) and install it on the HPC:

```bash
ssh-keygen -t ed25519 -C "you@example.com"
ssh-copy-id user@hpc.example.org
```

2. Use `rsync` or `git` to copy code to the HPC working directory (avoid copying the `work/` Nextflow folder):

```bash
rsync -av --exclude 'work/' --exclude '.nextflow/' ./ user@hpc:/home/user/earlGrey_dev/
# or
git push origin feature/earlgrey && ssh user@hpc 'cd /path/to/repo && git pull'
```

3. (Optional) Create a small `deploy_and_run.sh` helper locally:

```bash
#!/usr/bin/env bash
set -e
TARGET=user@hpc:/home/user/earlGrey_dev/
rsync -av --exclude 'work/' . "$TARGET"
ssh user@hpc 'cd /home/user/earlGrey_dev && nextflow run main.nf -profile hpc -resume -with-report report.html'
```

B. Nextflow `hpc` profile (example `conf/hpc.config`)

- This file should live under `conf/` and be referenced with `-profile hpc`.

```groovy
profiles {
  hpc {
    process {
      executor = 'lsf'
      queue = 'normal'
      // default cpus/memory/time can be overridden per process
      container = '' // set per-process or via params
    }
    singularity {
      enabled = true
      autoMounts = true
    }
    docker {
      enabled = false
    }
  }
}
```

Per-process cluster options (recommended in `nextflow.config` or per-process):

```groovy
process {
  withName:STRAINER {
    cpus = 4
    memory = '16 GB'
    time = '02:00'
    clusterOptions = '-R "rusage[mem=16000]" -P my_project'
    queue = 'long'
    container = 'docker://myorg/earlgrey:strain_v1'
  }
}
```

Notes:

- Use Singularity on HPC: Nextflow will automatically convert `docker://` URIs to Singularity images when `singularity.enabled = true`.
- Tune `clusterOptions`, `queue`, and resource requests to match cluster policy.

C. Wrapper submission via `bsub` (quick iterative tests)

- Each process should have a small wrapper in `scripts/nextflow-wrappers/` that accepts positional args and produces expected outputs + `metrics.json`.
- Example `bsub` command to run `strainer` wrapper:

```bash
mkdir -p logs
bsub -J earlgrey_strainer -q normal -n 4 -R "rusage[mem=8000]" -W 02:00 -o logs/strainer.%J.out -e logs/strainer.%J.err -- /bin/bash scripts/nextflow-wrappers/strainer.sh input.fa families.fa 4
```

- Ensure the wrapper loads required modules inside the script, e.g. `module load singularity`.

D. Containers & SIF tips for HPC

- Prefer Singularity SIF images on HPC. Build images locally (multi-stage Docker) and convert to SIF on HPC or in CI:

```bash
# on HPC or CI host with singularity installed
singularity build earlgrey-strain.sif docker://myorg/earlgrey:strain_v1
```

- Store SIFs in a shared storage path (e.g., `/group/shared/images/`) to avoid re-pulling on every run.
- If SIF pre-pull isn't possible, let Nextflow convert docker:// automatically to Singularity cache (slower first run).

E. Troubleshooting & best practices

- Test small wrappers first via `bsub` to verify environment, modules, and container access.
- Use `-with-report report.html -with-trace trace.txt` in Nextflow to gather process-level metrics.
- For reproducibility, pin image tags and record `singularity cache` location in `conf/hpc.config`.
- Clean up `work/` and `work/` caches between test runs or use `-resume` to continue runs.

Acceptance criteria

- You can `rsync`/`git` code to HPC and run `nextflow run main.nf -profile hpc` to submit jobs to LSF.
- You can submit per-process wrapper scripts with `bsub` and receive expected `metrics.json` and outputs.

Deliverables

- `plans/01_hpc_ssh_bsub.md` (this file)
- Example `deploy_and_run.sh` script (optional to add under `scripts/`) and sample `conf/hpc.config`

Notes & next steps

- Once you confirm the cluster specifics (queues, project names, module availability), I can scaffold `conf/hpc.config` with exact cluster options and add `deploy_and_run.sh` and example wrappers under `scripts/nextflow-wrappers/`.
