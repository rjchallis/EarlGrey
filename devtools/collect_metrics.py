#!/usr/bin/env python3
"""Collect and compare baseline metrics from earlGrey runs.

Usage:
  python3 collect_metrics.py --baseline /lustre/.../yeast_R64 --run /lustre/.../yeast_R64_baseline_iter_001
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class RunMetrics:
    """Metrics collected from a single earlGrey run."""

    run_id: str
    run_dir: str
    timestamp: str
    genome_size_bp: int
    num_sequences: int
    repeatmasker_time_sec: float
    repeatmodeler_time_sec: float
    repeatmodeler_rounds: int
    repeatmodeler_families_found: int
    repeatscout_families: int
    recon_families: int
    total_wall_time_sec: float
    peak_memory_mb: float | None = None
    cpu_percent: float | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


def extract_metrics_from_log(log_path: str) -> dict:
    """Extract timing and metrics from earlGrey.log."""
    metrics = {}

    try:
        with open(log_path, "r") as f:
            content = f.read()

        # Extract database info
        seq_match = re.search(r"Sequences = (\d+)", content)
        if seq_match:
            metrics["num_sequences"] = int(seq_match.group(1))

        bases_match = re.search(r"Bases = (\d+)", content)
        if bases_match:
            metrics["genome_size_bp"] = int(bases_match.group(1))

        # Extract RepeatScout families
        repeatscout_match = re.search(r"RepeatScout:.*?(\d+).*?families identified", content)
        if repeatscout_match:
            metrics["repeatscout_families"] = int(repeatscout_match.group(1))
        else:
            # Try alternate pattern
            repeatscout_match = re.search(r"no families identified", content)
            if repeatscout_match:
                metrics["repeatscout_families"] = 0

        # Extract RECON families
        recon_match = re.search(r"Number of families returned by RECON: (\d+)", content)
        if recon_match:
            metrics["recon_families"] = int(recon_match.group(1))

        # Extract RepeatModeler family counts and timing
        families_match = re.search(r"(\d+) families discovered", content)
        if families_match:
            metrics["repeatmodeler_families_found"] = int(families_match.group(1))

        # Count rounds
        rounds = len(re.findall(r"RepeatModeler Round #", content))
        metrics["repeatmodeler_rounds"] = rounds

        # Extract total program time
        time_match = re.search(r"Program Time: (\d+):(\d+):(\d+)", content)
        if time_match:
            h, m, s = int(time_match.group(1)), int(time_match.group(2)), int(time_match.group(3))
            metrics["repeatmodeler_time_sec"] = h * 3600 + m * 60 + s

    except Exception as e:
        print(f"Warning: Error parsing log {log_path}: {e}", file=sys.stderr)

    return metrics


def extract_metrics_from_time_output(metrics_path: str) -> dict:
    """Parse /usr/bin/time -v output file."""
    metrics = {}

    try:
        with open(metrics_path, "r") as f:
            content = f.read()

        # Map of metric names to regex patterns
        patterns = {
            "user_time_sec": r"User time \(seconds\): ([\d.]+)",
            "system_time_sec": r"System time \(seconds\): ([\d.]+)",
            "elapsed_wall_time": r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): ([\d:\.]+)",
            "percent_cpu": r"Percent of CPU this job got: ([\d.]+)%",
            "peak_rss_mb": r"Maximum resident set size \(kbytes\): (\d+)",
            "major_page_faults": r"Major \(requiring I/O\) page faults: (\d+)",
            "minor_page_faults": r"Minor \(reclaiming a page\) page faults: (\d+)",
            "io_input_blocks": r"File system inputs: (\d+)",
            "io_output_blocks": r"File system outputs: (\d+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value = match.group(1)
                # Convert to numeric types
                if key in ("user_time_sec", "system_time_sec", "percent_cpu"):
                    try:
                        metrics[key] = float(value)
                    except ValueError:
                        metrics[key] = value
                elif key.endswith("_mb") or key.endswith("_faults") or key.startswith("io_"):
                    try:
                        metrics[key] = int(value)
                    except ValueError:
                        metrics[key] = value
                else:
                    metrics[key] = value

        # Convert peak RSS from KB to MB
        if "peak_rss_mb" in metrics:
            metrics["peak_rss_mb"] = metrics["peak_rss_mb"] / 1024.0

        # Parse elapsed wall time (handle both h:mm:ss and m:ss formats)
        if "elapsed_wall_time" in metrics:
            time_str = metrics["elapsed_wall_time"]
            parts = time_str.split(":")
            try:
                if len(parts) == 3:
                    h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
                    metrics["elapsed_wall_time_sec"] = h * 3600 + m * 60 + s
                elif len(parts) == 2:
                    m, s = int(parts[0]), float(parts[1])
                    metrics["elapsed_wall_time_sec"] = m * 60 + s
            except (ValueError, IndexError):
                pass

    except FileNotFoundError:
        pass  # Metrics file may not exist yet
    except Exception as e:
        print(f"Warning: Error parsing time output {metrics_path}: {e}", file=sys.stderr)

    return metrics


def collect_metrics_from_run(ssh_host: str, run_dir: str, run_id: str) -> RunMetrics | None:
    """Collect all metrics from a single run directory on remote host."""
    try:
        # Find the main earlGrey log
        cmd = f"find {run_dir} -name 'Saccharomyces_cerevisiaeEarlGrey.log' 2>/dev/null | head -1"
        result = subprocess.run(
            ["ssh", ssh_host, cmd],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if not result.stdout.strip():
            print(f"Warning: No earlGrey.log found in {run_dir}", file=sys.stderr)
            return None

        log_path = result.stdout.strip()

        # Copy log locally for parsing
        local_tmp = f"/tmp/earlgrey_log_{run_id}.log"
        subprocess.run(
            ["scp", "-q", f"{ssh_host}:{log_path}", local_tmp],
            timeout=10,
        )

        # Also look for metrics file from time -v output
        metrics_file_remote = os.path.join(run_dir, "earlgrey_metrics.txt")
        local_metrics_tmp = f"/tmp/earlgrey_metrics_{run_id}.txt"

        metrics_time_output = {}
        try:
            subprocess.run(
                ["scp", "-q", f"{ssh_host}:{metrics_file_remote}", local_metrics_tmp],
                timeout=10,
            )
            metrics_time_output = extract_metrics_from_time_output(local_metrics_tmp)
            os.unlink(local_metrics_tmp)
        except Exception as e:
            print(f"Info: Could not retrieve time metrics ({metrics_file_remote}): {e}", file=sys.stderr)

        # Extract metrics from earlGrey log
        metrics_dict = extract_metrics_from_log(local_tmp)
        metrics_dict.update(metrics_time_output)

        # Use elapsed wall time from time -v if available, fallback to RepeatModeler time
        total_wall_time = metrics_dict.get("elapsed_wall_time_sec") or metrics_dict.get("repeatmodeler_time_sec", 0)

        metrics = RunMetrics(
            run_id=run_id,
            run_dir=run_dir,
            timestamp=datetime.now().isoformat(),
            genome_size_bp=metrics_dict.get("genome_size_bp", 0),
            num_sequences=metrics_dict.get("num_sequences", 0),
            repeatmasker_time_sec=0,  # TODO: extract from logs
            repeatmodeler_time_sec=metrics_dict.get("repeatmodeler_time_sec", 0),
            repeatmodeler_rounds=metrics_dict.get("repeatmodeler_rounds", 0),
            repeatmodeler_families_found=metrics_dict.get("repeatmodeler_families_found", 0),
            repeatscout_families=metrics_dict.get("repeatscout_families", 0),
            recon_families=metrics_dict.get("recon_families", 0),
            total_wall_time_sec=total_wall_time,
            peak_memory_mb=metrics_dict.get("peak_rss_mb"),
            cpu_percent=metrics_dict.get("percent_cpu"),
        )

        # Cleanup
        os.unlink(local_tmp)

        return metrics

    except Exception as e:
        print(f"Error collecting metrics from {run_dir}: {e}", file=sys.stderr)
        return None


def compare_metrics(baseline: RunMetrics, current: RunMetrics) -> None:
    """Print a comparison table between baseline and current run."""
    print("\n" + "=" * 100)
    print("BASELINE METRICS COMPARISON")
    print("=" * 100)

    metrics_list = [
        ("Genome Size (bp)", "genome_size_bp", lambda x: f"{x:,}"),
        ("Num Sequences", "num_sequences", lambda x: f"{x}"),
        ("RepeatModeler Rounds", "repeatmodeler_rounds", lambda x: f"{x}"),
        ("RepeatScout Families", "repeatscout_families", lambda x: f"{x}"),
        ("RECON Families", "recon_families", lambda x: f"{x}"),
        ("Families Found", "repeatmodeler_families_found", lambda x: f"{x}"),
        ("RepeatModeler Time (sec)", "repeatmodeler_time_sec", lambda x: f"{x:.1f}"),
        ("Total Wall Time (sec)", "total_wall_time_sec", lambda x: f"{x:.1f}"),
        ("Peak Memory (MB)", "peak_memory_mb", lambda x: f"{x:.1f}" if x else "N/A"),
        ("CPU %", "cpu_percent", lambda x: f"{x:.1f}%" if x else "N/A"),
    ]

    print(f"\n{'Metric':<40} {'Baseline':<20} {'Current':<20} {'Δ':<15}")
    print("-" * 100)

    for metric_name, attr, formatter in metrics_list:
        baseline_val = getattr(baseline, attr)
        current_val = getattr(current, attr)

        # Skip if both are None/0
        if baseline_val is None and current_val is None:
            continue

        # Format values
        baseline_str = formatter(baseline_val) if baseline_val is not None and baseline_val != 0 else "N/A"
        current_str = formatter(current_val) if current_val is not None and current_val != 0 else "N/A"

        # Calculate delta
        delta_str = "N/A"
        if baseline_val is not None and current_val is not None and baseline_val > 0:
            delta_pct = ((current_val - baseline_val) / baseline_val) * 100
            delta_str = f"{delta_pct:+.1f}%"

        print(f"{metric_name:<40} {baseline_str:<20} {current_str:<20} {delta_str:<15}")

    print("\n" + "=" * 100)


def main(argv=None):
    p = argparse.ArgumentParser(description="Collect and compare earlGrey baseline metrics")
    p.add_argument("--ssh-host", default="farm", help="SSH host alias")
    p.add_argument("--baseline", required=True, help="baseline run directory (remote)")
    p.add_argument("--run", required=True, help="current run directory (remote)")
    p.add_argument("--output", help="write JSON metrics to file")

    args = p.parse_args(argv)

    print("Collecting metrics from baseline run...")
    baseline = collect_metrics_from_run(args.ssh_host, args.baseline, "baseline")
    if not baseline:
        print("Failed to collect baseline metrics", file=sys.stderr)
        sys.exit(1)

    print("Collecting metrics from current run...")
    current = collect_metrics_from_run(args.ssh_host, args.run, "current")
    if not current:
        print("Failed to collect current run metrics", file=sys.stderr)
        sys.exit(1)

    # Print comparison
    compare_metrics(baseline, current)

    # Save JSON if requested
    if args.output:
        metrics_data = {
            "baseline": baseline.to_dict(),
            "current": current.to_dict(),
            "comparison_timestamp": datetime.now().isoformat(),
        }
        with open(args.output, "w") as f:
            json.dump(metrics_data, f, indent=2)
        print(f"\nMetrics saved to {args.output}")


if __name__ == "__main__":
    main()
