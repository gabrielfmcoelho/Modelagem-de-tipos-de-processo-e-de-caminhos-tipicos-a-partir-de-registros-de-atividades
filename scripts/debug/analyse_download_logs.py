
import argparse
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


RE_PROCESSO_SUMMARY = re.compile(
    r"\[(\d+)/(\d+)\] Processo (.+?): "
    r"(\d+) downloaded, (\d+) failed, (\d+) cancelled, (\d+) skipped"
)

RE_DOWNLOADED = re.compile(r"Downloaded doc (\S+) via unidade (.+)")

RE_CANCELLED = re.compile(r"Doc (\S+) is CANCELLED")

RE_ALL_FAILED = re.compile(r"All (\d+) unidades failed for doc (\S+): (.+)")

RE_HTTP_ERROR = re.compile(
    r"HTTP (\d+) for doc (\S+) unidade (\S+): (.+)"
)

RE_TRYING = re.compile(r"Trying doc (\S+) with unidade (.+?) \(id=(\S+)\)")

RE_HTTP_200 = re.compile(r'HTTP Request: .+ "HTTP/1\.1 200 OK"')
RE_HTTP_422 = re.compile(r'HTTP Request: .+ "HTTP/1\.1 422')

RE_TIMESTAMP = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")

RE_CANCELADO = re.compile(r"foi cancelado")
RE_ACESSO_NEGADO = re.compile(r"Acesso negado")
RE_NAO_POSSUI = re.compile(r"não possui acesso")



def _bar(value, max_val, width=25):
    if max_val == 0:
        return ""
    filled = int(value / max_val * width)
    return "█" * filled + "░" * (width - filled)


def _sec(title):
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}")



def analyse(logfile: Path, top: int):
    if not logfile.exists():
        print(f"File not found: {logfile}")
        sys.exit(1)

    lines = logfile.read_text(encoding="utf-8", errors="replace").splitlines()

    processos_completed = []
    total_processos_expected = 0

    downloaded_via = Counter()
    downloaded_docs = set()

    cancelled_docs = set()

    all_failed_docs = []

    http_200_count = 0
    http_422_count = 0

    error_types = Counter()

    attempts_per_doc = Counter()

    timestamps = []

    failed_unidades = Counter()

    for line in lines:
        ts_match = RE_TIMESTAMP.match(line)
        if ts_match:
            try:
                timestamps.append(datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M:%S"))
            except ValueError:
                pass

        m = RE_PROCESSO_SUMMARY.search(line)
        if m:
            _idx, total, protocolo = int(m.group(1)), int(m.group(2)), m.group(3)
            dl, fl, cn, sk = int(m.group(4)), int(m.group(5)), int(m.group(6)), int(m.group(7))
            processos_completed.append((protocolo, dl, fl, cn, sk))
            total_processos_expected = total
            continue

        m = RE_DOWNLOADED.search(line)
        if m:
            doc_id, unidade = m.group(1), m.group(2)
            downloaded_via[unidade] += 1
            downloaded_docs.add(doc_id)
            continue

        m = RE_CANCELLED.search(line)
        if m:
            cancelled_docs.add(m.group(1))
            continue

        m = RE_ALL_FAILED.search(line)
        if m:
            n_unidades, doc_id, unidades_str = int(m.group(1)), m.group(2), m.group(3)
            all_failed_docs.append((doc_id, n_unidades, unidades_str))
            continue

        m = RE_HTTP_ERROR.search(line)
        if m:
            status, doc_id, unidade_id, body = m.group(1), m.group(2), m.group(3), m.group(4)
            if RE_CANCELADO.search(body):
                error_types["cancelado"] += 1
            elif RE_ACESSO_NEGADO.search(body):
                error_types["acesso_negado"] += 1
                failed_unidades[unidade_id] += 1
            elif RE_NAO_POSSUI.search(body):
                error_types["nao_possui_acesso"] += 1
                failed_unidades[unidade_id] += 1
            else:
                error_types["other"] += 1
            continue

        m = RE_TRYING.search(line)
        if m:
            doc_id = m.group(1)
            attempts_per_doc[doc_id] += 1
            continue

        if RE_HTTP_200.search(line):
            http_200_count += 1
        elif RE_HTTP_422.search(line):
            http_422_count += 1


    total_downloaded = sum(p[1] for p in processos_completed)
    total_failed = sum(p[2] for p in processos_completed)
    total_cancelled = sum(p[3] for p in processos_completed)
    total_skipped = sum(p[4] for p in processos_completed)
    total_docs_attempted = total_downloaded + total_failed + total_cancelled + total_skipped


    print(f"\n{'=' * 70}")
    print(f"  DOWNLOAD LOG ANALYSIS: {logfile.name}")
    print(f"{'=' * 70}")

    _sec("TIME RANGE")
    if timestamps:
        t_start, t_end = timestamps[0], timestamps[-1]
        duration = t_end - t_start
        print(f"  Start:       {t_start}")
        print(f"  End:         {t_end}")
        print(f"  Duration:    {duration}")
        if duration.total_seconds() > 0:
            rate = total_downloaded / (duration.total_seconds() / 60)
            print(f"  Throughput:  {rate:.1f} docs/min downloaded")
    print(f"  Log lines:   {len(lines):,}")

    _sec("OVERALL RESULTS")
    print(f"  Processos completed:  {len(processos_completed):,} / {total_processos_expected:,}")
    print(f"  Processos pending:    {total_processos_expected - len(processos_completed):,}")
    print()
    print(f"  Documents attempted:  {total_docs_attempted:,}")
    print(f"    Downloaded:         {total_downloaded:>8,}  ({_pct(total_downloaded, total_docs_attempted)})")
    print(f"    Failed:             {total_failed:>8,}  ({_pct(total_failed, total_docs_attempted)})")
    print(f"    Cancelled:          {total_cancelled:>8,}  ({_pct(total_cancelled, total_docs_attempted)})")
    print(f"    Skipped (on disk):  {total_skipped:>8,}  ({_pct(total_skipped, total_docs_attempted)})")

    _sec("HTTP REQUESTS")
    total_http = http_200_count + http_422_count
    print(f"  Total requests:   {total_http:,}")
    print(f"    200 OK:         {http_200_count:>8,}  ({_pct(http_200_count, total_http)})")
    print(f"    422 Error:      {http_422_count:>8,}  ({_pct(http_422_count, total_http)})")
    if total_http > 0 and timestamps:
        req_rate = total_http / (duration.total_seconds() / 60)
        print(f"  Request rate:     {req_rate:.1f} req/min")

    _sec("ERROR TYPE BREAKDOWN (422 responses)")
    total_errors = sum(error_types.values())
    for etype, count in error_types.most_common():
        label = {
            "acesso_negado": "Acesso negado a este recurso",
            "nao_possui_acesso": "Unidade não possui acesso ao documento",
            "cancelado": "Documento foi cancelado",
            "other": "Other errors",
        }.get(etype, etype)
        print(f"    {count:>8,}  ({_pct(count, total_errors)})  {label}")

    _sec(f"CANCELLED DOCUMENTS ({len(cancelled_docs)})")
    if cancelled_docs:
        for doc in sorted(cancelled_docs)[:top]:
            print(f"    {doc}")
        if len(cancelled_docs) > top:
            print(f"    ... and {len(cancelled_docs) - top} more")

    _sec(f"DOCUMENTS THAT FAILED ALL UNIDADES ({len(all_failed_docs)})")
    if all_failed_docs:
        for doc_id, n_unidades, _unidades_str in sorted(all_failed_docs, key=lambda x: -x[1])[:top]:
            print(f"    doc {doc_id}  ({n_unidades} unidades tried)")
        if len(all_failed_docs) > top:
            print(f"    ... and {len(all_failed_docs) - top} more")

    _sec(f"DOCUMENTS WITH MOST RETRY ATTEMPTS (TOP {top})")
    for doc_id, attempts in attempts_per_doc.most_common(top):
        status = "✓" if doc_id in downloaded_docs else ("✗ cancelled" if doc_id in cancelled_docs else "✗ failed")
        print(f"    {attempts:>4} attempts  {status:<14}  {doc_id}")

    _sec(f"UNIDADES THAT RESOLVED DOWNLOADS (TOP {top})")
    if downloaded_via:
        max_count = downloaded_via.most_common(1)[0][1]
        for unidade, count in downloaded_via.most_common(top):
            print(f"    {count:>6,}  {_bar(count, max_count)}  {unidade}")

    failed_processos = [(p, f + c) for p, d, f, c, s in processos_completed if f + c > 0]
    failed_processos.sort(key=lambda x: -x[1])
    _sec(f"PROCESSOS WITH MOST FAILURES+CANCELLATIONS (TOP {top})")
    if failed_processos:
        for protocolo, total_fail in failed_processos[:top]:
            dl = next(d for p, d, f, c, s in processos_completed if p == protocolo)
            print(f"    {total_fail:>4} failed/cancelled, {dl:>4} downloaded  {protocolo}")

    _sec("PER-PROCESSO DISTRIBUTION")
    if processos_completed:
        downloads = [p[1] for p in processos_completed]
        print("  Documents downloaded per processo:")
        print(f"    Min:     {min(downloads)}")
        print(f"    Max:     {max(downloads)}")
        print(f"    Avg:     {sum(downloads) / len(downloads):.1f}")
        print(f"    Median:  {sorted(downloads)[len(downloads) // 2]}")

        buckets = Counter()
        for d in downloads:
            if d == 0:
                buckets["0"] += 1
            elif d <= 5:
                buckets["1-5"] += 1
            elif d <= 10:
                buckets["6-10"] += 1
            elif d <= 20:
                buckets["11-20"] += 1
            elif d <= 50:
                buckets["21-50"] += 1
            else:
                buckets["51+"] += 1
        max_b = max(buckets.values()) if buckets else 1
        print("\n  Histogram (docs downloaded per processo):")
        for label in ["0", "1-5", "6-10", "11-20", "21-50", "51+"]:
            val = buckets.get(label, 0)
            print(f"    {label:>6}  {val:>6,}  {_bar(val, max_b)}")

    _sec("SUCCESS RATE SUMMARY")
    success_rate_docs = _pct(total_downloaded, total_downloaded + total_failed)
    success_rate_with_cancelled = _pct(total_downloaded, total_docs_attempted - total_skipped)
    print(f"  Download success rate (excl. skipped & cancelled): {success_rate_docs}")
    print(f"  Download success rate (excl. skipped only):        {success_rate_with_cancelled}")
    print(f"  Unique documents downloaded: {len(downloaded_docs):,}")
    print(f"  Unique documents cancelled:  {len(cancelled_docs):,}")

    print(f"\n{'=' * 70}\n")


def _pct(part, total):
    if total == 0:
        return "—"
    return f"{part / total * 100:.1f}%"


def main():
    parser = argparse.ArgumentParser(description="Analyse download_documentos_sead.py log files")
    parser.add_argument("logfile", help="Path to the log file")
    parser.add_argument("--top", type=int, default=15, help="Items to show in rankings (default: 15)")
    args = parser.parse_args()

    analyse(Path(args.logfile), args.top)


if __name__ == "__main__":
    main()
