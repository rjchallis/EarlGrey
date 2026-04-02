#!/usr/bin/env python3
"""Wrapper script to instrument earlGrey with detailed timing and resource metrics.

This script wraps earlGrey to capture per-step metrics including:
  - Wallclock time
  - CPU time
  - Peak resident set size (RSS)
  - Exit status
  - Output file sizes

Usage:
  earlgrey_instrumented.py -g <genome> -s <species> -o <output> [other earlGrey options]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def run_with_timing(cmd: list[str], label: str) -> dict:
    """Run a command with /usr/bin/time -v and capture metrics.

    Returns dict with: start_time, end_time, walltime_sec, return_code, time_output
    """
    start_time = time.time()
    start_dt = datetime.now().isoformat()

    # Prepend /usr/bin/time -v to capture detailed metrics
    instrumented_cmd = ["/usr/bin/time", "-v"] + cmd

    print(f"[{label}] Running: {' '.join(cmd)}", file=sys.stderr)

    try:
        result = subprocess.run(
            instrumented_cmd,
            capture_output=True,
            text=True,
            timeout=86400,  # 24 hour timeout
        )
    except subprocess.TimeoutExpired:
        return {
            "label": label,
            "status": "timeout",
            "start_time": start_dt,
            "end_time": datetime.now().isoformat(),
            "error": "Command timed out after 24 hours",
            "return_code": -1,
        }

    end_time = time.time()
    end_dt = datetime.now().isoformat()
    walltime_sec = end_time - start_time

    metrics = {
        "label": label,
        "start_time": start_dt,
        "end_time": end_dt,
        "walltime_sec": walltime_sec,
        "return_code": result.returncode,
        "status": "success" if result.returncode == 0 else "failed",
    }

    # Parse /usr/bin/time output (stderr)
    time_output = result.stderr
    time_metrics = parse_time_output(time_output)
    metrics.update(time_metrics)

    return metrics


def parse_time_output(time_output: str) -> dict:
    """Parse /usr/bin/time -v output and extract key metrics."""
    metrics = {}

    # Map of metric names to regex patterns
    patterns = {
        "user_time_sec": r"User time \(seconds\): ([\d.]+)",
        "system_time_sec": r"System time \(seconds\): ([\d.]+)",
        "elapsed_time_sec": r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): ([\d:]+)",
        "percent_cpu": r"Percent of CPU this job got: ([\d.]+)%",
        "peak_rss_mb": r"Maximum resident set size \(kbytes\): (\d+)",
        "exit_code": r"Exit status: (\d+)",
        "major_page_faults": r"Major \(requiring I/O\) page faults: (\d+)",
        "minor_page_faults": r"Minor \(reclaiming a page\) page faults: (\d+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, time_output, re.IGNORECASE)
        if match:
            value = match.group(1)
            # Convert to numeric types where appropriate
            if key.endswith("_sec") or key == "percent_cpu":
                try:
                    metrics[key] = float(value)
                except ValueError:
                    metrics[key] = value
            elif key.endswith("_mb") or key.endswith("_faults"):
                try:
                    metrics[key] = int(value)
                except ValueError:
                    metrics[key] = value
            else:
                metrics[key] = value

    # Convert peak RSS from KB to MB
    if "peak_rss_mb" in metrics:
        metrics["peak_rss_mb"] = metrics["peak_rss_mb"] / 1024.0

    return metrics


def collect_output_metrics(output_dir: str) -> dict:
    """Collect metrics about the output directory."""
    metrics = {}

    try:
        output_path = Path(output_dir)
        if output_path.exists():
            # Count files and total size
            total_size = 0
            file_count = 0
            for root, dirs, files in os.walk(output_dir):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total_size += os.path.getsize(fp)
                        file_count += 1
                    except OSError:
                        pass

            metrics["output_dir_size_mb"] = total_size / (1024 * 1024)
            metrics["output_file_count"] = file_count

    except Exception as e:
        print(f"Warning: Error collecting output metrics: {e}", file=sys.stderr)

    return metrics


def main(argv=None):
    # Parse earlGrey arguments (pass through to earlGrey)
    parser = argparse.ArgumentParser(description="Instrumented earlGrey wrapper")
    parser.add_argument("-g", "--genome", required=True, help="Input genome FASTA")
    parser.add_argument("-s", "--species", required=True, help="Species name")
    parser.add_argument("-o", "--out-dir", dest="out_dir", required=True, help="Output directory")
    parser.add_argument("-r", "--repeat-type", dest="repeat_type", default="", help="Repeat type")
    parser.add_argument("-t", "--threads", type=int, default=1, help="Number of threads")
    parser.add_argument("--metrics-file", help="Output file for metrics JSON")

    # Capture any additional args for earlGrey
    args, extra_args = parser.parse_known_args(argv)

    # Build earlGrey command
    earlgrey_cmd = [
        "earlGrey",
        "-g",
        args.genome,
        "-s",
        args.species,
        "-o",
        args.out_dir,
    ]

    if args.repeat_type:
        earlgrey_cmd.extend(["-r", args.repeat_type])

    earlgrey_cmd.extend(["-t", str(args.threads)])
    earlgrey_cmd.extend(extra_args)

    # Run with instrumentation
    record_start = datetime.now().isoformat()
    run_metrics = run_with_timing(earlgrey_cmd, "earlGrey")
    record_end = datetime.now().isoformat()

    # Collect output metrics
    output_metrics = collect_output_metrics(args.out_dir)
    run_metrics.update(output_metrics)

    # Save metrics
    output_data = {
        "invocation_time": record_start,
        "completion_time": record_end,
        "command": earlgrey_cmd,
        "run_metrics": run_metrics,
    }

    if args.metrics_file:
        os.makedirs(os.path.dirname(args.metrics_file) or ".", exist_ok=True)
        with open(args.metrics_file, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nMetrics saved to {args.metrics_file}", file=sys.stderr)

    # Print summary
    print(f"\n{'=' * 70}", file=sys.stderr)
    print("EARLGREY RUN SUMMARY", file=sys.stderr)
    print(f"{'=' * 70}", file=sys.stderr)
    print(f"Status:             {run_metrics.get('status', 'unknown')}", file=sys.stderr)
    print(f"Walltime (sec):     {run_metrics.get('walltime_sec', 'N/A'):.1f}", file=sys.stderr)
    print(f"User Time (sec):    {run_metrics.get('user_time_sec', 'N/A')}", file=sys.stderr)
    print(f"CPU %:              {run_metrics.get('percent_cpu', 'N/A')}", file=sys.stderr)
    print(f"Peak RSS (MB):      {run_metrics.get('peak_rss_mb', 'N/A'):.1f}", file=sys.stderr)
    print(f"Output Size (MB):   {run_metrics.get('output_dir_size_mb', 'N/A'):.1f}", file=sys.stderr)
    print(f"Output Files:       {run_metrics.get('output_file_count', 'N/A')}", file=sys.stderr)
    print(f"{'=' * 70}", file=sys.stderr)

    sys.exit(run_metrics.get("return_code", 1))


if __name__ == "__main__":
    main()
