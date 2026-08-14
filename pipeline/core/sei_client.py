from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import httpx

from .config import ConfigError, Settings

log = logging.getLogger(__name__)


DEFAULT_SEI_BASE_URL = "https://api.sei.pi.gov.br/v1"


RETRY_MAX = 3


RETRY_BACKOFF = 2


HTTP_TIMEOUT = 180


def _sei_request(client: httpx.Client, url: str, headers: dict, params: dict) -> httpx.Response:
    for attempt in range(RETRY_MAX):
        try:
            resp = client.get(url, headers=headers, params=params, timeout=HTTP_TIMEOUT)
            return resp
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if attempt < RETRY_MAX - 1:
                wait = RETRY_BACKOFF * (attempt + 1)
                log.warning("Retry %d/%d after %s: %s", attempt + 1, RETRY_MAX, type(e).__name__, e)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("unreachable")


class _DocumentCancelled(Exception):
    pass


class _AccessDenied(Exception):
    pass


def download_document(
    client: httpx.Client,
    token: str,
    id_unidade: str,
    documento_numero: str,
    sei_base_url: str = DEFAULT_SEI_BASE_URL,
) -> dict | None:
    url = f"{sei_base_url}/unidades/{id_unidade}/documentos/baixar"
    headers = {"accept": "application/json", "token": token}
    params = {"protocolo_documento": documento_numero}

    try:
        resp = _sei_request(client, url, headers, params)
    except Exception as e:
        log.error("Request failed for doc %s unidade %s: %s", documento_numero, id_unidade, e)
        return None

    if resp.status_code != 200:
        body = resp.text[:300]
        log.warning(
            "HTTP %d for doc %s unidade %s: %s",
            resp.status_code, documento_numero, id_unidade, body,
        )
        if "foi cancelado" in body:
            raise _DocumentCancelled(f"Documento {documento_numero} foi cancelado")
        if "não possui acesso" in body or "Acesso negado" in body:
            raise _AccessDenied(body)
        return None

    content_disposition = resp.headers.get("content-disposition", "")
    import re
    match = re.search(r'filename="(.+)"', content_disposition)
    filename = match.group(1) if match else f"documento_{documento_numero}.bin"

    return {
        "filename": filename,
        "content": resp.content,
        "tipo": "pdf" if filename.lower().endswith(".pdf") else "html",
    }


def _sort_unidades(
    unidades: list[dict],
    login_orgao: str,
    doc_creator_unidade: dict | None = None,
    success_stats: dict | None = None,
) -> list[dict]:
    login_orgao_prefix = login_orgao + "/"

    def _is_own_orgao(sigla: str) -> bool:
        return sigla == login_orgao or sigla.startswith(login_orgao_prefix)

    own_unidades = [u for u in unidades if _is_own_orgao(u.get("sigla", ""))]

    if doc_creator_unidade and _is_own_orgao(doc_creator_unidade.get("sigla", "")):
        creator_id = str(doc_creator_unidade.get("id_unidade", ""))
        if not any(str(u.get("id_unidade", "")) == creator_id for u in own_unidades):
            own_unidades.append(doc_creator_unidade)

    def _sort_key(u):
        sigla = u.get("sigla", "")
        id_unidade = str(u.get("id_unidade", ""))

        if doc_creator_unidade and id_unidade == str(doc_creator_unidade.get("id_unidade", "")):
            return (0, 0)

        hist_score = -(success_stats.get(sigla, 0)) if success_stats else 0
        return (1, hist_score)

    return sorted(own_unidades, key=_sort_key)


def try_download_with_unidades(
    client: httpx.Client,
    token: str,
    documento_numero: str,
    unidades: list[dict],
    login_orgao: str = "",
    doc_creator_unidade: dict | None = None,
    success_stats: dict | None = None,
    sei_base_url: str = DEFAULT_SEI_BASE_URL,
) -> tuple[dict | None, str | None, str]:
    sorted_unidades = _sort_unidades(unidades, login_orgao, doc_creator_unidade, success_stats)

    tried = []
    for u in sorted_unidades:
        id_unidade = u.get("id_unidade")
        sigla = u.get("sigla", "?")
        if not id_unidade:
            continue
        log.info("  Trying doc %s with unidade %s (id=%s)", documento_numero, sigla, id_unidade)
        try:
            result = download_document(
                client, token, str(id_unidade), documento_numero, sei_base_url=sei_base_url)
        except _DocumentCancelled:
            log.warning("  ✗ Doc %s is CANCELLED — skipping remaining unidades", documento_numero)
            return None, None, "cancelled"
        except _AccessDenied:
            tried.append(sigla)
            continue
        if result is not None:
            log.info("  ✓ Downloaded doc %s via unidade %s", documento_numero, sigla)
            if success_stats is not None:
                success_stats[sigla] = success_stats.get(sigla, 0) + 1
            return result, str(id_unidade), "ok"
        tried.append(sigla)
    log.warning(
        "  ✗ All %d unidades failed for doc %s: %s",
        len(tried), documento_numero, ", ".join(tried),
    )
    return None, None, "failed"


def sei_login(usuario: str, senha: str, orgao: str, sei_base_url: str = DEFAULT_SEI_BASE_URL) -> str:
    url = f"{sei_base_url}/orgaos/usuarios/login"
    with httpx.Client(verify=False) as client:
        for attempt in range(RETRY_MAX):
            try:
                resp = client.post(
                    url,
                    headers={"accept": "application/json", "Content-Type": "application/json"},
                    json={"Usuario": usuario, "Senha": senha, "Orgao": orgao},
                    timeout=30,
                )
                break
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt < RETRY_MAX - 1:
                    log.warning("Login retry %d/%d: %s", attempt + 1, RETRY_MAX, e)
                    time.sleep(RETRY_BACKOFF * (attempt + 1))
                else:
                    log.error("SEI login failed after %d attempts: %s", RETRY_MAX, e)
                    sys.exit(1)

    if resp.status_code == 401:
        log.error("SEI login failed: invalid credentials (usuario=%s, orgao=%s)", usuario, orgao)
        sys.exit(1)
    if resp.status_code != 200:
        log.error("SEI login failed: HTTP %d — %s", resp.status_code, resp.text[:500])
        sys.exit(1)

    data = resp.json()
    token = data.get("Token")
    if not token:
        log.error("SEI login response missing 'Token': %s", list(data.keys()))
        sys.exit(1)

    log.info("SEI login successful (usuario=%s, orgao=%s)", usuario, orgao)
    return token


def resolve_token(args, settings: Settings) -> str:
    token = args.token or settings.sei_token
    if token:
        return token
    usuario = args.usuario or settings.sei_api_user
    senha = args.senha or settings.sei_api_password
    if usuario and senha:
        sei_base_url = settings.sei_base_url or DEFAULT_SEI_BASE_URL
        return sei_login(usuario, senha, args.orgao, sei_base_url=sei_base_url)
    log.error(
        "Authentication required: set SEI_API_USER/SEI_API_PASSWORD (or SEI_TOKEN) "
        "in .env, or pass --flag token=… / --flag usuario=… --flag senha=…"
    )
    sys.exit(1)
