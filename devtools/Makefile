# Site-local overrides (gitignored).  Copy Makefile.local.example → Makefile.local
# and set BASELINE_RUN / CURRENT_RUN for your cluster paths.
-include Makefile.local

CONFIG ?= config/baseline_config.yaml
ID     ?= yeast_R64_chr1
PY     ?= python3
OUT_DIR ?=
NF_PROFILES ?= hpc,singularity
NF_VARIANT  ?= default
NF_EXTRA    ?=
BASELINE_RUN ?=
CURRENT_RUN ?=

.PHONY: help dry-run submit chmod \
        nextflow-validate nextflow-dry-run nextflow-submit nextflow-collect-metrics nextflow-logs \
        extract-chr1 extract-chr1-remote collect-metrics

help:
	@echo "Usage: make [target] [VARIABLE=value]"
	@echo ""
	@echo "=== Baseline (legacy earlGrey) ==="
	@echo "  dry-run              Print job script without submitting (ID=yeast_R64)"
	@echo "  submit               Submit baseline earlGrey job to remote cluster"
	@echo "  collect-metrics      Compare two baseline runs locally"
	@echo "  extract-chr1-remote  Extract chr1 from an assembly on the remote"
	@echo ""
	@echo "=== Nextflow pipeline ==="
	@echo "  nextflow-validate    Local syntax check (needs nextflow installed locally)"
	@echo "  nextflow-dry-run     Dry run: show rsync + job script without submitting"
	@echo "  nextflow-submit      Rsync pipeline + submit Nextflow job to remote cluster"
	@echo "  nextflow-collect-metrics  Fetch trace.txt from last Nextflow run and print summary"
	@echo ""
	@echo "Variables (with defaults):"
	@echo "  ID=$(ID)             Assembly ID from config"
	@echo "  CONFIG=$(CONFIG)     Config file path"
	@echo "  NF_PROFILES=$(NF_PROFILES)  Nextflow -profile value"
	@echo "  NF_VARIANT=$(NF_VARIANT)   Nextflow --variant (AB testing)"
	@echo "  NF_EXTRA=$(NF_EXTRA)       Extra args forwarded to Nextflow"
	@echo "  OUT_DIR=$(OUT_DIR)          Override output subdirectory name"
	@echo ""
	@echo "Examples:"
	@echo "  # Test Nextflow with chr1 (fast ~5 min)"
	@echo "  make nextflow-dry-run ID=yeast_R64_chr1"
	@echo "  make nextflow-submit  ID=yeast_R64_chr1"
	@echo ""
	@echo "  # Full genome run"
	@echo "  make nextflow-submit  ID=yeast_R64 NF_PROFILES=hpc,singularity"
	@echo ""
	@echo "  # AB test: fast RepeatModeler"
	@echo "  make nextflow-submit  ID=yeast_R64_chr1 NF_VARIANT=repeatmodeler_fast"

# ─── Legacy baseline targets ────────────────────────────────────────────────

dry-run:
	$(PY) ./baseline_submit.py --config $(CONFIG) --id $(ID) $(if $(OUT_DIR),--out-dir $(OUT_DIR)) --dry-run

submit:
	$(PY) ./baseline_submit.py --config $(CONFIG) --id $(ID) $(if $(OUT_DIR),--out-dir $(OUT_DIR))

chmod:
	chmod +x ./baseline_submit.py

extract-chr1:
	$(PY) ./extract_chr1.py --url $(URL) --output $(OUTPUT)

extract-chr1-remote:
	$(PY) ./baseline_submit.py --config $(CONFIG) --extract-chr1-from $(ID)

collect-metrics:
	$(PY) ./collect_metrics.py \
		--baseline $(BASELINE_RUN) \
		--run $(CURRENT_RUN) \
		--output metrics_comparison.json
	@echo ""
	@echo "Metrics saved to metrics_comparison.json"

# ─── Nextflow targets ────────────────────────────────────────────────────────

# Local syntax check — validates DSL2 module imports and workflow body
# without running any processes or requiring a cluster.
# Install nextflow locally: brew install nextflow
# or: curl -s https://get.nextflow.io | bash
nextflow-validate:
	@echo "Checking Nextflow syntax (--help)..."
	cd ../nextflow && nextflow run main.nf --help
	@echo ""
	@echo "Inspecting workflow DAG (nextflow inspect)..."
	cd ../nextflow && nextflow inspect main.nf --params-file /dev/null 2>&1 || \
	  echo "(nextflow inspect requires Nextflow >=23 — skip if not available)"

# Dry run: show exactly what will be rsynced and the job script, no submission
nextflow-dry-run:
	$(PY) ./nextflow_submit.py \
		--config $(CONFIG) \
		--id $(ID) \
		--profiles "$(NF_PROFILES)" \
		--variant $(NF_VARIANT) \
		$(if $(OUT_DIR),--outdir-name $(OUT_DIR)) \
		$(if $(NF_EXTRA),--extra-args=$(NF_EXTRA)) \
		--dry-run

# Rsync nextflow/ to the cluster then submit as an LSF job.
# The Nextflow driver runs on one LSF slot and submits per-process sub-jobs.
nextflow-submit:
	$(PY) ./nextflow_submit.py \
		--config $(CONFIG) \
		--id $(ID) \
		--profiles "$(NF_PROFILES)" \
		--variant $(NF_VARIANT) \
		$(if $(OUT_DIR),--outdir-name $(OUT_DIR)) \
		$(if $(NF_EXTRA),--extra-args=$(NF_EXTRA))

# Fetch pipeline_info/trace.txt from the last Nextflow run and print a
# per-process timing summary.
# Requires: ssh access + assembly ID to resolve the remote outdir path.
nextflow-collect-metrics:
	@REMOTE_OUTDIR=$$($(PY) -c "import yaml,os;cfg=yaml.safe_load(open('$(CONFIG)'));w=cfg['remote']['work_dir'];print(os.path.join(w,'$(if $(OUT_DIR),$(OUT_DIR),$(ID)_nextflow)','results','pipeline_info'))"); \
	SSH_HOST=$$($(PY) -c "import yaml;print(yaml.safe_load(open('$(CONFIG)'))['ssh_host'])"); \
	echo "Fetching trace from $$SSH_HOST:$$REMOTE_OUTDIR/trace.txt ..."; \
	scp "$$SSH_HOST:$$REMOTE_OUTDIR/trace.txt" ./nf_trace_$(ID).txt && \
	echo "" && \
	echo "=== Per-process timing summary ===" && \
	awk -F'\t' 'NR==1{for(i=1;i<=NF;i++) h[$$i]=i; next} \
	  {printf "%-40s  %s\n", $$h["name"], $$h["realtime"]}' ./nf_trace_$(ID).txt | sort && \
	echo "" && \
	echo "Full trace saved to: ./nf_trace_$(ID).txt"

# Fetch and print the LSF driver job output/error logs and any Nextflow .nextflow.log.
# Use OUT_DIR= to match the directory you submitted with.
nextflow-logs:
	@REMOTE_WORK=$$($(PY) -c "import yaml,os;cfg=yaml.safe_load(open('$(CONFIG)'));print(os.path.join(cfg['remote']['work_dir'],'$(if $(OUT_DIR),$(OUT_DIR),$(ID)_nextflow)'))"); \
	SSH_HOST=$$($(PY) -c "import yaml;print(yaml.safe_load(open('$(CONFIG)'))['ssh_host'])"); \
	JOBNAME="nf_$(ID)"; \
	echo "=== LSF stdout ($$SSH_HOST:$$REMOTE_WORK/$$JOBNAME.*.out) ==="; \
	ssh $$SSH_HOST "ls -t $$REMOTE_WORK/$$JOBNAME.*.out ~/$$JOBNAME.*.out 2>/dev/null | head -1 | xargs -r cat" || echo "(no .out file found)"; \
	echo ""; \
	echo "=== LSF stderr ($$SSH_HOST:$$REMOTE_WORK/$$JOBNAME.*.err) ==="; \
	ssh $$SSH_HOST "ls -t $$REMOTE_WORK/$$JOBNAME.*.err ~/$$JOBNAME.*.err 2>/dev/null | head -1 | xargs -r cat" || echo "(no .err file found)"; \
	echo ""; \
	echo "=== Nextflow log ($$SSH_HOST:$$REMOTE_WORK/.nextflow.log) ==="; \
	ssh $$SSH_HOST "cat $$REMOTE_WORK/.nextflow.log 2>/dev/null | tail -100" || echo "(no .nextflow.log found)"

