"""Equivalence test template

This pytest template demonstrates how to write an equivalence test that:
- runs the legacy implementation on a small fixture to produce a reference output,
- runs the new implementation (Rust/Python binding or CLI) on the same fixture,
- compares outputs using deterministic checks or tolerances.

Usage
- Edit `legacy_cmd` to invoke the legacy script/CLI that writes its output to
  `legacy_out`.
- Replace `run_new_impl(...)` with a call to the new implementation (Python
  binding or CLI) that writes to `new_out`.
- Enable the test by setting environment variable `RUN_EQUIVALENCE_TESTS=1`.

The test is skipped by default so CI won't fail while you're scaffolding.
"""

import filecmp
import os
import subprocess
from pathlib import Path

import pytest

RUN_EQUIV = os.getenv("RUN_EQUIVALENCE_TESTS") == "1"


@pytest.mark.skipif(not RUN_EQUIV, reason="Set RUN_EQUIVALENCE_TESTS=1 to run equivalence tests")
def test_equivalence_template(tmp_path):
    """Template equivalence test: compare legacy tool output vs. new implementation."""

    # Small example fixture - replace with a representative fixture from the repo
    fixture = Path("tests/example/input.fa")
    if not fixture.exists():
        pytest.skip("fixture not found: tests/example/input.fa")

    legacy_out = tmp_path / "legacy_out.txt"
    new_out = tmp_path / "new_out.txt"

    # TODO: update this to the legacy CLI invocation that writes to legacy_out
    # Example: legacy_cmd = ["bash", "scripts/nextflow-wrappers/prepare.sh", str(fixture), str(legacy_out), "default"]
    legacy_cmd = None

    if legacy_cmd:
        subprocess.run(legacy_cmd, check=True)
    else:
        pytest.skip("legacy_cmd not configured; edit test_equivalence_template.py to set legacy_cmd")

    # TODO: replace with new implementation invocation (import + call, or CLI)
    try:
        import earlgrey_bindings  # type: ignore
    except Exception as e:
        pytest.skip(f"earlgrey_bindings not available: {e}")

    # Example placeholder - replace with real API call
    # earlgrey_bindings.do_prepare(str(fixture), str(new_out), seed=42)
    pytest.skip("Replace the placeholder new implementation call with the real function or CLI")

    # Exact file comparison (common-case)
    assert filecmp.cmp(str(legacy_out), str(new_out), shallow=False)
