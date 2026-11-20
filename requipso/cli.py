import subprocess
import sys
from pathlib import Path


def main() -> None:
    notebook = Path(__file__).parent / "notebooks" / "marimo" / "run.py"
    code = subprocess.call(
        ["marimo", "run", str(notebook), "--show-tracebacks", *sys.argv[1:]]
    )
    sys.exit(code)
