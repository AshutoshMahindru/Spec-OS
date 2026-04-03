"""Repository-root shim for local src-layout development.

Python 3.14 skips hidden editable-install ``.pth`` files, which breaks local
console-script and ``python -m`` execution in this checkout. Expose
``src/spec_os`` on the package search path when imports resolve through the
repository root.
"""

from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

SRC_PACKAGE = Path(__file__).resolve().parent.parent / "src" / "spec_os"
if SRC_PACKAGE.is_dir():
    src_path = str(SRC_PACKAGE)
    if src_path in __path__:
        __path__.remove(src_path)
    __path__.insert(0, src_path)

__version__ = "2.0.0"
