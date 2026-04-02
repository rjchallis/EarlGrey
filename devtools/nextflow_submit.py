#!/usr/bin/env python3
"""devtools/nextflow_submit.py

Rsync the nextflow/ pipeline directory to the remote cluster, then submit a
Nextflow runner as an LSF job via bsub.

Assembly parameters (genome path, species, threads) are resolved from the
same `devtools/config/baseline_config.yaml` used by baseline_submit.py —
just pass --id <assembly_id>.

Usage examples:

    # Dry run (show job script; do not submit)
    make nextflow-dry-run ID=yeast_R64_chr1

    # Submit chr1 test job
    make nextflow-submit ID=yeast_R64_chr1

    # Submit full genome job
    make nextflow-submit ID=yeast_R64

    # Override profiles
    make nextflow-submit ID=yeast_R64 NF_PROFILES=hpc
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import textwrap
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:
    print("PyYAML is required. pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def load_config(path: str) -> Dict[str, Any]:
    with open(path) as fh:
        return yaml.safe_load(fh)


def find_assembly(cfg: Dict[str, Any], aid: str) -> Dict[str, Any]:
    for a in cfg.get("assemblies", []):
        if a.get("id") == aid:
            return a
    raise KeyError(f"assembly id '{aid}' not found in config")


def load_baseline_module(devtools_dir: str):
    path = os.path.join(devtools_dir, "baseline_submit.py")
    spec = importlib.util.spec_from_file_location("baseline_submit", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rsync_dir(
    ssh_host: str,
    local_dir: str,
    remote_dir: str,
    exclude: list | None = None,
    dry_run: bool = False,
) -> None:
    """Rsync a local directory to the remote host, creating the destination first."""
    src = local_dir.rstrip("/") + "/"
    dest = f"{ssh_host}:{remote_dir}/"
    cmd = ["rsync", "-az", "--delete"]
    for pat in exclude or []:
        cmd += ["--exclude", pat]
    cmd += [src, dest]
    label = os.path.basename(local_dir.rstrip("/"))
    if dry_run:
        print("DRY RUN rsync:", " ".join(cmd))
        return
    # rsync cannot create intermediate parent directories on the remote side;
    # create them explicitly before transferring.
    mkdir = subprocess.run(["ssh", ssh_host, f"mkdir -p '{remote_dir}'"], check=False)
    if mkdir.returncode != 0:
        raise RuntimeError(f"failed to create remote directory: {remote_dir}")
    print(f"Syncing {label}/ to {ssh_host}:{remote_dir} ...")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"rsync failed (exit {result.returncode})")
    print(f"Synced {label}/.")


def make_job_script(
    remote_init: str,
    bsub: Dict[str, Any],
    jobname: str,
    remote_work_dir: str,
    nextflow_cmd: str,
) -> str:
    mem = bsub.get("mem", 4000)
    return textwrap.dedent(
        f"""\
        #!/bin/bash
        #BSUB -J {jobname}
        #BSUB -q {bsub.get('queue', 'normal')}
        #BSUB -G {bsub.get('project', '')}
        #BSUB -n {bsub.get('n', 1)}
        #BSUB -M {mem}
        #BSUB -R "select[mem>{mem}] rusage[mem={mem}] span[hosts=1]"
        #BSUB -o {remote_work_dir}/{jobname}.%J.out
        #BSUB -e {remote_work_dir}/{jobname}.%J.err

        set -euo pipefail

        {remote_init}

        mkdir -p '{remote_work_dir}'
        cd '{remote_work_dir}'

        echo "Started: $(date)"
        echo "Running: {nextflow_cmd}"

        {nextflow_cmd}

        echo "Finished: $(date)"
    """
    )


def resolve_genome_path(
    cfg: Dict[str, Any],
    asm: Dict[str, Any],
) -> str:
    """Return the expected path to the decompressed genome on the remote."""
    remote_data_root = cfg["remote"]["data_dir"]
    remote_data_dir = os.path.join(remote_data_root, asm.get("out_dir", asm["id"]))
    filename = asm["filename"]
    # baseline_submit.py decompresses .gz files and drops the .gz extension
    if filename.endswith(".gz"):
        filename = filename[:-3]
    return os.path.join(remote_data_dir, filename)


def main(argv: Optional[list] = None) -> None:
    p = argparse.ArgumentParser(description="Rsync pipeline to remote cluster and submit as an LSF job")
    p.add_argument(
        "--config",
        default="config/baseline_config.yaml",
        help="Baseline config YAML (default: config/baseline_config.yaml)",
    )
    p.add_argument(
        "--id",
        required=True,
        help="Assembly ID from config (used to resolve genome path, species, threads)",
    )
    p.add_argument(
        "--profiles",
        default="hpc,singularity",
        help="Nextflow -profile value (default: hpc,singularity)",
    )
    p.add_argument(
        "--outdir-name",
        help="Output subdirectory name under remote work_dir (default: <id>_nextflow)",
    )
    p.add_argument(
        "--script-dir",
        help="Override --script_dir passed to Nextflow (default: <work_dir>/../scripts)",
    )
    p.add_argument(
        "--variant",
        default="default",
        help="Nextflow --variant AB-testing profile (default: default)",
    )
    p.add_argument(
        "--repeat-species",
        default="",
        help="Pass --repeat_species to Nextflow for an initial Dfam masking step",
    )
    p.add_argument(
        "--extra-args",
        default="",
        help="Any additional arguments forwarded verbatim to nextflow run",
    )
    p.add_argument(
        "--mem",
        type=int,
        help="Override bsub memory (MB) for the Nextflow driver job",
    )
    p.add_argument(
        "--n",
        type=int,
        help="Override bsub slot count for the Nextflow driver job",
    )
    p.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    p.add_argument("--debug-remote", action="store_true", help="Verbose SSH output")
    p.add_argument(
        "--no-rsync",
        action="store_true",
        help="Skip rsync step (pipeline already at remote destination)",
    )
    args = p.parse_args(argv)

    cfg = load_config(args.config)
    ssh_host = cfg.get("ssh_host")
    if not ssh_host:
        print("ERROR: ssh_host must be defined in config", file=sys.stderr)
        sys.exit(2)

    asm = find_assembly(cfg, args.id)
    remote_init = cfg.get("remote", {}).get("init", "")
    remote_work_root = cfg["remote"]["work_dir"]
    species = asm.get("species", args.id)
    threads = asm.get("threads", cfg.get("bsub_defaults", {}).get("n", 4))

    outdir_name = args.outdir_name or f"{args.id}_nextflow"
    remote_work_dir = os.path.join(remote_work_root, outdir_name)

    # Pipeline lives one level up from devtools/
    devtools_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(devtools_dir)
    local_nextflow_dir = os.path.join(repo_root, "nextflow")
    local_scripts_dir = os.path.join(repo_root, "scripts")

    # Remote destinations: live under a shared "pipeline" prefix
    remote_pipeline_root = os.path.join(remote_work_root, "pipeline")
    remote_pipeline_dir = os.path.join(remote_pipeline_root, "nextflow")
    remote_scripts_dir = os.path.join(remote_pipeline_root, "scripts")

    genome_path = resolve_genome_path(cfg, asm)

    # script_dir: config value > CLI override > auto-derived
    config_scripts_dir = cfg.get("remote", {}).get("scripts_dir", "").strip()
    script_dir = args.script_dir or config_scripts_dir or remote_scripts_dir

    # Collect outputs inside the work directory
    remote_outdir = os.path.join(remote_work_dir, "results")
    pipeline_info_dir = os.path.join(remote_outdir, "pipeline_info")

    # Build the nextflow run command
    nf_parts = [
        f"nextflow run '{remote_pipeline_dir}/main.nf'",
        f"-profile {args.profiles}",
        f"-work-dir '{remote_work_dir}/.nf_work'",
        f"--genome '{genome_path}'",
        f"--species '{species}'",
        f"--outdir '{remote_outdir}'",
        f"--threads {threads}",
        f"--script_dir '{script_dir}'",
        f"--variant {args.variant}",
        f"-with-report '{pipeline_info_dir}/report.html'",
        f"-with-trace '{pipeline_info_dir}/trace.txt'",
        f"-with-timeline '{pipeline_info_dir}/timeline.html'",
        f"-with-dag '{pipeline_info_dir}/dag.svg'",
        "-resume",
    ]
    if args.repeat_species:
        nf_parts.append(f"--repeat_species '{args.repeat_species}'")
    if asm.get("repeat_term"):
        nf_parts.append(f"--repeat_type '{asm['repeat_term']}'")
    if args.extra_args:
        # Avoid duplicating -resume if it's already in the static command
        extra = args.extra_args.strip()
        if extra not in ("-resume", "--resume"):
            nf_parts.append(extra)

    nextflow_cmd = " \\\n    ".join(nf_parts)

    bsub = dict(cfg.get("bsub_defaults", {}))
    # Driver job only needs a couple of cores / modest memory; workers are
    # submitted by Nextflow itself.
    bsub["n"] = args.n or 2
    bsub["mem"] = args.mem or 4000
    # Allow remote.queue to override the driver queue (bsub_defaults.queue
    # is intended for the legacy baseline job which needs many cores).
    remote_queue = cfg.get("remote", {}).get("queue", "")
    if remote_queue:
        bsub["queue"] = remote_queue

    jobname = f"nf_{args.id}"
    # Point LSF output files into the work dir, not the user's home dir.
    bsub["out"] = f"{remote_work_dir}/{jobname}.%J.out"
    bsub["err"] = f"{remote_work_dir}/{jobname}.%J.err"
    job_script = make_job_script(remote_init, bsub, jobname, remote_work_dir, nextflow_cmd)

    if args.dry_run:
        print(f"DRY RUN — remote host : {ssh_host}")
        print(f"Assembly              : {args.id}")
        print(f"Genome path (remote)  : {genome_path}")
        print(f"Species               : {species}")
        print(f"Remote work dir       : {remote_work_dir}")
        print(f"Pipeline dir (remote) : {remote_pipeline_dir}")
        print(f"Scripts dir (remote)  : {script_dir}")
        print(f"Profiles              : {args.profiles}")
        print()
        print("--- RSYNC (would run) ---")
        print(f"  {local_nextflow_dir}/ → {ssh_host}:{remote_pipeline_dir}/")
        print(f"  {local_scripts_dir}/  → {ssh_host}:{remote_scripts_dir}/")
        print()
        print("--- JOB SCRIPT ---")
        print(job_script)
        print("--- END SCRIPT ---")
        return

    # ── Rsync pipeline code and scripts to remote ────────────────────────────
    if not args.no_rsync:
        rsync_dir(
            ssh_host,
            local_nextflow_dir,
            remote_pipeline_dir,
            exclude=[".work", "results", ".nextflow"],
        )
        rsync_dir(ssh_host, local_scripts_dir, remote_scripts_dir)

    # ── Submit job ────────────────────────────────────────────────────────────
    baseline = load_baseline_module(devtools_dir)
    baseline.submit_job(
        ssh_host,
        bsub,
        remote_work_dir,
        jobname,
        job_script,
        remote_init=remote_init,
        debug=args.debug_remote,
    )


if __name__ == "__main__":
    main()
