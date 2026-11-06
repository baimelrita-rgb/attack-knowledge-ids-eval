"""Generates appendix_generated.tex (splits, hyperparameters, rules, figure values) from the code and result files."""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/ext/PIDSMaker")
sys.path.insert(0, "/home/user/stt-gnn-/dep/reach")
from pidsmaker.config.config import DATASET_DEFAULT_CONFIG as C  # noqa: E402
import l2_explain  # noqa: E402
import semantic_linux  # noqa: E402

R = "/home/user/stt-gnn-/dep/data_raw/reach_runs"


def fmt(l):
    if len(l) == 1:
        return l[0]
    end = l[-1][len(l[0][:8]):] if l[0][:8] == l[-1][:8] else l[-1]
    return f"{l[0]} -- {end} ({len(l)}\\,d)"


rows = []
for name, key in [("ATLASv2-EDR", "ATLASV2_EDR"), ("CARBANAKv2-EDR", "CARBANAKV2_EDR"), ("OpTC h501", "optc_h501"),
                  ("OpTC h051", "optc_h051"), ("OpTC h201", "optc_h201"), ("CLEARSCOPE E3", "CLEARSCOPE_E3"),
                  ("CADETS E3", "CADETS_E3"), ("THEIA E3", "THEIA_E3")]:
    d = C[key]
    rows.append(f"{name} & {fmt(d['train_dates'])} & {fmt(d['val_dates'])} & {fmt(d['test_dates'])} \\\\")
splits_prov = "\n".join(rows)

panels = [("ATLASv2 (dev)", f"{R}/v2dev/atlas.json", ["velox", "knowledge", "fused_sum", "interleave"]),
          ("OpTC h501", f"{R}/v2dev/h501.json", ["velox", "knowledge", "fused_sum", "interleave"]),
          ("OpTC h051", f"{R}/v2dev/h051.json", ["velox", "knowledge", "fused_sum", "interleave"]),
          ("OpTC h201", f"{R}/v2dev/h201.json", ["velox", "knowledge", "fused_sum", "interleave"]),
          ("CADETS E3", f"{R}/velox_lite/CADETS_E3/seed0/eval_phase3.json", ["velox", "knowledge", "sum", "interleave"]),
          ("THEIA E3", f"{R}/velox_lite/THEIA_E3/seed0/eval_phase3.json", ["velox", "knowledge", "sum", "interleave"]),
          ("CLEARSCOPE E3", f"{R}/velox_lite/CLEARSCOPE_E3/seed0/eval_phase3.json", ["velox", "knowledge", "sum", "interleave"])]
lines = []
for name, path, ks in panels:
    r = json.load(open(path))
    for i, k in enumerate(ks):
        vals = " & ".join(str(r[k][f"gt@{b}"]) for b in [10, 25, 50, 100, 250, 500])
        lines.append(f"{name if i == 0 else ''} & {['Learned', 'Knowledge', 'Sum', 'Interleave'][i]} & {vals} \\\\")
    lines.append("\\midrule")
fig_rows = "\n".join(lines[:-1])


def esc(t):
    for a, b in [("\\", "\\textbackslash{}"), ("_", "\\_"), ("&", "\\&"), ("%", "\\%"), ("#", "\\#"), ("{", "\\{"),
                 ("}", "\\}"), ("^", "\\^{}"), ("$", "\\$"), ("~", "\\~{}")]:
        t = t.replace(a, b)
    for ch in "|()*+?/.-,":
        t = t.replace(ch, ch + "\\allowbreak{}")
    return t


def listing(pairs):
    return "\n".join(f"\\item \\texttt{{{esc(p.pattern)}}} $\\rightarrow$ {esc(t)}" for p, t in pairs)


tex = Path(__file__).with_name("appendix_template.tex").read_text()
tex = (tex.replace("%%SPLITS_PROV%%", splits_prov).replace("%%FIG_ROWS%%", fig_rows)
       .replace("%%WIN_RULES%%", listing(l2_explain.RULES)).replace("%%LIN_RULES%%", listing(semantic_linux.NODE_RULES)))
Path(__file__).with_name("appendix_generated.tex").write_text(tex)
print(len(l2_explain.RULES), "windows rules;", len(semantic_linux.NODE_RULES), "linux rules")
