# Planning prompts

model: GPT-5-mini

- Can you audit this codebase and identify ways to optimise the code? I plan to reimplement in Rust/Python using the `genomehubs/rust-py-template` as a starting point. I want to move orchestration to Nextflow and review all tools for efficiency, looking for opportunities to swap out tools or implement custom Rust code. Implement components so they can be swapped for A/B testing to compare speed and accuracy.

- Can you write the plan to file for iteration and refinement?

- Include a clear plan for evaluating alternate external tools for key steps and consider whether any are candidates for reimplementation (for example, if only a small subset of a tool's functionality is used).

- Define that Docker containers should be minimal (e.g., slim or distroless variants) but easy to configure; probably avoid Alpine where compatibility is a concern.

- Aim for nf-core compatibility, but avoid the overhead of full nf-core integration during development — align with best practices without committing to full integration until after A/B testing.

- Can you check that the steps are in a logical order and note any dependencies? Then create a `plans/` directory and work through the steps in `ITERATION_PLAN` to set out sub-steps in detail.

- I'll develop locally but will need SSH/LSF (bsub) jobs to run on HPC for testing. Define setting this up as part of the plan.

- One key aspect is using the template repo at `../../genomehubs/rust-py-template` to get initial setup consistent with other projects. Given the scope of changes, what would be a good folder structure as you begin the refactor?

- Can you scaffold a monorepo structure inside this repository?

- Can you pull in additional files from the template at `../../genomehubs/rust-py-template`? It covers both Rust and Python bindings to Rust and includes agent files that should be included to enforce code style.

- Add an agent instruction requiring an equivalence test for any function that is reimplemented to ensure equivalence. The legacy code lacks tests, so testing replaced functionality is useful; full unit testing is not required.

- Can you add a template for equivalence tests?

- Update the README to highlight that this is an experimental refactoring focused on performance, orchestration, and enabling A/B testing to refine the pipeline.
