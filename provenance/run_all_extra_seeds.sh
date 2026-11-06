#!/bin/bash
# Driver: all test datasets, seeds 1-4. Safe to restart (finished seeds are skipped).
PGB=/home/user/ext/pg17/postgresql-17.11.0-x86_64-unknown-linux-gnu/bin
su postgres -c "$PGB/pg_ctl -D /home/user/ext/pgdata17 status" >/dev/null 2>&1 || \
  su postgres -c "$PGB/pg_ctl -D /home/user/ext/pgdata17 -l /home/user/ext/pgdata17/log.txt start" >/dev/null 2>&1
sleep 3
cd /home/user/stt-gnn-/dep/reach
./run_extra_seeds.sh THEIA_E3 theia_e3 THEIA_E3 1p7HoH5SdMEFi0vkrEtMeG7B-hpw741p6 phase3
./run_extra_seeds.sh CLEARSCOPE_E3 clearscope_e3 CLEARSCOPE_E3 1v8vsgJxv4OPFVxx8UlYvixDq8FpkIqkd phase3
./run_extra_seeds.sh CADETS_E3 cadets_e3 CADETS_E3 1DGcGBhpavNmXTnCDd_s4NWBNh2n4-6nd phase3
./run_extra_seeds.sh optc_h501 optc_501 OPTC_H501 1046BVjpMql1bb5WHr9yQeB6Uq6RpngbM phase2
./run_extra_seeds.sh optc_h051 optc_051 OPTC_H051 1zzwge346AdAdxldykZOai5FtUrIaWc6q phase2
./run_extra_seeds.sh optc_h201 optc_201 OPTC_H201 1OSZXCQrocFSRN7wkPM02p-BqE2WmgdLD phase2
echo ALL_DONE
