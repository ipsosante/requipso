import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

DOCS_ADDR = "127.0.0.1:8001"


def _start_docs() -> subprocess.Popen | None:
    mkdocs_yml = Path(__file__).parent / "docs" / "mkdocs.yml"
    if not mkdocs_yml.exists() or shutil.which("mkdocs") is None:
        print("[requipso] Documentation non disponible (mkdocs ou mkdocs.yml absent).")
        return None
    proc = subprocess.Popen(
        ["mkdocs", "serve", "-f", str(mkdocs_yml), "-a", DOCS_ADDR, "--no-livereload"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # mkdocs builds the site (importing requipso.pipes) before it starts listening.
    threading.Timer(4, webbrowser.open_new_tab, args=[f"http://{DOCS_ADDR}"]).start()
    return proc


def main() -> None:
    notebook = Path(__file__).parent / "notebooks" / "marimo" / "run.py"
    docs = _start_docs()
    try:
        code = subprocess.call(
            ["marimo", "run", str(notebook), "--show-tracebacks", *sys.argv[1:]]
        )
    finally:
        if docs is not None:
            docs.terminate()
    sys.exit(code)
