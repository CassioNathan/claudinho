"""Abas do navegador pela extensão: listar, achar pelo nome ("a aba da Strandberg") e trocar ou fechar.

Antes o chat tirava print da tela e ia apertando Ctrl+Tab às cegas até achar a aba (dezenas de prints, caro e
lento). A extensão sabe o título e o site de cada aba: basta escolher pelo nome.
"""
import difflib

import musica

PALAVRAS_FRACAS = {"a", "o", "do", "da", "de", "aba", "guia", "video", "site", "pagina", "essa", "esta", "que", "tem"}


def listar():
    """[{id, titulo, site, ativa, tocando}] ou None se a extensão não respondeu."""
    r = musica.consultar_ext("navegador", {"modo": "abas"}, espera=6)
    dados = r.get("dados") if isinstance(r, dict) and r.get("ok") else None
    return [a for a in dados if isinstance(a, dict) and "id" in a] if isinstance(dados, list) else None


def _palavras(texto):
    import comandos
    return [p for p in comandos.normalizar(texto).split() if p not in PALAVRAS_FRACAS]


def pontuar(pedido, aba):
    """0 a 1: o quanto a aba parece com o que foi pedido (título e site, aceitando erro de escuta)."""
    alvo = _palavras(pedido)
    if not alvo:
        return 0.0
    texto = _palavras(f"{aba.get('titulo', '')} {aba.get('site', '').replace('www.', '').replace('.com', '')}")
    if not texto:
        return 0.0
    total = 0.0
    for p in alvo:
        total += max(difflib.SequenceMatcher(None, p, t).ratio() for t in texto)
    return total / len(alvo)


def achar(pedido, lista, minimo=0.72):
    """A aba que mais parece com o pedido (prefere a que está tocando e a não ativa, pra "volta pro YouTube"
    trazer a outra), ou None."""
    if not lista:
        return None
    notas = sorted(((pontuar(pedido, a) + (0.05 if a.get("tocando") else 0) - (0.02 if a.get("ativa") else 0), a)
                    for a in lista), key=lambda t: -t[0])
    return notas[0][1] if notas[0][0] >= minimo else None


def ir(pedido):
    """Traz pra frente a aba pedida. Devolve (ok, frase)."""
    lista = listar()
    if lista is None:
        return False, "a extensão do navegador não respondeu"
    aba = achar(pedido, lista)
    if not aba:
        return False, f"não achei aba parecida com \"{pedido}\""
    musica.pela_extensao("navegador", {"acao": "aba", "qual": "focar", "id": aba["id"]})
    return True, f"Fui pra aba {aba['titulo'][:60] or aba['site']}."


def fechar(pedido=""):
    """Fecha a aba pedida (sem nome: a que está na frente). Devolve (ok, frase)."""
    if not pedido.strip():
        musica.pela_extensao("navegador", {"acao": "aba", "qual": "fechar", "id": "ativa"})
        return True, "Fechei."
    lista = listar()
    if lista is None:
        return False, "a extensão do navegador não respondeu"
    aba = achar(pedido, lista)
    if not aba:
        return False, f"não achei aba parecida com \"{pedido}\""
    musica.pela_extensao("navegador", {"acao": "aba", "qual": "fechar", "id": aba["id"]})
    return True, f"Fechei a aba {aba['titulo'][:60] or aba['site']}."


def texto():
    """A lista em texto pro chat (ferramenta do MCP)."""
    lista = listar()
    if lista is None:
        return "a extensão do navegador não respondeu (está instalada e o navegador aberto?)"
    linhas = [f"[{a['id']}] {a.get('titulo', '')[:90]} — {a.get('site', '')}"
              + (" (na frente)" if a.get("ativa") else "") + (" (tocando)" if a.get("tocando") else "") for a in lista]
    return "\n".join(linhas) or "nenhuma aba aberta"
