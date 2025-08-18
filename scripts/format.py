#!/usr/bin/env python3
"""
Format code using black and isort.
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
        print(f"PASSED: {description} completed successfully")
        if result.stdout.strip():
            print(result.stdout)
        return True


def main():
    """Format the codebase."""
    root_dir = Path(__file__).parent.parent

    success = True

    # Run black formatter
    success &= run_command(["uv", "run", "black", "."], "Black code formatting")

    # Run isort for import sorting
    success &= run_command(["uv", "run", "isort", "."], "Import sorting with isort")

    if success:
        print("\nSUCCESS: Code formatting completed successfully!")
    else:
        print("\nFAILED: Code formatting failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
