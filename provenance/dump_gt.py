"""Dump PIDSMaker's per-attack ground-truth node ids and all node attributes for a dataset.

Usage: python dump_gt.py DATASET DBNAME OUT_DIR
Writes OUT_DIR/attacks.json ({attack: {nids, time_range}}) and OUT_DIR/nodes.parquet
(index_id, kind, path, cmd, remote_ip, remote_port).
"""
import json
import sys
from pathlib import Path

import pandas as pd
import psycopg2

sys.path.insert(0, "/home/user/ext/PIDSMaker")
from pidsmaker.config.pipeline import get_runtime_required_args, get_yml_cfg  # noqa: E402
from pidsmaker.utils.labelling import get_GP_of_each_attack  # noqa: E402


def main(dataset, db, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    sys.argv = ["x", "velox", dataset, "--cpu", "--database_host", "localhost", "--artifact_dir", "/tmp/gt_art/"]
    args, _ = get_runtime_required_args(return_unknown_args=True)
    cfg = get_yml_cfg(args)
    att = get_GP_of_each_attack(cfg)
    (out / "attacks.json").write_text(json.dumps(
        {str(k): {"nids": sorted(v["nids"]), "time_range": [str(x) for x in v["time_range"]]} for k, v in att.items()}))
    con = psycopg2.connect(database=db, host="localhost", user="postgres", password="postgres")
    sub = pd.read_sql("select index_id, path, cmd from subject_node_table", con).assign(kind="process")
    fil = pd.read_sql("select index_id, path from file_node_table", con).assign(kind="file")
    net = pd.read_sql("select index_id, dst_addr as remote_ip, dst_port as remote_port from netflow_node_table", con).assign(kind="netflow")
    nodes = pd.concat([sub, fil, net], ignore_index=True)
    nodes["index_id"] = nodes["index_id"].astype("int64")
    nodes.to_parquet(out / "nodes.parquet", index=False)
    print({k: len(v["nids"]) for k, v in att.items()}, len(nodes))


if __name__ == "__main__":
    main(*sys.argv[1:])
