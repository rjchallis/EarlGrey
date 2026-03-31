# 11 — Validation & AB test acceptance

Goal

- Define acceptance tests and validation metrics for AB experiments comparing implementation variants.

Validation metrics

- Precision/Recall against a gold or expected set (if available).
- Structural metrics: number of predicted TEs, total bp masked, mean length distribution, fragmentation rate.
- Runtime & memory metrics from `metrics.json`.

AB acceptance rules

- Define thresholds for acceptable quality loss for any variant (e.g., <2% absolute recall drop), or require improved runtime with no significant loss.
- For algorithms that change semantics, require a human review on a small sample set and document differences.

Deliverables

- `plans/11_validation_ab.md` (this file)
- `tests/validation/` containing scripts to compute precision/recall and structural metrics.

Next steps

- Provide a small `tests/validation/run_validation.sh` that reads predicted GFF and expected GFF and outputs a metrics CSV.
