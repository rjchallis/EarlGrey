#!/usr/bin/env python3
"""devtools/extract_chr1.py

Extract the first chromosome/sequence from a FASTA file (local or remote URL)
and save it as a new file for faster testing runs.

Usage examples:
  # Extract from a remote URL and save locally (compressed)
  ./devtools/extract_chr1.py --url https://ftp.ncbi.nlm.nih.gov/.../GCF_000146045.2_R64_genomic.fna.gz \\
      --output yeast_R64_chr1.fna.gz

  # Extract from a local FASTA file
  ./devtools/extract_chr1.py --input ./GCF_000146045.2_R64_genomic.fna --output yeast_R64_chr1.fna

This helper is useful for creating small test datasets (e.g. single chromosome)
to iterate quickly on baseline runs before full-genome analysis.
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


def download_file(url: str, output_path: str) -> str:
    """Download a file from URL using curl or wget.

    Returns the path to the downloaded file.
    """
    import subprocess

    print(f"Downloading {url}...")
    try:
        res = subprocess.run(
            ["curl", "-L", "-f", "-o", output_path, url],
            check=False,
            capture_output=True,
        )
        if res.returncode == 0:
            print(f"Downloaded to {output_path}")
            return output_path
    except FileNotFoundError:
        pass

    # Fallback to wget
    try:
        res = subprocess.run(
            ["wget", "-O", output_path, url],
            check=False,
            capture_output=True,
        )
        if res.returncode == 0:
            print(f"Downloaded to {output_path}")
            return output_path
    except FileNotFoundError:
        pass

    print("Neither curl nor wget available; cannot download", file=sys.stderr)
    sys.exit(1)


def main(argv=None):
    p = argparse.ArgumentParser(description="Extract first sequence from a FASTA file (local or remote)")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="remote FASTA URL to download and extract from")
    group.add_argument("--input", help="local FASTA file to extract from")
    p.add_argument("--output", required=True, help="output FASTA file (can end in .gz)")
    p.add_argument(
        "--compress",
        action="store_true",
        help="gzip-compress the output (default: auto-detect from .output filename)",
    )

    args = p.parse_args(argv)

    # Determine compression from output filename if not explicitly set
    compress = args.compress or args.output.endswith(".gz")

    # Get input file (download if URL)
    if args.url:
        # Download to a temp file first
        import tempfile

        temp_dir = tempfile.gettempdir()
        temp_input = f"{temp_dir}/temp_fasta_extract.fa"
        download_file(args.url, temp_input)
        input_path = temp_input
    else:
        input_path = args.input

    # Read and extract
    print(f"Extracting first sequence from {input_path}...")

    # Handle gzipped input
    if input_path.endswith(".gz"):
        with gzip.open(input_path, "rt") as f:
            first_seq = extract_first_sequence(f)
    else:
        with open(input_path, "r") as f:
            first_seq = extract_first_sequence(f)

    if not first_seq:
        print("No sequences found in input file", file=sys.stderr)
        sys.exit(1)

    # Write output
    print(f"Writing first sequence to {args.output}" + (" (gzip-compressed)" if compress else ""))
    if compress:
        with gzip.open(args.output, "wt") as f:
            f.write(first_seq)
            f.write("\n")
    else:
        with open(args.output, "w") as f:
            f.write(first_seq)
            f.write("\n")

    print(f"Done. Output: {args.output}")
    print(f"\nTo use this in devtools config, add:")
    print(
        f"""
  - id: {args.output.split('/')[-1].rsplit('.', 1)[0]}
    filename: {args.output.split('/')[-1]}
    species: yeast_R64  # adjust if needed
    threads: 4
"""
    )


if __name__ == "__main__":
    main()
