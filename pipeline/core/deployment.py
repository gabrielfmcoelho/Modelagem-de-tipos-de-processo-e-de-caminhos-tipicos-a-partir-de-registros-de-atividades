from __future__ import annotations

import os

ORGAO_SIGLA = os.getenv("PIPELINE_ORGAO_SIGLA", "SEAD-PI")
ORGAO_SUFIXO = os.getenv("PIPELINE_ORGAO_SUFIXO", "SEAD")
ORGAO_GOVERNO = os.getenv("PIPELINE_ORGAO_GOVERNO", "governo do Estado do Piauí")
ORGAO_GOVERNO_CURTO = os.getenv("PIPELINE_ORGAO_GOVERNO_CURTO", "governo do Piauí")
ORGAO_DOMINIO = os.getenv("PIPELINE_ORGAO_DOMINIO", "sead.pi.gov.br")
ORGAOS_IRMAOS = os.getenv("PIPELINE_ORGAOS_IRMAOS", "SEJUS, Tribunal de Justiça")
ORGAOS_ACRONIMOS = os.getenv("PIPELINE_ORGAOS_ACRONIMOS", "TJPI, TCU, SEAD")
TRIBUNAL_EXEMPLO = os.getenv(
    "PIPELINE_TRIBUNAL_EXEMPLO", "Tribunal de Justiça do Estado do Piauí (TJPI)")
ENDERECO_EXEMPLO = os.getenv(
    "PIPELINE_ENDERECO_EXEMPLO", "Av. Pedro Freitas, Bairro São Pedro, Teresina/PI")
