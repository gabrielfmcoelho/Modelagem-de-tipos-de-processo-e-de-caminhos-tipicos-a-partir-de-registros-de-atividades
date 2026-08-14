from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from ...core.paths import ROOT


def esc(s) -> str:
    if not isinstance(s, str):
        return "" if s is None else str(s)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("_", r"\_"),
                 ("#", r"\#"), ("$", r"\$"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}")):
        s = s.replace(a, b)
    return s


def num(v, nd=3):
    if v is None:
        return "---"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return f"{v:,}" if isinstance(v, int) else esc(v)


def table(caption, label, spec, header, rows, note=None, small=False, long=False):
    if long:
        out = [f"\\begin{{longtable}}{{{spec}}}",
               f"\\caption{{{caption}}}\\label{{{label}}}\\\\",
               "\\toprule", " & ".join(header) + " \\\\", "\\midrule", "\\endfirsthead",
               "\\toprule", " & ".join(header) + " \\\\", "\\midrule", "\\endhead",
               "\\bottomrule", "\\endfoot"]
        out += [" & ".join(r) + " \\\\" for r in rows]
        out.append("\\end{longtable}")
        return "{\\footnotesize\n" + "\n".join(out) + "\n}\n"
    out = ["\\begin{table}[htbp]", "\\centering",
           f"\\caption{{{caption}}}\\label{{{label}}}"]
    if small:
        out.append("\\footnotesize")
    out += [f"\\begin{{tabular}}{{{spec}}}", "\\toprule",
            " & ".join(header) + " \\\\", "\\midrule"]
    out += [" & ".join(r) + " \\\\" for r in rows]
    out += ["\\bottomrule", "\\end{tabular}"]
    if note:
        out.append(f"\\par\\vspace{{2pt}}\\footnotesize\\raggedright {note}")
    out.append("\\end{table}")
    return "\n".join(out) + "\n"


def t_glossary(f):
    rows = [[f"\\texttt{{{esc(r['metric'])}}}", esc(r["family"]),
             {"↑": "$\\uparrow$", "↓": "$\\downarrow$"}.get(r["direction"], "---"),
             esc(r["definition"])] for r in (f.get("metric_glossary") or [])]
    return table("Measures used in this paper.", "tab:glossary", "llcp{0.52\\textwidth}",
                 ["measure", "category", "better", "definition"], rows, small=True)
