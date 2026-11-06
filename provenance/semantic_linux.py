"""REACH semantic prior for Linux / FreeBSD / Android provenance (DARPA TC format), written before loading any E3 data.

Generic public knowledge only (MITRE ATT&CK Linux techniques and common Sigma Linux rules). Points per process:
  +1 per matching node rule on its path / command line;
  +2 for both ends of a process-creation event where the parent is a network-facing program
     (browser, mail client, web / ssh / ftp server) and the child is a shell, interpreter or downloader;
  +1 for both ends of a process-creation event where the parent is a shell or interpreter and the child is a
     downloader, network or discovery tool.
Disclosure: the DARPA TC E3 attack reports are public and known to the author in outline; no dataset-specific
names (implant names, file names, IPs) are used.
"""
import re

import pandas as pd
import psycopg2

NODE_RULES = [
    (r"(^|/)(tmp|dev/shm|var/tmp)/[^ ]*", "T1059 exec from temp dir"),
    (r"chmod\s+(\+x|[0-7]*7[0-7]*)", "T1222.002"),
    (r"base64\s+(-d|--decode)", "T1140"),
    (r"(wget|curl)\s+[^|]*http", "T1105"),
    (r"(curl|wget)[^|]*\|\s*(ba)?sh", "T1059.004"),
    (r"\b(nc|ncat|netcat|socat)\b.*(-e|-c|exec)", "T1059.004 reverse shell"),
    (r"/etc/(passwd|shadow|sudoers)", "T1003.008"),
    (r"crontab|/etc/cron", "T1053.003"),
    (r"\.ssh/authorized_keys", "T1098.004"),
    (r"\b(whoami|id|uname -a|hostname|ifconfig|ip addr|netstat|ss -)\b", "T1033/T1082/T1016"),
    (r"\b(useradd|adduser|usermod)\b", "T1136.001"),
    (r"\b(scp|sftp)\b", "T1105"),
    (r"insmod|modprobe", "T1547.006"),
    (r"history\s+-c|rm\s+-rf\s+/var/log|unset\s+HISTFILE", "T1070"),
]
NODE_RULES = [(re.compile(p, re.I), t) for p, t in NODE_RULES]
NET_FACING = re.compile(r"(^|/)(firefox|chrome|chromium|thunderbird|nginx|apache2|httpd|lighttpd|sshd|vsftpd|proftpd|"
                        r"sendmail|postfix|dovecot)$", re.I)
SHELLS = re.compile(r"(^|/)(sh|bash|dash|zsh|csh|tcsh|ksh|python[0-9.]*|perl|ruby|php[0-9.]*|lua|node)$", re.I)
TOOLS = re.compile(r"(^|/)(wget|curl|nc|ncat|netcat|socat|ftp|tftp|scp|ssh|whoami|id|uname|ifconfig|ip|netstat|ss|"
                   r"hostname|ps|chmod|chown|crontab|base64|useradd|sudo|su|cat|nmap|telnet)$", re.I)
CREATE_OPS = ("EVENT_FORK", "EVENT_CLONE", "EVENT_EXECUTE")


def basename(p):
    return str(p or "").strip().split(" ")[0]


def semantic_points_linux(db, path_col="path", cmd_col="cmd"):
    con = psycopg2.connect(database=db, host="localhost", user="postgres", password="postgres")
    procs = pd.read_sql(f"select index_id, {path_col} as path, {cmd_col} as cmd from subject_node_table", con)
    procs["index_id"] = procs["index_id"].astype("int64")
    text = procs["path"].fillna("").astype(str) + " " + procs["cmd"].fillna("").astype(str)
    pts = pd.Series(0.0, index=procs["index_id"])
    for p, _t in NODE_RULES:
        pts += text.str.contains(p, regex=True).to_numpy().astype(float)
    ops = ",".join(f"'{o}'" for o in CREATE_OPS)
    ev = pd.read_sql(f"select distinct src_index_id, dst_index_id from event_table where operation in ({ops})", con).astype("int64")
    path = procs.set_index("index_id")["path"].fillna("").astype(str).map(basename)
    ev = ev[ev["src_index_id"].isin(path.index) & ev["dst_index_id"].isin(path.index)]
    par, chi = path.reindex(ev["src_index_id"]).to_numpy(), path.reindex(ev["dst_index_id"]).to_numpy()
    m1 = [bool(NET_FACING.search(a) and (SHELLS.search(b) or TOOLS.search(b))) for a, b in zip(par, chi)]
    m2 = [bool(SHELLS.search(a) and TOOLS.search(b)) for a, b in zip(par, chi)]
    for mask, w in [(m1, 2.0), (m2, 1.0)]:
        sel = ev[pd.Series(mask, index=ev.index, dtype=bool)] if len(ev) else ev  # bug fix: empty mask
        for col in ["src_index_id", "dst_index_id"]:
            pts = pts.add(sel.groupby(col).size().clip(upper=1) * w, fill_value=0)
    con.close()
    return pts
