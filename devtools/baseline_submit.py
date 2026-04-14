#!/usr/bin/env python3
"""
baseline_submit.py

Parameterised helper to fetch an assembly (remote URL if needed) and submit
an EarlGrey baseline job on a remote LSF cluster via SSH.

Usage examples:
  # use entry from config
  ./devtools/baseline_submit.py --config config/baseline_config.yaml --id yeast_R64

  # one-off use with url and filename
  ./devtools/baseline_submit.py --config config/baseline_config.yaml \
      --url https://.../GCF_...fna.gz --filename GCF_...fna.gz --out-dir test_run --species S_example

Notes:
- The example config file is provided at `config/baseline_config.yaml.example`.
- Copy it to `config/baseline_config.yaml` and edit values locally (do not commit).
- This script requires PyYAML on the machine/environment where it runs.
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
    print("PyYAML is required. Activate your conda env and `pip install pyyaml`.", file=sys.stderr)
    sys.exit(1)


def load_config(path: str) -> Dict[str, Any]:
    with open(path) as fh:
        return yaml.safe_load(fh)


def find_assembly(cfg: Dict[str, Any], aid: str) -> Dict[str, Any]:
    for a in cfg.get("assemblies", []):
        if a.get("id") == aid:
            return a
    raise KeyError(f"assembly id '{aid}' not found in config")


def ssh_run(host: str, script: str, capture: bool = False, login: bool = True) -> subprocess.CompletedProcess:
    """Run `script` on remote host via ssh.

    By default this invokes a login shell on the remote side so user init
    files are sourced (useful to load modules and scheduler `bsub` into
    `PATH`). Set `login=False` to use a non-login shell.
    """
    shell_arg = "bash -l -s" if login else "bash -s"
    proc = subprocess.run(
        ["ssh", host, shell_arg],
        input=script.encode("utf-8"),
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=False,
    )
    return proc


def ensure_remote_file(
    ssh_host: str,
    url: str,
    remote_path: str,
    filename: str,
    decompress: bool = True,
    remote_init: str = "",
    debug: bool = False,
) -> str:
    """Ensure the file exists on the remote host; fetch if missing.

    Automatically checks if the file already exists on the remote side. If it
    does and is not corrupted (>1000 bytes), skips the download. Otherwise,
    fetches from the provided URL.

    If `decompress` is True and the filename ends with .gz, also create an
    uncompressed copy (using `gunzip -c`) and return the path to the
    uncompressed file. Returns the final path to provide to `earlGrey`.
    """
    # remote-safe shell script that prints the final path as REMOTE_FINAL=...
    decompress_flag = "true" if decompress else "false"
    prefix = "set -x\n" if debug else ""
    remote_init_block = (remote_init.strip() + "\n") if remote_init else ""
    cmd = textwrap.dedent(
        f"""
        set -euo pipefail
        {prefix}{remote_init_block}
        echo `pwd`  # debug: print remote working dir
        mkdir -p '{remote_path}'

        # Smart fetch: check if file exists locally first before downloading
        file_path='{remote_path}/{filename}'

        # Check if file exists and is reasonable size (not corrupted stub)
        if [ -f "$file_path" ]; then
            file_size=$(stat -c%s "$file_path" 2>/dev/null || stat -f%z "$file_path" 2>/dev/null || echo 0)
            if [ "$file_size" -lt 1000 ]; then
                echo "File $file_path exists but is too small ($file_size bytes); likely corrupted. Removing and refetching..."
                rm -f "$file_path"
            else
                echo "Remote file $file_path exists (size: $file_size bytes); skipping download."
            fi
        fi

        # Fetch if file doesn't exist or was removed as corrupted
        if [ ! -f "$file_path" ]; then
            echo 'Fetching {filename} from {url}...'
            (curl -L -f -o '{remote_path}/{filename}' '{url}' || wget -O '{remote_path}/{filename}' '{url}')
            file_size=$(stat -c%s "$file_path" 2>/dev/null || stat -f%z "$file_path" 2>/dev/null || echo 0)
            echo "Downloaded file (size: $file_size bytes)"
        fi

        # handle optional decompression of .gz files
        if [ "{decompress_flag}" = "true" ]; then
            case "{filename}" in
                *.gz)
                    uncompressed="{remote_path}/$(basename '{filename}' .gz)"
                    if [ ! -f "${{uncompressed}}" ]; then
                        echo "Decompressing {filename} to ${{uncompressed}}..."
                        gunzip -c '{remote_path}/{filename}' > "${{uncompressed}}" || {{
                            echo "Error: gunzip decompression failed"
                            rm -f "${{uncompressed}}"
                            exit 1
                        }}
                        # Validate that decompression produced a non-empty file
                        output_size=$(stat -c%s "${{uncompressed}}" 2>/dev/null || stat -f%z "${{uncompressed}}" 2>/dev/null || echo 0)
                        if [ "$output_size" -eq 0 ]; then
                            echo "Error: decompression produced empty file (0 bytes); .gz file may be corrupted"
                            rm -f "${{uncompressed}}" "$file_path"
                            exit 1
                        fi
                    else
                        echo "Uncompressed file ${{uncompressed}} exists; skipping decompression."
                    fi
                    echo "REMOTE_FINAL=${{uncompressed}}"
                    ;;
                *)
                    echo "REMOTE_FINAL={remote_path}/{filename}"
                    ;;
            esac
        else
            echo "REMOTE_FINAL={remote_path}/{filename}"
        fi
    """
    )

    print(f"Ensuring remote file {remote_path}/{filename} on {ssh_host} (decompress={decompress})")
    if debug:
        print("--- REMOTE SCRIPT ---")
        print(cmd)
        print("--- END REMOTE SCRIPT ---")

    res = ssh_run(ssh_host, cmd, capture=True)
    out = res.stdout.decode() if res.stdout else ""
    err = res.stderr.decode() if res.stderr else ""
    if res.returncode != 0:
        if out:
            print(out, file=sys.stdout)
        if err:
            print(err, file=sys.stderr)
        raise RuntimeError("remote fetch failed")
    else:
        if debug:
            if out:
                print(out)
            if err:
                print(err, file=sys.stderr)

    # parse REMOTE_FINAL= from stdout
    final = None
    for line in out.splitlines():
        if line.startswith("REMOTE_FINAL="):
            final = line.split("=", 1)[1].strip()
            break
    if not final:
        # fallback: if no REMOTE_FINAL printed, try to infer
        final = f"{remote_path}/{filename}"
    return final


def submit_job(
    ssh_host: str,
    bsub: Dict[str, Any],
    remote_work_dir: str,
    jobname: str,
    job_script: str,
    remote_init: str = "",
    debug: bool = False,
) -> None:
    # ensure work dir exists and upload script
    mkdir_cmd = f"mkdir -p '{remote_work_dir}'"
    res = ssh_run(ssh_host, mkdir_cmd, capture=True)
    if res.returncode != 0:
        print(res.stdout.decode() if res.stdout else "", file=sys.stdout)
        print(res.stderr.decode() if res.stderr else "", file=sys.stderr)
        raise RuntimeError("failed to create remote work dir")

    remote_script_path = f"{remote_work_dir}/{jobname}.sh"
    # write script to remote
    print(f"Uploading job script to {ssh_host}:{remote_script_path}")
    put = subprocess.run(
        ["ssh", ssh_host, f"cat > '{remote_script_path}'"],
        input=job_script.encode("utf-8"),
    )
    if put.returncode != 0:
        raise RuntimeError("failed to upload remote script")
    # make executable
    res = ssh_run(ssh_host, f"chmod +x '{remote_script_path}'", capture=True)
    if res.returncode != 0:
        print(res.stdout.decode() if res.stdout else "", file=sys.stdout)
        print(res.stderr.decode() if res.stderr else "", file=sys.stderr)
        raise RuntimeError("failed to chmod remote script")

    # build bsub command
    bsub_cmd = (
        f"bsub -n {bsub['n']} -R \"span[hosts=1] select[mem>{bsub['mem']}] rusage[mem={bsub['mem']}]\" "
        f"-M {bsub['mem']} -q {bsub['queue']} -o {bsub['out']} -e {bsub['err']} -P {bsub['project']} < '{remote_script_path}'"
    )

    print("Submitting job via bsub on remote host...")
    # if a remote init string is provided, run it before the bsub command
    bsub_wrapper = f"{remote_init}\n{bsub_cmd}" if remote_init else bsub_cmd
    res = ssh_run(ssh_host, bsub_wrapper, capture=True)
    if res.returncode != 0:
        print(res.stdout.decode() if res.stdout else "", file=sys.stdout)
        print(res.stderr.decode() if res.stderr else "", file=sys.stderr)
        raise RuntimeError("bsub submission failed")
    else:
        out = res.stdout.decode() if res.stdout else ""
        print("bsub output:\n", out)


def extract_chr1_remote(
    ssh_host: str,
    remote_data_dir: str,
    filename: str,
    remote_init: str = "",
    debug: bool = False,
) -> str:
    """Extract first sequence from a remote FASTA and save as _chr1 variant.

    Returns the path to the extracted chr1 file on the remote host.
    """
    # Generate the chr1 filename
    base, ext = os.path.splitext(filename)

    # Check if already a chr1 extraction to avoid double-naming
    if base.endswith("_chr1.fna"):
        # Already extracted; just ensure .gz extension if input was .gz
        chr1_filename = filename
    elif ext == ".gz":
        chr1_filename = f"{base}_chr1.fna.gz"
    else:
        chr1_filename = f"{base}_chr1.fna"

    remote_input = os.path.join(remote_data_dir, filename)
    remote_output = os.path.join(remote_data_dir, chr1_filename)

    # Build a shell script that extracts chr1 on the remote side using Python
    extraction_script = f"""
import gzip
import sys

def extract_first_sequence(infile):
    seq_lines = []
    in_first_seq = False
    found_header = False
    for line in infile:
        line = line.rstrip('\\n')
        if not line:
            continue
        if line.startswith('>'):
            if found_header and seq_lines:
                break
            if not found_header:
                found_header = True
                in_first_seq = True
                seq_lines.append(line)
            continue
        if in_first_seq:
            seq_lines.append(line)
    return '\\n'.join(seq_lines)

input_path = "{remote_input}"
output_path = "{remote_output}"

print(f"Extracting first sequence from {{input_path}}...", flush=True)

if input_path.endswith(".gz"):
    with gzip.open(input_path, "rt") as f:
        first_seq = extract_first_sequence(f)
else:
    with open(input_path, "r") as f:
        first_seq = extract_first_sequence(f)

if not first_seq:
    print("Error: no sequences found", file=sys.stderr, flush=True)
    sys.exit(1)

compress_output = output_path.endswith(".gz")
if compress_output:
    with gzip.open(output_path, "wt") as f:
        f.write(first_seq)
        f.write("\\n")
else:
    with open(output_path, "w") as f:
        f.write(first_seq)
        f.write("\\n")

print(f"Done. Output: {{output_path}}", flush=True)
"""

    # Wrap with remote_init if provided
    prefix = "set -x\n" if debug else ""
    remote_init_block = (remote_init.strip() + "\n") if remote_init else ""
    cmd = f"""set -euo pipefail
{prefix}{remote_init_block}python3 << 'PYTHON_EOF'
{extraction_script}
PYTHON_EOF
"""

    print(f"Extracting chr1 from {remote_input} on {ssh_host}...")
    if debug:
        print("--- REMOTE SCRIPT ---")
        print(cmd)
        print("--- END REMOTE SCRIPT ---")

    res = ssh_run(ssh_host, cmd, capture=True)
    if res.returncode != 0:
        out = res.stdout.decode() if res.stdout else ""
        err = res.stderr.decode() if res.stderr else ""
        if out:
            print(out, file=sys.stdout)
        if err:
            print(err, file=sys.stderr)
        raise RuntimeError("remote chr1 extraction failed")
    else:
        out = res.stdout.decode() if res.stdout else ""
        if debug or True:  # Always print output for visibility
            if out:
                print(out)

    return remote_output


def make_job_script(
    remote_data_file: str, species: str, out_dir: str, threads: int, repeat_term: str, remote_init: str = ""
) -> str:
    # job script executed on the remote login node (and then by the compute node via bsub)
    # Use /usr/bin/time -v to capture detailed metrics
    metrics_file = os.path.join(out_dir, "earlgrey_metrics.txt")

    script = textwrap.dedent(
        f"""
        #!/bin/bash
        set -euo pipefail

        export OMP_NUM_THREADS=1
        export OPENBLAS_NUM_THREADS=1
        export MKL_NUM_THREADS=1

        # load your shell init so conda is available (customise if needed)
        . ~/.bashrc 2>/dev/null || true

        {remote_init}

        if command -v conda >/dev/null 2>&1; then
            conda activate earlgrey || true
        fi

        mkdir -p '{out_dir}'

        echo "Running earlGrey on {remote_data_file}"
        /usr/bin/time -v earlGrey -g '{remote_data_file}' -s '{species}' -o '{out_dir}' -r '{repeat_term}' -t {threads} 2> '{metrics_file}' || {{
            # earlGrey may fail but we still want to save metrics
            echo "earlGrey failed with exit code $?" >> '{metrics_file}'
            exit 1
        }}
    """
    )
    return script


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Fetch assembly (remote if needed) and submit EarlGrey via bsub on remote cluster"
    )
    p.add_argument(
        "--config",
        default="config/baseline_config.yaml",
        help="path to baseline config (copy from .example and keep local)",
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--id", help="assembly id from config to submit")
    group.add_argument("--url", help="assembly URL to fetch directly")
    group.add_argument(
        "--extract-chr1-from",
        help="assembly id from config: extract first chromosome and print config entry (no submit)",
    )
    p.add_argument("--filename", help="local filename for the assembly (required with --url)")
    p.add_argument("--out-dir", help="remote output subdirectory (overrides config assembly.out_dir)")
    p.add_argument("--threads", type=int, help="threads for earlGrey (overrides config)")
    p.add_argument("--mem", type=int, help="memory MB for bsub (overrides bsub_defaults)")
    p.add_argument("--dry-run", action="store_true", help="print planned actions but do not run")
    p.add_argument("--no-decompress", action="store_true", help="do not decompress .gz files on remote host")
    p.add_argument(
        "--debug-remote",
        action="store_true",
        help="print the remote script before execution and enable set -x on remote for tracing",
    )

    args = p.parse_args(argv)

    cfg = load_config(args.config)
    ssh_host = cfg.get("ssh_host")
    if not ssh_host:
        print("ssh_host must be defined in config", file=sys.stderr)
        sys.exit(2)

    # Handle chr1 extraction if requested
    if args.extract_chr1_from:
        asm = find_assembly(cfg, args.extract_chr1_from)
        url = asm.get("url")
        filename = asm.get("filename")
        species = asm.get("species", args.extract_chr1_from)
        local_out = args.extract_chr1_from
        remote_data_root = cfg["remote"]["data_dir"]
        remote_data_dir = os.path.join(remote_data_root, local_out)
        remote_init = cfg.get("remote", {}).get("init", "")

        # Ensure the file exists first (fetch if missing)
        # Note: skip remote_init for fetch since we don't need modules for simple extraction
        remote_file = ensure_remote_file(
            ssh_host,
            url,
            remote_data_dir,
            filename,
            decompress=False,
            remote_init="",  # Don't load modules for simple fetch/extraction
            debug=args.debug_remote,
        )

        # Extract chr1 on the remote
        chr1_path = extract_chr1_remote(
            ssh_host,
            remote_data_dir,
            filename,
            remote_init="",  # Don't load modules for extraction
            debug=args.debug_remote,
        )

        # Output config entry for the user to add
        print("\n✓ Chr1 extraction complete!")
        print("\nAdd this entry to your devtools/config/baseline_config.yaml under 'assemblies':")

        default_threads = asm.get("threads", cfg.get("bsub_defaults", {}).get("n", 4))
        print(
            f"""
  - id: {args.extract_chr1_from}_chr1
    filename: {os.path.basename(chr1_path)}
    species: {species}
    threads: {default_threads}
"""
        )
        print(f"Remote path: {chr1_path}")
        return

    if args.id:
        asm = find_assembly(cfg, args.id)
        url = asm.get("url")
        filename = asm.get("filename")
        species = asm.get("species", args.id)
        # Data directory: based on assembly id/out_dir (shared across runs)
        # Work directory: based on --out-dir override if provided, otherwise assembly out_dir or id
        data_dir_id = asm.get("out_dir") or args.id
        work_dir_id = args.out_dir or asm.get("out_dir") or args.id
        threads = args.threads or asm.get("threads", cfg.get("bsub_defaults", {}).get("n", 4))
        repeat_term = asm.get("repeat_term", "")
        decompress_cfg = asm.get("decompress_gz", cfg.get("decompress_gz", True))
    else:
        if not args.filename:
            print("--filename is required when using --url", file=sys.stderr)
            sys.exit(2)
        url = args.url
        filename = args.filename
        species = args.out_dir or "sample"
        # For one-off URL runs, both data and work use out_dir
        data_dir_id = args.out_dir or os.path.splitext(filename)[0]
        work_dir_id = args.out_dir or os.path.splitext(filename)[0]
        threads = args.threads or cfg.get("bsub_defaults", {}).get("n", 4)
        repeat_term = ""
        decompress_cfg = cfg.get("decompress_gz", True)

    remote_data_root = cfg["remote"]["data_dir"]
    remote_work_root = cfg["remote"]["work_dir"]
    remote_data_dir = os.path.join(remote_data_root, data_dir_id)
    remote_work_dir = os.path.join(remote_work_root, work_dir_id)
    remote_init = cfg.get("remote", {}).get("init", "")

    # decide whether to decompress .gz on remote (can be overridden with --no-decompress)
    decompress = (not args.no_decompress) and bool(decompress_cfg)
    # preview remote file (before fetch) and preview final file name
    preview_raw = os.path.join(remote_data_dir, filename)
    if decompress and filename.endswith(".gz"):
        preview_final = os.path.join(remote_data_dir, filename[:-3])
    else:
        preview_final = preview_raw

    bsub = dict(cfg.get("bsub_defaults", {}))
    if args.mem:
        bsub["mem"] = args.mem
    bsub.setdefault("out", "fastga.%J")
    bsub.setdefault("err", "fastga.er.%J")
    bsub.setdefault("project", cfg.get("remote", {}).get("project", ""))

    # jobname based on final filename (use base name without extensions)
    jobname = f"earlgrey_{os.path.splitext(os.path.basename(preview_final))[0]}"

    if args.dry_run:
        print("DRY RUN\nConfig:")
        print(
            json.dumps(
                {
                    "ssh_host": ssh_host,
                    "remote_data_preview": preview_raw,
                    "remote_final_preview": preview_final,
                    "remote_init": remote_init,
                    "remote_work_dir": remote_work_dir,
                    "bsub": bsub,
                    "decompress": decompress,
                },
                indent=2,
            )
        )
        print("\nJob script preview:\n")
        print(make_job_script(preview_final, species, remote_work_dir, threads, repeat_term, remote_init=remote_init))
        return

    # ensure remote has the data file (fetch on remote if necessary) and get final path
    remote_data_file = ensure_remote_file(
        ssh_host,
        url,
        remote_data_dir,
        filename,
        decompress=decompress,
        remote_init=remote_init,
        debug=args.debug_remote,
    )

    # create the job script and submit
    job_script = make_job_script(
        remote_data_file, species, remote_work_dir, threads, repeat_term, remote_init=remote_init
    )
    submit_job(ssh_host, bsub, remote_work_dir, jobname, job_script, remote_init=remote_init, debug=args.debug_remote)


if __name__ == "__main__":
    main()
