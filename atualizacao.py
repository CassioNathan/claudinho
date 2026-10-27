"""Versão nova do Claudinho: olha a última release no GitHub (sem login, só leitura) e diz se ela é mais nova que esta.

Não baixa nem instala nada: quem atualiza é a pessoa, pelo link da release. Dá pra desligar no painel (Sistema)."""
import json
import re
import urllib.request

import sistema

REPO = "CassioNathan/claudinho"
API = f"https://api.github.com/repos/{REPO}/releases/latest"


def numero(versao):
    """"v1.10.2" -> (1, 10, 2): pra comparar versão como número, não como texto."""
    return tuple(int(n) for n in re.findall(r"\d+", versao or "")[:3])


def nova():
    """A release mais nova, se for maior que esta: {"versao", "url", "titulo"}; None se não tem ou não deu pra olhar."""
    pedido = urllib.request.Request(API, headers={"Accept": "application/vnd.github+json",
                                                  "User-Agent": f"Claudinho/{sistema.VERSAO}"})
    try:
        with urllib.request.urlopen(pedido, timeout=10) as r:
            release = json.load(r)
    except (OSError, ValueError):
        return None
    versao = str(release.get("tag_name") or "").lstrip("v")
    if release.get("draft") or release.get("prerelease") or numero(versao) <= numero(sistema.VERSAO):
        return None
    return {"versao": versao, "url": release.get("html_url") or f"https://github.com/{REPO}/releases/latest",
            "titulo": release.get("name") or f"Claudinho {versao}"}
