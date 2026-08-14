from __future__ import annotations

from collections import Counter, defaultdict

_NOISE = {None, -1, "-1"}


def _macro(entry):
    return entry.get("macro") if isinstance(entry, dict) else entry


def _micro(entry):
    return entry.get("micro") if isinstance(entry, dict) else None


def aggregate_catalog(labels: dict, attrs: dict) -> dict[str, dict]:
    members: dict[object, list[str]] = defaultdict(list)
    micros: dict[object, set] = defaultdict(set)
    for pf, entry in labels.items():
        mac = _macro(entry)
        if mac in _NOISE:
            continue
        members[mac].append(pf)
        mic = _micro(entry)
        if mic not in _NOISE:
            micros[mac].add(mic)
    out: dict[str, dict] = {}
    for mac, pfs in members.items():
        concl = 0
        tipo_counts: Counter = Counter()
        for pf in pfs:
            a = attrs.get(pf) or {}
            if a.get("open_units", 1) == 0:
                concl += 1
            t = a.get("tipo")
            if t:
                tipo_counts[t] += 1
        out[str(mac)] = {
            "n": len(pfs), "concl": concl, "micro": len(micros[mac]),
            "tipos": [{"tipo": t[:52], "n": c} for t, c in tipo_counts.most_common(3)],
        }
    return out
