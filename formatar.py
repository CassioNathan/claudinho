"""Markdown -> texto de balão. O balão é texto puro: tabela vira lista, título vira destaque e somem os
asteriscos, crases, cercas de código e links feios."""
import re

_SEPARADOR = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def _celulas(linha):
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def _tabela(linhas):
    """| | Antes | Agora |  ->  • Largura: Antes 1024px · Agora 1200px"""
    cab = _celulas(linhas[0])
    saida = []
    for linha in linhas[1:]:
        if _SEPARADOR.match(linha):
            continue
        cel = _celulas(linha)
        rotulo, resto, nomes = cel[0], cel[1:], cab[1:]
        if not cab[0] and rotulo:  # primeira coluna é o nome da linha
            pares = [f"{n}: {v}" if n else v for n, v in zip(nomes, resto) if v]
            saida.append(f"• {rotulo} — " + " · ".join(pares) if pares else f"• {rotulo}")
        else:  # tabela "normal": cada linha vira campo: valor
            pares = [f"{n}: {v}" if n else v for n, v in zip(cab, cel) if v]
            saida.append("• " + " · ".join(pares))
    return saida


def limpar(texto):
    linhas, saida, i = texto.replace("\r\n", "\n").split("\n"), [], 0
    while i < len(linhas):
        linha = linhas[i]
        if linha.strip().startswith("|") and i + 1 < len(linhas) and _SEPARADOR.match(linhas[i + 1]):
            fim = i
            while fim < len(linhas) and linhas[fim].strip().startswith("|"):
                fim += 1
            saida += _tabela(linhas[i:fim])
            i = fim
            continue
        if linha.strip().startswith("```"):  # cerca de código: some a cerca, fica o código
            i += 1
            continue
        if re.fullmatch(r"\s*([-*_])\s*(\1\s*){2,}", linha):  # linha horizontal
            i += 1
            continue
        titulo = re.match(r"\s*#{1,6}\s+(.*)", linha)
        if titulo:
            linha = "▸ " + titulo.group(1)
        else:
            linha = re.sub(r"^(\s*)[-*+]\s+", r"\1• ", linha)  # marcador de lista
            linha = re.sub(r"^\s*>\s?", "", linha)  # citação
        saida.append(linha)
        i += 1
    texto = "\n".join(saida)
    texto = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", texto)  # [texto](link) -> texto
    texto = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: m.group(1) or m.group(2), texto)  # negrito
    texto = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", texto)  # itálico
    texto = texto.replace("`", "")
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()
