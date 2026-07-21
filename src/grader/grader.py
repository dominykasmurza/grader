"""Backward-compatible public API.

The implementation is split across focused modules. Existing imports from
``grader.grader`` continue to work through these re-exports.
"""

from .alignment import *
from .cli import build_arg_parser, main
from .detection import *
from .geometry import *
from .grading import *
from .part_detection import *
from .processing import *
from .reporting import *
from .templates import *
from .visualization import *
