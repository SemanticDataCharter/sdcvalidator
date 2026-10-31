"""
The conformance suite (conformance/): sdcvalidator must still give every committed expected result.

A change here is a change to what "valid" means for every implementation of SDC4 validation, so a
failing case is not fixed by regenerating: regenerate only when the change is intended, record it in
the CHANGELOG, and give the other implementations the new expectations to meet.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sdcvalidator_gives_every_expected_result():
    run = subprocess.run(
        [sys.executable, str(ROOT / 'conformance' / 'tools' / 'expected.py'), '--check'],
        capture_output=True, text=True,
    )
    assert run.returncode == 0, run.stdout + run.stderr
