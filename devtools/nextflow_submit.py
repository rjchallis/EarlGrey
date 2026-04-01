#!/usr/bin/env python3
"""devtools/nextflow_submit.py

Create and submit a Nextflow runner job on the remote cluster via SSH/LSF.

This helper builds a job script (with #BSUB headers), uploads it and
submits it with `bsub` on the configured `ssh_host` in
`devtools/config/baseline_config.yaml`.

It reuses the same `remote.init` mechanism as `baseline_submit.py` so you
can `module load` nextflow/singularity/lsf before running.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import textwrap
from typing import Any, Dict

try:
    import yaml
except Exception:
    print("PyYAML is required. pip install pyyaml", file=sys.stderr)
    sys.exit(1)

import importlib.util


def load_config(path: str) -> Dict[str, Any]:
    with open(path) as fh:
        return yaml.safe_load(fh)


def load_baseline_module(path: str):
    spec = importlib.util.spec_from_file_location("baseline_submit", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_job_script(
    remote_init: str, bsub: Dict[str, Any], remote_work_dir: str, jobname: str, nextflow_cmd: str
) -> str:
    # Build a job script containing #BSUB header lines and the nextflow command.
    header = textwrap.dedent(
        f"""
        #!/bin/bash
        #BSUB -e nextflow-{jobname}-%J.err
        #BSUB -J {jobname}
        #BSUB -q {bsub.get('queue','normal')}
        #BSUB -G {bsub.get('project','')}
        #BSUB -n {bsub.get('n',1)}
        #BSUB -M {bsub.get('mem',4000)}
        #BSUB -R "select[mem>{bsub.get('mem',4000)}] rusage[mem={bsub.get('mem',4000)}]"
        set -euo pipefail
        """
    )

    body = textwrap.dedent(
        f"""
        {remote_init}

        mkdir -p '{remote_work_dir}'
        cd '{remote_work_dir}'

        echo "Running: {nextflow_cmd}"
        {nextflow_cmd}
        """
    )

    return header + "\n" + body


def main(argv=None):
    p = argparse.ArgumentParser(description="Submit Nextflow runner as an LSF job on remote cluster")
    p.add_argument("--config", default="devtools/config/baseline_config.yaml")
    p.add_argument("--pipeline", default="./nextflow/main.nf", help="Nextflow pipeline (path or repo) to run")
    p.add_argument("--profiles", default="hpc,singularity", help="Comma-separated Nextflow profiles")
    p.add_argument("--outdir", required=True, help="Pipeline output directory (remote subdir)")
    p.add_argument("--work-subdir", help="work subdirectory (optional)")
    p.add_argument("--nextflow-args", default="", help="Extra args to pass to Nextflow")
    p.add_argument("--jobname", help="Job name override")
    p.add_argument("--mem", type=int, help="Memory MB for bsub override")
    p.add_argument("--n", type=int, help="Number of cores for bsub override")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--debug-remote", action="store_true")

    args = p.parse_args(argv)

    cfg = load_config(args.config)
    ssh_host = cfg.get("ssh_host")
    if not ssh_host:
        print("ssh_host must be defined in config", file=sys.stderr)
        sys.exit(2)

    remote_init = cfg.get("remote", {}).get("init", "")
    remote_work_root = cfg["remote"]["work_dir"]
    remote_work_dir = os.path.join(remote_work_root, args.work_subdir or args.outdir)

    bsub = dict(cfg.get("bsub_defaults", {}))
    if args.mem:
        bsub["mem"] = args.mem
    if args.n:
        bsub["n"] = args.n

    jobname = args.jobname or f"nextflow_{os.path.basename(args.outdir)}"

    # Compose nextflow command
    nextflow_cmd = f"nextflow run {args.pipeline} -profile {args.profiles} -work-dir '{remote_work_dir}' --outdir '{args.outdir}' {args.nextflow_args} -with-report report.html -with-trace trace.txt -with-timeline timeline.html"

    job_script = make_job_script(remote_init, bsub, remote_work_dir, jobname, nextflow_cmd)

    if args.dry_run:
        print("DRY RUN: remote host=", ssh_host)
        print("bsub settings:")
        print(json.dumps(bsub, indent=2))
        print("--- JOB SCRIPT ---")
        print(job_script)
        print("--- END SCRIPT ---")
        return

    # import baseline_submit helpers and submit
    baseline_path = os.path.join(os.path.dirname(__file__), "baseline_submit.py")
    baseline = load_baseline_module(baseline_path)

    # upload and submit using baseline.submit_job which uses ssh
    baseline.submit_job(
        ssh_host, bsub, remote_work_dir, jobname, job_script, remote_init=remote_init, debug=args.debug_remote
    )


if __name__ == "__main__":
    main()
