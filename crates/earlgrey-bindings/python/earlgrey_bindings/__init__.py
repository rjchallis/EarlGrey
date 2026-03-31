"""EarlGrey Python bindings package.

This package re-exports the compiled Rust extension module.
"""

from .earlgrey_bindings import gc_content

__all__ = ["gc_content"]
