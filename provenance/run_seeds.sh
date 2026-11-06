#!/bin/bash
# Usage: run_seeds.sh SYSTEM DATASET "SEEDS"   e.g. run_seeds.sh velox ATLASV2_EDR "0 1 2 3 4"
# Runs PIDSMaker on CPU per seed, keeps the log and the evaluation outputs, deletes the other (large) artifacts.
SYS=$1; DS=$2; SEEDS=$3
OUT=/home/user/stt-gnn-/dep/data_raw/reach_runs/$SYS/$DS; mkdir -p $OUT
cd /home/user/ext/PIDSMaker
for s in $SEEDS; do
  A=/home/user/ext/artifacts_${SYS}_${DS}_s$s
  TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 python3 pidsmaker/main.py $SYS $DS --cpu --database_host localhost \
     --artifact_dir $A/ --training.seed $s --featurization.seed $s > $OUT/seed$s.log 2>&1
  mkdir -p $OUT/seed$s && cp -r $A/evaluation $OUT/seed$s/ 2>/dev/null
  find $OUT/seed$s -name "*.png" -delete; find $OUT/seed$s -name "*.svg" -delete
  rm -rf $A
  echo "seed $s done $(date -u +%H:%M)"
done
