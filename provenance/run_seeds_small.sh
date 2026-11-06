#!/bin/bash
# Same as run_seeds.sh but with Velox text-embedding size DIM (default 32) because of the disk limit of the CPU environment.
SYS=$1; DS=$2; SEEDS=$3; DIM=${4:-32}
OUT=/home/user/stt-gnn-/dep/data_raw/reach_runs/${SYS}_emb$DIM/$DS; mkdir -p "$OUT"
cd /home/user/ext/PIDSMaker || exit 1
for s in $SEEDS; do
  A=/home/user/ext/artifacts_${SYS}_${DS}_emb${DIM}_s$s
  TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 python3 pidsmaker/main.py $SYS $DS --cpu --database_host localhost \
     --artifact_dir "$A/" --training.seed $s --featurization.seed $s --featurization.emb_dim $DIM > "$OUT/seed$s.log" 2>&1
  mkdir -p "$OUT/seed$s" && cp -r "$A/evaluation" "$OUT/seed$s/" 2>/dev/null
  find "$OUT/seed$s" -name "*.png" -delete; find "$OUT/seed$s" -name "*.svg" -delete
  # delete the large artifacts only if the evaluation produced edge scores (keep everything after a failure)
  if ls "$OUT/seed$s"/evaluation/*/*/*/precision_recall_dir/edge_scores_*.pkl >/dev/null 2>&1; then
    [ -n "$SYS" ] && [ -n "$DS" ] && rm -rf "/home/user/ext/artifacts_${SYS}_${DS}_emb${DIM}_s$s"
  else
    echo "seed $s: no edge scores, artifacts kept for inspection"
  fi
  echo "seed $s done $(date -u +%H:%M)"
done
