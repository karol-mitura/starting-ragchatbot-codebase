#!/usr/bin/env python3
"""
Run linting checks using flake8.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return True if successful."""
    print(f"Running {description}...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FAILED: {description}:")
        print(result.stdout)
        print(result.stderr)
        return False
    else:
        print(f"PASSED: {description}")
        return True


def main():
    """Run linting checks."""
    root_dir = Path(__file__).parent.parent

    success = True

    # Run flake8 linter
    success &= run_command(
        ["uv", "run", "flake8", "backend/", "main.py", "scripts/"], "Flake8 linting"
    )

    if success:
        print("\nSUCCESS: Linting checks passed!")
    else:
        print("\nFAILED: Linting checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
