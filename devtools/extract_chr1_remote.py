#!/usr/bin/env python3
"""devtools/extract_chr1_remote.py

Extract the first chromosome/sequence from a remote FASTA file (already on the cluster)
and save it as a new file for fast testing.

This script is meant to be run on the remote cluster directly, or via SSH.

Usage examples:
  # Extract on remote cluster (run inside LSF job or via SSH)
  python3 extract_chr1_remote.py --remote-input /lustre/.../GCF_000146045.2_R64_genomic.fna.gz \\
      --remote-output /lustre/.../yeast_R64_chr1.fna.gz

SSH wrapper (call from local machine):
  # Uses baseline_submit config to SSH to cluster and run extraction
  python3 baseline_submit.py --config config/baseline_config.yaml --extract-chr1-remote yeast_R64
"""

from __future__ import annotations

import argparse
import gzip
import sys
from typing import TextIO


def extract_first_sequence(infile: TextIO) -> str:
    """Read a FASTA and extract only the first sequence as a string."""
    seq_lines = []
    in_first_seq = False
    found_header = False

    for line in infile:
        line = line.rstrip("\n")
        if not line:
            continue

        if line.startswith(">"):
            if found_header and seq_lines:
                # We've hit the second header; stop here
                break
            if not found_header:
                # First header
                found_header = True
                in_first_seq = True
                seq_lines.append(line)
            continue

        if in_first_seq:
            seq_lines.append(line)

    return "\n".join(seq_lines)


def main(argv=None):
    p = argparse.ArgumentParser(description="Extract first sequence from a remote FASTA file on cluster")
    p.add_argument("--remote-input", required=True, help="path to input FASTA on remote cluster")
    p.add_argument("--remote-output", required=True, help="path to output file on remote cluster")

    args = p.parse_args(argv)

    # Detect compression from filename
    compress_input = args.remote_input.endswith(".gz")
    compress_output = args.remote_output.endswith(".gz")

    print(f"Extracting first sequence from {args.remote_input}...")

    # Read from remote path (could be .gz or plain)
    if compress_input:
        with gzip.open(args.remote_input, "rt") as f:
            first_seq = extract_first_sequence(f)
    else:
        with open(args.remote_input, "r") as f:
            first_seq = extract_first_sequence(f)

    if not first_seq:
        print("No sequences found in input file", file=sys.stderr)
        sys.exit(1)

    # Write to remote output
    print(f"Writing first sequence to {args.remote_output}" + (" (gzip)" if compress_output else ""))
    if compress_output:
        with gzip.open(args.remote_output, "wt") as f:
            f.write(first_seq)
            f.write("\n")
    else:
        with open(args.remote_output, "w") as f:
            f.write(first_seq)
            f.write("\n")

    print(f"Done. Output: {args.remote_output}")


if __name__ == "__main__":
    main()
