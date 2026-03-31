"""Type stubs for the ``earlgrey_bindings`` Rust extension module.

Keep this file in sync with the ``#[pyfunction]`` exports in ``src/lib.rs``.
Pyright (and Pylance) use these stubs for type checking — the compiled ``.so``
file does not need to be present during static analysis.

When adding a new Rust function:
1. Add the ``#[pyfunction]`` in ``src/lib.rs``.
2. Register it with ``m.add_function(...)`` in the ``#[pymodule]``.
3. Add a typed signature here.
4. Add it to ``__init__.py``'s imports and ``__all__``.
"""

def gc_content(sequence: str) -> float:
    """Return the GC content of a DNA/RNA sequence as a fraction in [0.0, 1.0].

    GC content is the proportion of bases that are guanine (G/g) or cytosine
    (C/c). Both upper- and lower-case bases are recognised. Returns 0.0 for
    an empty sequence.

    Args:
        sequence: DNA or RNA sequence string (A, T/U, G, C; any case).

    Returns:
        Fraction of bases that are G or C, in the range ``[0.0, 1.0]``.
    """
    ...
