
import argparse
import base64
import json
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from ...core.deployment import ORGAO_DOMINIO, ORGAO_GOVERNO_CURTO

if TYPE_CHECKING:
    import pandas as pd

_HERE = Path(__file__).resolve()
_ROOT = next((p.parent for p in _HERE.parents if p.name == "pipeline"), _HERE.parents[2])
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ...core import parsed_store
from pipeline.cli import add_standard_args, resolve_settings
from ...core.config import Settings
from ...core.logging_setup import configure_logging

_settings = Settings.from_env()
log = configure_logging(__name__)
from .vision import MODEL_TEXTO, _get_client



SPREADSHEET_SYSTEM_PROMPT = (
    f"Você é um assistente de análise documental do {ORGAO_GOVERNO_CURTO}. "
    "Analise os dados da planilha abaixo e produza um resumo textual completo. "
    "Inclua: nome das colunas, quantidade de linhas, valores totais se houver, "
    "principais categorias, datas encontradas, nomes de pessoas/órgãos, e quaisquer valores monetários. "
    "Responda em texto corrido, sem formatação de tabela."
)


MAX_SPREADSHEET_CHARS = 6000


MAX_SPREADSHEET_COLS = 30


def _clean_dataframe(df) -> "pd.DataFrame":

    df = df.dropna(how="all", axis=0)
    df = df.dropna(how="all", axis=1)

    if df.empty:
        return df

    first_row = df.iloc[0]
    if first_row.notna().all() and all(isinstance(v, str) for v in first_row):
        unnamed_cols = sum(1 for c in df.columns if str(c).startswith("Unnamed"))
        if unnamed_cols > len(df.columns) * 0.5:
            df.columns = [str(v).strip() for v in first_row]
            df = df.iloc[1:].reset_index(drop=True)

    df.columns = [str(c).strip()[:60] for c in df.columns]

    df = df.loc[:, ~df.columns.duplicated()]

    if len(df.columns) > MAX_SPREADSHEET_COLS:
        df = df.iloc[:, :MAX_SPREADSHEET_COLS]

    threshold = len(df.columns) * 0.2
    df = df.dropna(thresh=max(int(threshold), 1))

    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].map(lambda x: str(x).strip() if isinstance(x, str) else x)

    return df.reset_index(drop=True)


def _read_spreadsheet(filepath: Path) -> "tuple[list[pd.DataFrame], list[str]]":
    import pandas as pd

    ext = filepath.suffix.lower()
    dfs = []
    names = []

    if ext == ".csv":
        for enc in ("utf-8", "latin-1", "cp1252", "iso-8859-1"):
            try:
                df = pd.read_csv(filepath, encoding=enc, on_bad_lines="skip",
                                 nrows=500, dtype=str)
                dfs.append(df)
                names.append("csv")
                break
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        if not dfs:
            df = pd.read_csv(filepath, encoding="latin-1", on_bad_lines="skip",
                             nrows=500, dtype=str)
            dfs.append(df)
            names.append("csv")
    else:
        try:
            xls = pd.ExcelFile(filepath, engine="openpyxl")
            for sheet_name in xls.sheet_names:
                try:
                    df = pd.read_excel(xls, sheet_name=sheet_name, nrows=500, dtype=str)
                    dfs.append(df)
                    names.append(sheet_name)
                except Exception as e:
                    log.warning("  Sheet '%s' failed: %s", sheet_name, e)
        except Exception as e:
            raise ValueError(f"Não foi possível abrir a planilha: {e}") from e

    return dfs, names


def parse_spreadsheet(filepath: Path, client) -> tuple[str, str]:
    try:
        dfs_raw, sheet_names = _read_spreadsheet(filepath)
    except Exception as e:
        return f"Erro ao ler planilha: {e}", "spreadsheet-error"

    if not dfs_raw:
        return "Planilha vazia ou ilegível.", "spreadsheet-empty"

    all_parts = []
    total_rows = 0

    for df_raw, sheet_name in zip(dfs_raw, sheet_names):
        df = _clean_dataframe(df_raw)
        if df.empty:
            all_parts.append(f"Aba '{sheet_name}': vazia após limpeza.")
            continue

        total_rows += len(df)
        header = (
            f"Aba: {sheet_name}\n"
            f"Colunas ({len(df.columns)}): {', '.join(df.columns)}\n"
            f"Linhas: {len(df)}"
        )

        remaining_budget = MAX_SPREADSHEET_CHARS - sum(len(p) for p in all_parts)
        if remaining_budget < 500:
            all_parts.append(f"Aba '{sheet_name}': {len(df)} linhas (omitida por limite de tamanho)")
            continue

        sample = df.head(80).to_string(index=False, max_colwidth=60)
        if len(sample) > remaining_budget:
            for n in (40, 20, 10, 5):
                sample = df.head(n).to_string(index=False, max_colwidth=60)
                if len(sample) <= remaining_budget:
                    break
            else:
                sample = sample[:remaining_budget] + "\n... (truncado)"

        all_parts.append(f"{header}\n\nDados:\n{sample}")

    spreadsheet_text = f"Planilha: {filepath.name}\n\n" + "\n\n---\n\n".join(all_parts)

    resp = client.chat.completions.create(
        model=MODEL_TEXTO,
        messages=[
            {"role": "system", "content": SPREADSHEET_SYSTEM_PROMPT},
            {"role": "user", "content": spreadsheet_text},
        ],
        temperature=0.3,
        max_tokens=4096,
    )
    llm_summary = resp.choices[0].message.content.strip()

    structure_info = f"Planilha: {filepath.name} | Abas: {len(dfs_raw)} | Total linhas: {total_rows}"
    full_text = structure_info + "\n\n" + llm_summary
    return full_text, f"spreadsheet-llm ({len(dfs_raw)} sheets, {total_rows} rows)"


def parse_docx(filepath: Path) -> tuple[str, str]:
    from docx import Document

    doc = Document(str(filepath))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)
    return text, "docx-extract"
