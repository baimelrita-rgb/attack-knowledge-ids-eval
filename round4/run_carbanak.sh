#!/bin/bash
# A1 (PLAN_ROUND4.md): Velox-lite seeds 0-4 on CARBANAKv2 + Phase-2 fusion evaluation. Keeps the database for A3.
PGB=/home/user/ext/pg17/postgresql-17.11.0-x86_64-unknown-linux-gnu/bin
DB=carbanakv2_edr; KEY=CARBANAKV2_EDR; ID=1rJN9F8JkmqMAV9zUjralcFB5wykAgLnd
R=/home/user/stt-gnn-/dep/data_raw/reach_runs/velox_lite/$KEY; G=/home/user/stt-gnn-/dep/data_raw/reach_gt/$KEY
export NLTK_ALLOW_PROXIED_URLOPEN=1; mkdir -p $R
cd /home/user/stt-gnn-/dep/reach
if ! su postgres -c "$PGB/psql -At -c \"select 1 from pg_database where datname='$DB'\"" | grep -q 1; then
  D=/home/user/stt-gnn-/dep/data_raw/pidsmaker/$DB.dump
  for i in 1 2 3; do
    curl -sS -L --max-time 5000 "https://drive.usercontent.google.com/download?id=$ID&export=download&confirm=t" -o $D
    head -c 5 $D | grep -q PGDMP && break; sleep 60
  done
  head -c 5 $D | grep -q PGDMP || { echo "download failed"; exit 1; }
  echo "downloaded $(du -h $D | cut -f1) $(date -u +%H:%M)"
  chmod 644 $D
  su postgres -c "$PGB/psql -q -c 'CREATE DATABASE $DB;'"
  su postgres -c "$PGB/pg_restore -d $DB -j 2 --no-owner $D" 2>&1 | tail -1
  rm -f $D; echo "restored $(date -u +%H:%M)"
fi
for s in 0 1 2 3 4; do
  [ -f $R/seed$s/eval.json ] && continue
  python3 velox_lite.py $KEY $DB $R/seed$s $s > $R/seed$s.log 2>&1 || { echo "seed $s failed"; continue; }
  python3 eval_ranking.py $R/seed$s/node_scores.parquet $G $R/seed$s/eval.json 0.1 > /dev/null 2>&1
  echo "seed $s done $(date -u +%H:%M)"
done
echo ALLDONE
