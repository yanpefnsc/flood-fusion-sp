from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, List, Optional, Tuple


PREFIXOS_VIARIOS = {
    r"\bAV\b\.?": "AVENIDA",
    r"\bR\b\.?": "RUA",
    r"\bPCA\b\.?": "PRACA",
    r"\bVD\b\.?": "VIADUTO",
    r"\bROD\b\.?": "RODOVIA",
    r"\bESTR\b\.?": "ESTRADA",
    r"\bAL\b\.?": "ALAMEDA",
    r"\bTV\b\.?": "TRAVESSA",
    r"\bLGO\b\.?": "LARGO",
}


def limpar_texto(texto: Any) -> str:
    if texto is None or not isinstance(texto, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", texto.casefold())
    sem_acento = "".join(c for c in decomposed if not unicodedata.combining(c)).upper()
    return re.sub(r"[^\w\s]", " ", sem_acento)


def normalizar_logradouro(nome: Any) -> str:
    if nome is None:
        return ""
    if isinstance(nome, list):
        nome = nome[0] if nome else ""
    elif not isinstance(nome, str):
        nome = str(nome)
        if nome.lower() in ("nan", "none"):
            return ""

    txt = limpar_texto(nome)
    for padrao, sub in PREFIXOS_VIARIOS.items():
        txt = re.sub(padrao, sub, txt)
    return re.sub(r"\s+", " ", txt).strip()


def extrair_nucleo_logradouro(nome_normalizado: str) -> str:
    prefixos = [
        "AVENIDA",
        "RUA",
        "PRACA",
        "VIADUTO",
        "RODOVIA",
        "ESTRADA",
        "ALAMEDA",
        "TRAVESSA",
        "LARGO",
    ]
    tokens = nome_normalizado.split()
    if tokens and tokens[0] in prefixos:
        return " ".join(tokens[1:]).strip()
    return nome_normalizado


def similaridade_string(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def melhor_correspondencia(
    alvo: str, candidatos: List[str], limiar: float = 0.70
) -> Tuple[Optional[str], float]:
    alvo_norm = normalizar_logradouro(alvo)
    alvo_nucleo = extrair_nucleo_logradouro(alvo_norm)
    
    melhor_cand = None
    maior_score = 0.0

    for cand in candidatos:
        cand_norm = normalizar_logradouro(cand)
        cand_nucleo = extrair_nucleo_logradouro(cand_norm)

        if alvo_norm == cand_norm:
            return cand, 1.0

        if alvo_nucleo and alvo_nucleo == cand_nucleo:
            return cand, 0.95

        score_completo = similaridade_string(alvo_norm, cand_norm)
        score_nucleo = similaridade_string(alvo_nucleo, cand_nucleo) if alvo_nucleo and cand_nucleo else 0.0
        score = max(score_completo, score_nucleo)

        if score > maior_score:
            maior_score = score
            melhor_cand = cand

    if maior_score >= limiar:
        return melhor_cand, maior_score

    return None, 0.0