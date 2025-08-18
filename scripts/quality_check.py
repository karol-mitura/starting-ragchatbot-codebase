#!/usr/bin/env python3
"""
Run all code quality checks (formatting, linting, and type checking).
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return True if successful."""
    print(f"\n{'='*50}")
    print(f"Running {description}...")
    print("=" * 50)

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FAILED: {description}:")
        if result.stdout.strip():
            print("STDOUT:")
            print(result.stdout)
        if result.stderr.strip():
            print("STDERR:")
            print(result.stderr)
        return False
    else:
        print(f"PASSED: {description}")
        if result.stdout.strip():
            print(result.stdout)
        return True


def main():
    """Run all code quality checks."""
    root_dir = Path(__file__).parent.parent

    print("Running comprehensive code quality checks...")

    checks = [
        (["uv", "run", "black", "--check", "."], "Black formatting check"),
        (["uv", "run", "isort", "--check-only", "."], "Import sorting check"),
        (["uv", "run", "flake8", "backend/", "main.py", "scripts/"], "Flake8 linting"),
        (
            ["uv", "run", "mypy", "backend/", "main.py", "scripts/"],
            "MyPy type checking",
        ),
    ]

    failed_checks = []

    for cmd, description in checks:
        if not run_command(cmd, description):
            failed_checks.append(description)

    print(f"\n{'='*60}")
    if failed_checks:
        print(f"FAILED: {len(failed_checks)} quality check(s) failed:")
        for check in failed_checks:
            print(f"  - {check}")
        print("\nRun the following to fix formatting issues:")
        print("  uv run python scripts/format.py")
        sys.exit(1)
    else:
        print("SUCCESS: All code quality checks passed!")


if __name__ == "__main__":
    main()
