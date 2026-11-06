"""REACH L2 (development): evidence incidents from event-level surprise, vs. flat top-N node lists.

Input: PIDSMaker edge_scores pickle (test edges: srcnode, dstnode, loss, tw, edge_type, time, *_is_malicious),
attacks.json and nodes.parquet from dump_gt.py.

For an inspection budget B (nodes an analyst must look at):
- flat:     the B nodes with the highest node score (node score = max loss of its edges), as in Velox.
- incident: seeds = top nodes by score; each seed is expanded through edges within +-WINDOW of the seed's
            highest-loss edge, keeping neighbours whose node score is in the top Q of all test nodes, to DEPTH hops;
            seeds are added until the incident nodes reach B.
Metrics per budget: attacks detected (>= 1 ground-truth node of the attack in the set), ground-truth nodes
found, precision. ATT&CK tags (rule-based, on process path / command line) are attached to incident nodes.

Usage: python l2_explain.py EDGE_SCORES_PKL GT_DIR OUT_JSON [WINDOW_MIN Q DEPTH]
"""
import json
import os
import re
import sys
from collections import defaultdict

os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

BUDGETS = [10, 25, 50, 100, 250, 500]

# Deterministic ATT&CK tagging on process path / command line (Windows). Pattern -> technique.
RULES = [
    (r"powershell.*(-enc|-e |encodedcommand|iex|invoke-expression|downloadstring|-nop|bypass)", "T1059.001"),
    (r"\\powershell(_ise)?\.exe", "T1059.001"),
    (r"\\cmd\.exe", "T1059.003"),
    (r"\\mshta\.exe", "T1218.005"),
    (r"\\rundll32\.exe", "T1218.011"),
    (r"\\regsvr32\.exe", "T1218.010"),
    (r"\\(wmic|wmiprvse)\.exe", "T1047"),
    (r"\\schtasks\.exe", "T1053.005"),
    (r"reg(\.exe)? add .*\\run", "T1547.001"),
    (r"certutil.*(urlcache|decode)", "T1105"),
    (r"\\(whoami)\.exe", "T1033"),
    (r"\\(net1?|netstat)\.exe", "T1087"),
    (r"\\(ipconfig|arp|route)\.exe", "T1016"),
    (r"\\systeminfo\.exe", "T1082"),
    (r"\\tasklist\.exe", "T1057"),
    (r"vssadmin.*delete", "T1490"),
    (r"\\psexe(c|svc)", "T1569.002"),
    (r"\\mstsc\.exe", "T1021.001"),
    (r"lsass", "T1003.001"),
    (r"\\(winword|excel|powerpnt|outlook)\.exe", "T1566.001"),
    (r"\\(wscript|cscript)\.exe", "T1059.005"),
    (r"\\bitsadmin\.exe", "T1197"),
]
RULES = [(re.compile(p, re.I), t) for p, t in RULES]


def tags_for(text):
    return sorted({t for p, t in RULES if p.search(text or "")})


def load(edge_pkl, gt_dir):
    e = torch.load(edge_pkl, map_location="cpu")
    att = json.load(open(os.path.join(gt_dir, "attacks.json")))
    nodes = pd.read_parquet(os.path.join(gt_dir, "nodes.parquet")).set_index("index_id")
    return e, att, nodes


def node_scores(e):
    s = pd.concat([e[["srcnode", "loss"]].rename(columns={"srcnode": "n"}),
                   e[["dstnode", "loss"]].rename(columns={"dstnode": "n"})]).groupby("n")["loss"].max()
    return s.sort_values(ascending=False)


def evaluate(selected, att):
    sel = set(selected)
    det = [k for k, v in att.items() if sel & set(v["nids"])]
    gt = set().union(*[set(v["nids"]) for v in att.values()])
    found = sel & gt
    return {"nodes": len(sel), "attacks_detected": len(det), "attacks": len(att),
            "gt_nodes_found": len(found), "gt_nodes": len(gt),
            "precision": len(found) / max(len(sel), 1), "detected_ids": det}


def incidents(e, scores, budget, window_ns, q, depth, cap=None):
    thr = scores.quantile(q)
    hot = set(scores[scores >= thr].index)
    by_node = defaultdict(list)
    for r in e[["srcnode", "dstnode", "loss", "time"]].itertuples(index=False):
        if r.srcnode in hot or r.dstnode in hot:
            by_node[r.srcnode].append((r.dstnode, r.time, r.loss))
            by_node[r.dstnode].append((r.srcnode, r.time, r.loss))
    peak = {}
    for n, lst in by_node.items():
        peak[n] = max(lst, key=lambda x: x[2])[1]
    selected, incs = [], []
    for seed in scores.index:
        if len(selected) >= budget:
            break
        if seed in selected:
            continue
        inc, frontier = {seed}, [seed]
        t0 = peak.get(seed)
        for _ in range(depth):
            nxt = []
            for n in frontier:
                for m, t, _l in by_node.get(n, []):
                    if m in hot and m not in inc and t0 is not None and abs(t - t0) <= window_ns:
                        inc.add(m)
                        nxt.append(m)
            frontier = nxt
        new = [n for n in sorted(inc, key=lambda n: -scores.get(n, 0)) if n not in selected]
        if cap:
            new = new[:cap]  # dev round L2-r3: at most `cap` nodes per incident
        new = new[: budget - len(selected)]
        selected.extend(new)
        incs.append(new)
    return selected, incs


def main(edge_pkl, gt_dir, out, window_min="30", q="0.99", depth="2"):
    e, att, nodes = load(edge_pkl, gt_dir)
    scores = node_scores(e)
    res = {"params": {"window_min": float(window_min), "q": float(q), "depth": int(depth)}, "budgets": {}}
    for b in BUDGETS:
        flat = evaluate(list(scores.index[:b]), att)
        sel, incs = incidents(e, scores, b, float(window_min) * 60e9, float(q), int(depth))
        inc = evaluate(sel, att)
        inc["incidents"] = len(incs)
        res["budgets"][b] = {"flat": flat, "incident": inc}
        print(b, "flat", flat["attacks_detected"], flat["gt_nodes_found"], "| incident", inc["attacks_detected"],
              inc["gt_nodes_found"], "incidents", len(incs), flush=True)
    # tags on the 50-node incident set, for inspection
    sel, incs = incidents(e, scores, 50, float(window_min) * 60e9, float(q), int(depth))
    gt = set().union(*[set(v["nids"]) for v in att.values()])
    res["tagged_incidents_50"] = [[{"node": int(n), "gt": n in gt, "kind": nodes.at[n, "kind"] if n in nodes.index else None,
                                    "text": str(nodes.at[n, "cmd"] if n in nodes.index and pd.notna(nodes.at[n, "cmd"]) else nodes.at[n, "path"] if n in nodes.index else "")[:160],
                                    "tags": tags_for(str(nodes.at[n, "cmd"]) + " " + str(nodes.at[n, "path"])) if n in nodes.index else []}
                                   for n in inc] for inc in incs]
    json.dump(res, open(out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main(*sys.argv[1:])
