"""helix_pct6 -- read ATF PC-Tool 6 setup files (`.pct6`). Read only, Python 3.9+ standard library.

    doc = read_pct6("preset.pct6")      # or read_pct6(file_bytes)
    inv = interpret(doc)                 # everything, raw + interpreted, JSON-ready
    diff = differences(doc, other_doc)   # by category: audio / system / save_metadata / ui_state / unknown
    rows = check(doc, [{"path": "/ATF/OC[@ON='16']/T[1]/@T", "expected": 4.63, "policy": "display_delay_ms"}])

There is no encoder and no write: this package never creates or changes a `.pct6` (see README, "Never writes").
Format documented by amATFpct6.
"""

from .compare import category, check, differences
from .container import (ChecksumError, ContainerError, Document, LimitError, Pct6Error, TruncatedError, XmlError,
                        file_unchanged, read_pct6)
from .inventory import interpret
from .models import MODELS, VERIFIED_NAMES, WARNING

__version__ = "0.1.0"
CREDIT = "Format documented by amATFpct6."

__all__ = ["read_pct6", "interpret", "differences", "check", "category", "file_unchanged", "Document",
           "Pct6Error", "ContainerError", "ChecksumError", "TruncatedError", "LimitError", "XmlError",
           "MODELS", "VERIFIED_NAMES", "WARNING", "CREDIT", "__version__"]
