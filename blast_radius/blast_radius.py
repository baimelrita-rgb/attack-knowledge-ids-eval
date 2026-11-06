"""REACH L3 on LANL: rank the computers the attacker will compromise next.

For each evaluation day d with new first-compromises:
  known  = computers seen in red-team events before day d (sources and destinations);
  target = computers whose first red-team event (as destination) is on day d and are not known;
  graph  = successful cross-computer LogOn counts of days < d (auth_daily.parquet), recency-weighted;
  rank all computers seen in the graph, excluding `known`.
Methods: random (expected), degree (in-weight), bfs1 (weight of edges from known hosts, ties by degree),
ppr (personalized PageRank seeded uniformly on known hosts), and, when a user-level table is given,
cred (credential exposure, BloodHound-style): users with a session on a known host (logged on to it, or from it)
in days < d are exposed; a candidate's score is the recency-weighted log-count of exposed users' logons to it;
cred_rt additionally treats the red-team accounts seen before day d as exposed.
Metrics: recall@k (k = 10, 50, 100) pooled over days (sum of hits / sum of targets), and mean reciprocal rank.

Usage: python blast_radius.py AUTH_DAILY REDTEAM_GZ FIRST_DAY LAST_DAY OUT_JSON [TAU_DAYS ALPHA USERS_DAILY]
"""
import json
import sys

import numpy as np
import pandas as pd
import scipy.sparse as sp

KS = [10, 50, 100]


def load(auth_path, rt_path):
    a = pd.read_parquet(auth_path)
    r = pd.read_csv(rt_path, names=["t", "user", "src", "dst"])
    r["day"] = (r["t"] - 1) // 86400 + 1
    return a, r


def graph(a, d, tau):
    h = a[a["day"] < d]
    w = np.log1p(h["n"].to_numpy()) * np.exp(-(d - h["day"].to_numpy()) / tau)
    e = pd.DataFrame({"src": h["src"].to_numpy(), "dst": h["dst"].to_numpy(), "w": w}).groupby(["src", "dst"], as_index=False)["w"].sum()
    nodes = pd.Index(sorted(set(e["src"]) | set(e["dst"])))
    return e, nodes


def ppr(e, nodes, seeds, alpha, iters=50):
    idx = {n: i for i, n in enumerate(nodes)}
    s = e["src"].map(idx).to_numpy()
    t = e["dst"].map(idx).to_numpy()
    n = len(nodes)
    # undirected walk: an attacker can move along a logon edge in either direction once credentials are exposed
    rows = np.r_[s, t]
    cols = np.r_[t, s]
    vals = np.r_[e["w"].to_numpy(), e["w"].to_numpy()]
    M = sp.csr_matrix((vals, (rows, cols)), shape=(n, n))
    deg = np.asarray(M.sum(axis=1)).ravel()
    deg[deg == 0] = 1
    P = sp.diags(1 / deg) @ M
    p0 = np.zeros(n)
    for x in seeds:
        if x in idx:
            p0[idx[x]] = 1
    if p0.sum() == 0:
        return pd.Series(0.0, index=nodes)
    p0 /= p0.sum()
    p = p0.copy()
    for _ in range(iters):
        p = (1 - alpha) * (P.T @ p) + alpha * p0
    return pd.Series(p, index=nodes)


def cred_scores(u, r, d, known, cand, tau, use_rt, after_compromise=False):
    h = u[u["day"] < d]
    if after_compromise:
        # dev round L3-r3: a credential is exposed only by a session on a host after that host's first red-team event
        ct = pd.concat([r[["dst", "t"]].rename(columns={"dst": "h"}), r[["src", "t"]].rename(columns={"src": "h"})])
        ct = ct[ct["t"] < (d - 1) * 86400 + 1].groupby("h")["t"].min()
        on = h[h["dst"].isin(ct.index)]
        exposed = set(on.loc[on["last_t"].to_numpy() >= ct.reindex(on["dst"]).to_numpy(), "user"])
    else:
        exposed = set(h.loc[h["dst"].isin(known) | h["src"].isin(known), "user"])
    if use_rt:
        exposed |= set(r.loc[r["day"] < d, "user"].str.split("@").str[0])
    x = h[h["user"].isin(exposed)]
    w = np.log1p(x["n"].to_numpy()) * np.exp(-(d - x["day"].to_numpy()) / tau)
    return pd.Series(w, index=x["dst"].to_numpy()).groupby(level=0).sum().reindex(cand).fillna(0)


def evaluate_day(a, r, d, tau, alpha, u=None):
    known = set(r.loc[r["day"] < d, "src"]) | set(r.loc[r["day"] < d, "dst"])
    first = r.sort_values("t").drop_duplicates("dst")
    target = set(first.loc[first["day"] == d, "dst"]) - known
    if not target:
        return None
    e, nodes = graph(a, d, tau)
    cand = nodes.difference(pd.Index(sorted(known)))
    indeg = e.groupby("dst")["w"].sum().reindex(cand).fillna(0)
    from_known = e[e["src"].isin(known)].groupby("dst")["w"].sum().reindex(cand).fillna(0)
    scores = {
        "degree": indeg,
        "bfs1": from_known + 1e-9 * indeg / (indeg.max() + 1e-12),
        "ppr": ppr(e, nodes, known, alpha).reindex(cand).fillna(0) + 1e-12 * indeg / (indeg.max() + 1e-12),
    }
    if u is not None:
        for name, rt, ac in [("cred", False, False), ("cred_rt", True, False), ("cred_after", False, True)]:
            scores[name] = cred_scores(u, r, d, known, cand, tau, rt, ac) + 1e-9 * indeg / (indeg.max() + 1e-12)
    out = {"day": int(d), "targets": len(target), "targets_in_graph": len(target & set(cand)), "candidates": len(cand)}
    for m, s in scores.items():
        order = s.sort_values(ascending=False).index
        pos = {n: i + 1 for i, n in enumerate(order)}
        ranks = [pos.get(x) for x in target]
        out[m] = {f"hits@{k}": sum(1 for x in ranks if x and x <= k) for k in KS}
        out[m]["rr"] = float(np.mean([1 / x if x else 0 for x in ranks]))
    out["random"] = {f"hits@{k}": len(target & set(cand)) * min(1, k / len(cand)) for k in KS}
    return out


def main(auth_path, rt_path, d0, d1, out, tau="7", alpha="0.15", users_path=""):
    a, r = load(auth_path, rt_path)
    u = pd.read_parquet(users_path) if users_path else None
    days = []
    for d in range(int(d0), int(d1) + 1):
        res = evaluate_day(a, r, d, float(tau), float(alpha), u)
        if res:
            days.append(res)
            print(res, flush=True)
    tot = sum(x["targets"] for x in days)
    summary = {}
    for m in ["random", "degree", "bfs1", "ppr"] + (["cred", "cred_rt", "cred_after"] if u is not None else []):
        summary[m] = {f"recall@{k}": sum(x[m][f"hits@{k}"] for x in days) / tot for k in KS}
        if m != "random":
            summary[m]["mrr"] = float(np.average([x[m]["rr"] for x in days], weights=[x["targets"] for x in days]))
    res = {"days": days, "targets": tot, "params": {"tau": float(tau), "alpha": float(alpha)}, "summary": summary}
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
