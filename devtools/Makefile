CONFIG ?= config/baseline_config.yaml
ID     ?= yeast_R64
PY     ?= python3
OUT_DIR ?=

.PHONY: help dry-run submit chmod nextflow-dry-run nextflow-submit extract-chr1

help:
	@echo "Usage: make [target] [VARIABLE=value]"
	@echo "Targets: help, dry-run, submit, chmod, nextflow-dry-run, nextflow-submit, extract-chr1"
	@echo ""
	@echo "Variables:"
	@echo "  ID=<id>              assembly id (default: yeast_R64)"
	@echo "  OUT_DIR=<dir>        override output directory (optional, for multiple test runs)"
	@echo "  CONFIG=<path>        config file path (default: config/baseline_config.yaml)"

dry-run:
	$(PY) ./baseline_submit.py --config $(CONFIG) --id $(ID) $(if $(OUT_DIR),--out-dir $(OUT_DIR)) --dry-run

submit:
	$(PY) ./baseline_submit.py --config $(CONFIG) --id $(ID) $(if $(OUT_DIR),--out-dir $(OUT_DIR))

nextflow-dry-run:
	$(PY) ./nextflow_submit.py --config $(CONFIG) --outdir $(ID)_nextflow --dry-run

nextflow-submit:
	$(PY) ./nextflow_submit.py --config $(CONFIG) --outdir $(ID)_nextflow --debug-remote

chmod:
	chmod +x ./baseline_submit.py

extract-chr1:
	$(PY) ./extract_chr1.py --url $(URL) --output $(OUTPUT)

extract-chr1-remote:
	$(PY) ./baseline_submit.py --config $(CONFIG) --extract-chr1-from $(ID)
