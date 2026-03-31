# 10 — Containerization: images, policies, and CI

Principles

- Keep images minimal and reproducible: prefer `debian:bullseye-slim` or distroless where possible; avoid Alpine for musl-related correctness issues.
- Pin versions for domain tools and verify licenses.
- Provide a small `dev` image for local iteration and larger `prod` images for real runs.

Image layout suggestions

- `earlgrey/dev:latest` — small image with Python, Rust toolchain (optional), and scripts for local dev. Use multi-stage builds to keep runtime image small.
- `earlgrey/tool-<name>:<tag>` — per-tool images for heavy domain tools (RepeatMasker, RepeatModeler). Keep them pinned and cached as SIF for HPC.

CI integration

- Build and push images in CI (GitHub Actions) on tag builds. Use `--cache-from` to speed up builds.
- Provide a `ci/docker-build.yaml` that builds dev/test images for PR validation.

Deliverables

- `plans/10_containerization.md` (this file)
- `devops/images/` template Dockerfiles for two standard images (dev and a sample tool image).

Notes

- When possible, prefer `docker://` URIs in Nextflow and let Singularity convert them to SIF on HPC, or prebuild SIFs in CI and stage to a shared location.
