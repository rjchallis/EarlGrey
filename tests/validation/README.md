Equivalence test templates

Place small fixtures under `tests/example/` and use the test template
`tests/validation/test_equivalence_template.py` to write an equivalence test
for a reimplemented function.

How to run (locally):

```bash
# enable equivalence tests
export RUN_EQUIVALENCE_TESTS=1
pytest tests/validation/ -q
```

Test guidance:

- Prefer small, deterministic fixtures (subset of real inputs).
- If the new implementation is stochastic, pass and record a fixed `seed`.
- Use file checksums or numeric tolerances for comparing floating-point results.
- Document acceptance criteria in the test docstring.
