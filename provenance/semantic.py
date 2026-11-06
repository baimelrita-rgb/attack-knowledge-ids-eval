"""REACH semantic prior: generic ATT&CK / Sigma-style knowledge about process behaviour, independent of any dataset.

Fixed before use; sources: MITRE ATT&CK technique descriptions and well-known public Sigma rules
("Suspicious MS Office child process", "Suspicious browser child process", LOLBin execution).
Points per node:
  +1 per matching node rule (l2_explain.RULES) on its path / command line;
  +2 for both ends of a process-creation event where the parent is an Office application, mail client,
     browser or document reader and the child is a script interpreter or LOLBin;
  +1 for both ends of a process-creation event where the parent is a script interpreter and the child is a
     discovery / LOLBin tool.

Usage (library): semantic_points(db, family) -> pd.Series(index_id -> points)
"""
import re

import pandas as pd
import psycopg2

from l2_explain import RULES

DOC_PARENTS = re.compile(r"\\(winword|excel|powerpnt|outlook|msaccess|mspub|onenote|acrord32|acrobat|foxitreader|"
                         r"firefox|plugin-container|chrome|iexplore|msedge|thunderbird)\.exe$", re.I)
INTERPRETERS = re.compile(r"\\(powershell|powershell_ise|pwsh|cmd|mshta|wscript|cscript)\.exe$", re.I)
LOLBINS = re.compile(r"\\(regsvr32|rundll32|certutil|bitsadmin|schtasks|wmic|msiexec|installutil|regasm|regsvcs|"
                     r"msbuild|cmstp|hh|forfiles|whoami|net|net1|ipconfig|systeminfo|tasklist|nltest|netstat|arp|"
                     r"psexec|psexesvc|vssadmin|reg|sc|at)\.exe$", re.I)

# process-creation operations per data format (from the PIDSMaker event tables)
CREATE_OPS = {"edr": ("PROCESS_EXECUTED",), "optc": ("CREATE", "EVENT_CLONE", "EVENT_FORK", "EVENT_EXECUTE")}


def semantic_points(db, family):
    con = psycopg2.connect(database=db, host="localhost", user="postgres", password="postgres")
    procs = pd.read_sql("select index_id, path, cmd from subject_node_table", con)
    procs["index_id"] = procs["index_id"].astype("int64")
    procs["text"] = procs["path"].fillna("") + " " + procs["cmd"].fillna("")
    pts = pd.Series(0.0, index=procs["index_id"])
    for p, _t in RULES:
        pts += procs["text"].str.contains(p, regex=True).to_numpy().astype(float)
    ops = ",".join(f"'{o}'" for o in CREATE_OPS[family])
    ev = pd.read_sql(f"select distinct src_index_id, dst_index_id from event_table where operation in ({ops})", con)
    ev = ev.astype("int64")
    path = procs.set_index("index_id")["path"].fillna("")
    ev = ev[ev["src_index_id"].isin(path.index) & ev["dst_index_id"].isin(path.index)]
    par, chi = path.reindex(ev["src_index_id"]).to_numpy(), path.reindex(ev["dst_index_id"]).to_numpy()
    doc_to_bad = [bool(DOC_PARENTS.search(a) and (INTERPRETERS.search(b) or LOLBINS.search(b))) for a, b in zip(par, chi)]
    int_to_lol = [bool(INTERPRETERS.search(a) and LOLBINS.search(b)) for a, b in zip(par, chi)]
    for mask, w in [(doc_to_bad, 2.0), (int_to_lol, 1.0)]:
        sel = ev[mask]
        for col in ["src_index_id", "dst_index_id"]:
            add = sel.groupby(col).size().clip(upper=1) * w
            pts = pts.add(add, fill_value=0)
    con.close()
    return pts
