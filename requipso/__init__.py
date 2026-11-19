from pathlib import Path

# Define paths FIRST before any other imports that might need them
BASE_DIR = Path(__file__).parent.resolve()
RESOURCES_DIR = BASE_DIR / "resources"

from .data import Data

# Registry and schema are imported lazily to avoid circular imports
# Use: from requipso.registry import registry
# Use: from requipso.schema import schema_provider

# Auto-install Polars column completer in IPython contexts
try:
    from IPython import get_ipython

    if get_ipython() is not None:
        from .completer import install as _install_completer

        _install_completer()
except ImportError:
    pass

__all__ = [
    "BASE_DIR",
    "RESOURCES_DIR",
]
