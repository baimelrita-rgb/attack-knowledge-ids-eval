#!/bin/bash
# Usage: run_extra_seeds.sh KEY DB GT_NAME DUMP_ID MODE   (MODE: phase2|phase3)
# Restores the dump if the database is missing, runs Velox-lite seeds 1-4, evaluates each, then drops the database.
KEY=$1; DB=$2; GT=$3; DUMP_ID=$4; MODE=$5
PGB=/home/user/ext/pg17/postgresql-17.11.0-x86_64-unknown-linux-gnu/bin
R=/home/user/stt-gnn-/dep/data_raw/reach_runs/velox_lite/$GT
G=/home/user/stt-gnn-/dep/data_raw/reach_gt/$GT
export NLTK_ALLOW_PROXIED_URLOPEN=1
cd /home/user/stt-gnn-/dep/reach
if ! su postgres -c "$PGB/psql -At -c \"select 1 from pg_database where datname='$DB'\"" | grep -q 1; then
  D=/home/user/stt-gnn-/dep/data_raw/pidsmaker/$DB.dump
  for i in 1 2 3; do
    curl -sS -L --max-time 3000 "https://drive.usercontent.google.com/download?id=$DUMP_ID&export=download&confirm=t" -o $D
    head -c 5 $D | grep -q PGDMP && break
    sleep 60
  done
  head -c 5 $D | grep -q PGDMP || { echo "$DB: dump download failed"; exit 1; }
  chmod 644 $D
  su postgres -c "$PGB/psql -q -c 'CREATE DATABASE $DB;'"
  su postgres -c "$PGB/pg_restore -d $DB -j 2 --no-owner $D" 2>&1 | tail -1
  rm -f $D
fi
for s in 1 2 3 4; do
  [ -f $R/seed$s/node_scores.parquet ] && continue
  python3 velox_lite.py $KEY $DB $R/seed$s $s > $R/seed$s.log 2>&1 || { echo "$GT seed $s failed"; continue; }
  if [ "$MODE" = phase2 ]; then python3 eval_ranking.py $R/seed$s/node_scores.parquet $G $R/seed$s/eval.json 0.1 > /dev/null 2>&1
  else python3 eval_phase3.py $R/seed$s/node_scores.parquet $G $R/seed$s/eval_phase3.json > /dev/null 2>&1; fi
  echo "$GT seed $s done $(date -u +%H:%M)"
done
su postgres -c "$PGB/psql -q -c 'DROP DATABASE $DB;'"
