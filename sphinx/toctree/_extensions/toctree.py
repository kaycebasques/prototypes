"""Custom Sphinx extension named toctree."""

from typing import Any, Dict
from sphinx.application import Sphinx


def setup(app: Sphinx) -> Dict[str, Any]:
    print("[toctree extension] Initialized custom extension!")
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
