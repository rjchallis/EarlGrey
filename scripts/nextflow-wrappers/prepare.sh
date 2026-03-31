#!/usr/bin/env bash
set -euo pipefail
input=${1:-tests/example/input.fa}
outdir=${2:-prepared}
variant=${3:-default}
mkdir -p "$outdir"
start=$(date +%s)
# placeholder operation
echo "prepared from $input (variant=$variant)" > "$outdir/result.txt"
rc=0
end=$(date +%s)
walltime=$((end-start))
cat > "$outdir/metrics.json" <<EOF
{"process":"prepare","variant":"$variant","walltime_seconds":$walltime,"exit_code":$rc}
EOF
exit $rc
