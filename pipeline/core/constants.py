
from __future__ import annotations
from .deployment import ENDERECO_EXEMPLO, ORGAO_DOMINIO, ORGAO_SIGLA, ORGAOS_IRMAOS

LABEL_TO_KEY: dict[str, str] = {
    "nome completo de pessoa física, ex: João Silva, Maria de Souza": "pessoa",
    "nome de empresa ou pessoa jurídica, ex: ABC LTDA, Fundação XYZ, Instituto Nacional": "pessoa_juridica",
    f"órgão ou secretaria do governo, ex: {ORGAO_SIGLA}, {ORGAOS_IRMAOS}": "orgao",
    "cargo, função ou título de autoridade, ex: Secretário, Governador do Estado, Superintendente, Presidente, Diretor": "cargo",
    f"endereço de email, ex: fulano@{ORGAO_DOMINIO}": "email",
    "número de CPF, ex: 807.713.433-53": "cpf",
    "número de CNPJ, ex: 46.067.730/0001-00": "cnpj",
    "matrícula de servidor público, ex: 269422X, 124181-8": "matricula",
    "data completa, ex: 10 de janeiro de 2025, 05/02/2025": "data",
    "valor monetário em reais, ex: R$ 3.441,36, R$ 250.000,00": "valor_monetario",
    f"endereço ou logradouro, ex: {ENDERECO_EXEMPLO}": "endereco",
    "número de telefone, ex: (86) 3216-1712": "telefone",
    "número de processo SEI, ex: 00095.000323/2025-58": "numero_processo",
    "número de lei, ex: Lei nº 6.201, Lei Complementar nº 13": "lei",
    "número de decreto, ex: Decreto nº 21.787, Decreto Estadual nº 18.142": "decreto",
    "número de portaria, ex: Portaria nº 123/2025, Portaria GR nº 265": "portaria",
    "número de contrato ou edital, ex: Edital 001/2025, Contrato nº 15/2024": "contrato_edital",
    "objeto ou assunto do documento, ex: progressão funcional, cessão de servidor, enquadramento": "assunto",
    "objeto de licitação ou contrato, ex: prestação de serviços de TI, aquisição de equipamentos": "objeto_licitacao",
    "vigência ou prazo, ex: 12 meses, dois anos, 200 horas, prazo indeterminado": "vigencia",
    f"endereço de website ou URL, ex: http://www.{ORGAO_DOMINIO}": "url",
}

ENTITY_LABELS: list[str] = list(LABEL_TO_KEY.keys())
ENTITY_KEYS: list[str] = list(LABEL_TO_KEY.values())
