#!/usr/bin/env python3
"""
Run type checking using mypy.
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
    """Run type checking."""
    root_dir = Path(__file__).parent.parent

    success = True

    # Run mypy type checker
    success &= run_command(
        ["uv", "run", "mypy", "backend/", "main.py", "scripts/"], "MyPy type checking"
    )

    if success:
        print("\nSUCCESS: Type checking passed!")
    else:
        print("\nFAILED: Type checking failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
