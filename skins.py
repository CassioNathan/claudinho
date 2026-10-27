"""Skins do Claudinho: uma cor de corpo + adereços em camadas (um por espaço) + pacotes prontos.

Nada de sprite novo por combinação: cada adereço é uma lista de pixels (coluna, linha, cor) na mesma grade
do corpo (11x8, linha 0 = topo da cabeça; linhas -2 e -1 ficam acima dela). O desenho do Claudinho já
desloca tudo junto com o pulinho, então os adereços acompanham qualquer pose sozinhos.
O painel (painel.html) desenha a prévia com estes mesmos dados."""
import colorsys

ESPACOS = ["cabeca", "olhos", "rosto", "pescoco", "bracos", "pes"]
NOMES_ESPACOS = {"cabeca": "Cabeça", "olhos": "Olhos", "rosto": "Rosto", "pescoco": "Pescoço", "bracos": "Braços",
                 "pes": "Pés"}

# cor do corpo e dos olhos (corpo escuro pede olho claro)
CORES = {
    "laranja": {"nome": "Clássico", "corpo": "#d97757", "olho": "#1f1e1d"},
    "preto": {"nome": "Dark", "corpo": "#2e2d2b", "olho": "#ece9e1"},
    "roxo": {"nome": "Uva", "corpo": "#8e6cc8", "olho": "#1f1e1d"},
    "limao": {"nome": "Limão", "corpo": "#9ccc3c", "olho": "#1f1e1d"},
    "menta": {"nome": "Menta", "corpo": "#5ec4b0", "olho": "#1f1e1d"},
    "rosa": {"nome": "Chiclete", "corpo": "#e58fb0", "olho": "#1f1e1d"},
    "dourado": {"nome": "Ouro", "corpo": "#d4a72c", "olho": "#1f1e1d"},
    "azul": {"nome": "Oceano", "corpo": "#4f86d9", "olho": "#1f1e1d"},
    "fantasma": {"nome": "Fantasma", "corpo": "#e8e6e1", "olho": "#1f1e1d"},
    "metal": {"nome": "Metal", "corpo": "#7d8590", "olho": "#ff3b30"},  # olho vermelho (combina com o modo Ultron)
    "arco_iris": {"nome": "Arco-íris", "corpo": "#d97757", "olho": "#1f1e1d", "animada": True},
    "peixinho": {"nome": "Peixinho", "corpo": "#f5932b", "olho": "#1f1e1d"},  # laranja de peixinho dourado
}


def cor_do_corpo(cor, t=0):
    """Cor do corpo nesse quadro (o arco-íris vai girando a cor com o tempo)."""
    c = CORES.get(cor) or CORES["laranja"]
    if c.get("animada"):
        r, g, b = colorsys.hsv_to_rgb((t % 120) / 120, 0.55, 0.92)
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
    return c["corpo"]


def _linha(cols, lin, cor):
    return [(c, lin, cor) for c in cols]


ADERECOS = {
    # ---------- cabeça ----------
    "bone": {"nome": "Boné", "frente": "direita", "espaco": "cabeca", "pixels": [
        *_linha(range(2, 9), -1, "#c0392b"), *_linha(range(1, 10), 0, "#c0392b"),
        (10, 0, "#8e2a20"), (11, 0, "#8e2a20"), (5, -1, "#f4efe4")]},
    "gorro_natal": {"nome": "Gorro de Natal", "frente": "esquerda", "espaco": "cabeca", "pixels": [
        *_linha(range(1, 10), 0, "#f4efe4"), *_linha(range(2, 9), -1, "#c0392b"),
        *_linha(range(4, 9), -2, "#c0392b"), (9, -2, "#c0392b"), (10, -1, "#f4efe4")]},
    "coroa": {"nome": "Coroa", "espaco": "cabeca", "pixels": [
        *_linha(range(2, 9), -1, "#e8b923"), (2, -2, "#e8b923"), (5, -2, "#e8b923"), (8, -2, "#e8b923"),
        (5, -1, "#c0392b"), (3, -1, "#3fbf6b"), (7, -1, "#4f86d9")]},
    "capacete": {"nome": "Capacete de obra", "espaco": "cabeca", "pixels": [
        *_linha(range(3, 8), -2, "#f2c94c"), *_linha(range(2, 9), -1, "#f2c94c"),
        *_linha(range(0, 11), 0, "#e0b43a"), (5, -2, "#fff3b0")]},
    "cowboy": {"nome": "Chapéu de cowboy", "espaco": "cabeca", "pixels": [
        *_linha(range(3, 8), -2, "#8b5a2b"), *_linha(range(3, 8), -1, "#5c3a1a"),
        *_linha(range(-1, 12), 0, "#8b5a2b"), (-1, -1, "#8b5a2b"), (11, -1, "#8b5a2b")]},
    "chifres": {"nome": "Chifrinhos", "espaco": "cabeca", "pixels": [
        (2, -1, "#c0392b"), (2, -2, "#e8452c"), (8, -1, "#c0392b"), (8, -2, "#e8452c")]},
    "antena": {"nome": "Antena", "espaco": "cabeca", "pixels": [
        (5, -1, "#9b978d"), (5, -2, "#3fbf6b")], "pisca": (5, -2, "#b6ffcf")},
    "aureola": {"nome": "Auréola", "espaco": "cabeca", "pixels": [
        *_linha(range(3, 8), -2, "#ffd23f"), (2, -2, "#e8b923"), (8, -2, "#e8b923")]},
    "franja_emo": {"nome": "Franja emo", "frente": "esquerda", "espaco": "cabeca", "pixels": [
        *_linha(range(2, 10), -1, "#141414"), *_linha(range(1, 10), 0, "#141414"),
        *_linha(range(1, 6), 1, "#141414"), *_linha(range(1, 5), 2, "#141414"), (1, 3, "#141414"), (2, 3, "#141414"),
        (7, -1, "#e0457b"), (6, 0, "#e0457b"), (5, 1, "#e0457b")]},
    "fone_gamer": {"nome": "Fone gamer", "espaco": "cabeca", "pixels": [
        *_linha(range(1, 10), -1, "#2c2c2c"), (0, 0, "#2c2c2c"), (0, 1, "#2c2c2c"),
        (10, 0, "#2c2c2c"), (10, 1, "#2c2c2c")], "rgb": [(0, 0), (10, 0)]},
    "topete": {"nome": "Topete", "frente": "direita", "espaco": "cabeca", "pixels": [
        *_linha(range(3, 8), -1, "#6b4226"), (4, -2, "#6b4226"), (5, -2, "#6b4226"), (6, -2, "#8a5a36"),
        (7, -2, "#6b4226")]},
    # ---------- olhos (desenhados por cima dos olhos) ----------
    "oculos_escuros": {"nome": "Óculos escuros", "espaco": "olhos", "pixels": [
        *_linha(range(2, 5), 1, "#141414"), *_linha(range(6, 9), 1, "#141414"),
        *_linha(range(2, 5), 2, "#141414"), *_linha(range(6, 9), 2, "#141414"), (5, 1, "#141414"),
        (1, 1, "#141414"), (9, 1, "#141414"), (3, 1, "#5a5a5a"), (7, 1, "#5a5a5a")]},
    "oculos_3d": {"nome": "Óculos 3D", "espaco": "olhos", "pixels": [
        *_linha(range(1, 10), 1, "#f4efe4"), *_linha(range(2, 5), 2, "#e8452c"),
        *_linha(range(6, 9), 2, "#4f86d9"), (1, 2, "#f4efe4"), (5, 2, "#f4efe4"), (9, 2, "#f4efe4")]},
    "viseira": {"nome": "Viseira cyber", "espaco": "olhos", "pixels": [
        *_linha(range(1, 10), 1, "#1fb5c9"), *_linha(range(1, 10), 2, "#127a88")], "varredura": 1},
    "tapa_olho": {"nome": "Tapa-olho", "frente": "esquerda", "espaco": "olhos", "pixels": [
        *_linha(range(2, 5), 1, "#141414"), *_linha(range(2, 5), 2, "#141414"),
        (5, 0, "#141414"), (6, 0, "#141414"), (7, -1 + 1, "#141414"), (1, 1, "#141414")]},
    "monoculo": {"nome": "Monóculo", "frente": "direita", "espaco": "olhos", "pixels": [
        (6, 0, "#e8b923"), (7, 0, "#e8b923"), (8, 0, "#e8b923"), (6, 3, "#e8b923"), (7, 3, "#e8b923"),
        (8, 3, "#e8b923"), (9, 1, "#e8b923"), (9, 2, "#e8b923"), (9, 3, "#e8b923"), (9, 4, "#e8b923")]},
    # olhão de desenho animado: branco em volta e a pupila no meio (anda junto com o olhar, como os óculos)
    "olhos_grandes": {"nome": "Olhões", "espaco": "olhos", "pixels": [
        *[(c, l, "#fbfaf6") for c in (2, 3, 4, 6, 7, 8) for l in (0, 1, 2, 3)],
        (3, 1, "#1f1e1d"), (3, 2, "#1f1e1d"), (7, 1, "#1f1e1d"), (7, 2, "#1f1e1d")]},
    # ---------- rosto ----------
    "bigode": {"nome": "Bigode", "espaco": "rosto", "pixels": [
        *_linha(range(3, 8), 3, "#3b2516"), (2, 4, "#3b2516"), (8, 4, "#3b2516")]},
    "bochechas": {"nome": "Bochechas", "espaco": "rosto", "pixels": [
        (1, 3, "#f08fa0"), (2, 3, "#f08fa0"), (8, 3, "#f08fa0"), (9, 3, "#f08fa0")]},
    "mascara": {"nome": "Máscara", "espaco": "rosto", "pixels": [
        *_linha(range(2, 9), 3, "#dfe6ea"), *_linha(range(2, 9), 4, "#dfe6ea"),
        (1, 3, "#b8c2c8"), (9, 3, "#b8c2c8")]},
    "barba": {"nome": "Barba", "espaco": "rosto", "pixels": [
        *_linha(range(1, 10), 4, "#4a2f1d"), *_linha(range(2, 9), 5, "#4a2f1d"), *_linha(range(4, 7), 3, "#4a2f1d")]},
    "boca_peixe": {"nome": "Boquinha de peixe", "espaco": "rosto", "pixels": [
        (4, 4, "#e2603a"), (5, 4, "#e2603a"), (6, 4, "#e2603a"), (5, 5, "#c94a2a")]},
    # ---------- pescoço ----------
    "gravata": {"nome": "Gravata", "espaco": "pescoco", "pixels": [
        (5, 4, "#2f3f63"), (5, 5, "#2f3f63"), (4, 5, "#2f3f63"), (6, 5, "#2f3f63"), (5, 6, "#2f3f63")]},
    "gravata_borboleta": {"nome": "Gravata-borboleta", "espaco": "pescoco", "pixels": [
        (4, 4, "#c0392b"), (6, 4, "#c0392b"), (5, 4, "#8e2a20"), (3, 4, "#c0392b"), (7, 4, "#c0392b")]},
    "cachecol": {"nome": "Cachecol", "frente": "esquerda", "espaco": "pescoco", "pixels": [
        *[(c, 4, "#c0392b" if c % 2 else "#f4efe4") for c in range(1, 10)], (8, 5, "#c0392b"), (8, 6, "#f4efe4")]},
    "corrente": {"nome": "Corrente de ouro", "espaco": "pescoco", "pixels": [
        (2, 4, "#e8b923"), (3, 5, "#e8b923"), (4, 5, "#e8b923"), (5, 5, "#ffd23f"), (6, 5, "#e8b923"),
        (7, 5, "#e8b923"), (8, 4, "#e8b923")]},
    "bandana": {"nome": "Bandana", "espaco": "pescoco", "pixels": [
        *_linha(range(1, 10), 4, "#c0392b"), *_linha(range(3, 8), 5, "#c0392b"), (5, 6, "#c0392b"), (4, 4, "#f4efe4"),
        (7, 4, "#f4efe4")]},
    # ---------- braços (só aparecem com os bracinhos no lugar) ----------
    "munhequeira": {"nome": "Munhequeira", "espaco": "bracos", "pixels": [(0, 4, "#141414"), (10, 4, "#141414")]},
    "relogio": {"nome": "Relógio", "espaco": "bracos", "pixels": [(10, 4, "#3a3936"), (10, 3, "#7fd6ff")]},
    "pulseira": {"nome": "Pulseiras", "espaco": "bracos", "pixels": [(0, 4, "#e0457b"), (10, 4, "#4f86d9")]},
    "nadadeiras": {"nome": "Nadadeiras", "espaco": "bracos", "pixels": [
        (0, 3, "#ffb866"), (0, 4, "#ffb866"), (-1, 4, "#ffb866"), (10, 3, "#ffb866"), (10, 4, "#ffb866"),
        (11, 4, "#ffb866")]},
    # ---------- pés (pintam o pezinho de cada perna, que sobe e desce andando) ----------
    "tenis": {"nome": "Tênis", "espaco": "pes", "sapato": "#f4efe4", "pixels": []},
    "tenis_verde": {"nome": "Tênis verde", "espaco": "pes", "sapato": "#3fbf6b", "pixels": []},
    "botinha": {"nome": "Botinha", "espaco": "pes", "sapato": "#6b4226", "pixels": []},
}

# pacotes prontos: montam vários espaços de uma vez (None = tira o adereço do espaço)
PACOTES = {
    "emo": {"nome": "Emo 🖤", "aderecos": {"cabeca": "franja_emo", "bracos": "munhequeira"}},
    "ceo": {"nome": "CEO 💼", "aderecos": {"olhos": "oculos_escuros", "pescoco": "gravata", "cabeca": None}},
    "natal": {"nome": "Natal 🎄", "aderecos": {"cabeca": "gorro_natal", "pescoco": "cachecol", "rosto": "bochechas"}},
    "cowboy": {"nome": "Cowboy 🤠", "aderecos": {"cabeca": "cowboy", "rosto": "bigode", "pescoco": "bandana"}},
    "pirata": {"nome": "Pirata 🏴‍☠️", "aderecos": {"olhos": "tapa_olho", "rosto": "barba", "pescoco": "bandana",
                                                   "cabeca": None}},
    "anjinho": {"nome": "Anjinho 😇", "cor": "fantasma", "aderecos": {"cabeca": "aureola", "rosto": "bochechas"}},
    "diabinho": {"nome": "Diabinho 😈", "aderecos": {"cabeca": "chifres", "rosto": None}},
    "gamer": {"nome": "Gamer 🎮", "aderecos": {"cabeca": "fone_gamer", "olhos": "viseira", "bracos": "pulseira"}},
    "ultron": {"nome": "Ultron 🤖", "cor": "metal", "aderecos": {"cabeca": None, "olhos": None, "rosto": None,
                                                                "pescoco": None, "bracos": None}},
    "rei": {"nome": "Rei 👑", "cor": "dourado", "aderecos": {"cabeca": "coroa", "pescoco": "corrente", "olhos": "monoculo"}},
    # o peixinho laranja de olhão e tênis (inspirado no Darwin, de O Incrível Mundo de Gumball)
    "peixinho": {"nome": "Peixinho 🐟", "cor": "peixinho", "aderecos": {
        "cabeca": None, "olhos": "olhos_grandes", "rosto": "boca_peixe", "pescoco": None, "bracos": "nadadeiras",
        "pes": "tenis"}},
}

VISUAL_PADRAO = {"cor": "laranja", "cabeca": None, "olhos": None, "rosto": None, "pescoco": None, "bracos": None,
                 "pes": None}


def cor_do_sapato(visual):
    """Cor do pezinho (o pixel de baixo de cada perna) com o calçado escolhido, ou None descalço."""
    a = ADERECOS.get(visual.get("pes") or "")
    return a.get("sapato") if a else None


def visual_valido(v):
    """Completa o visual salvo e joga fora o que não existe mais (adereço apagado, espaço trocado)."""
    v = dict(VISUAL_PADRAO, **(v or {}))
    if v["cor"] not in CORES:
        v["cor"] = "laranja"
    for e in ESPACOS:
        if v.get(e) and (v[e] not in ADERECOS or ADERECOS[v[e]]["espaco"] != e):
            v[e] = None
    return {k: v[k] for k in VISUAL_PADRAO}


def aplicar_pacote(visual, nome):
    p = PACOTES[nome]
    novo = dict(visual, **p["aderecos"])
    if p.get("cor"):
        novo["cor"] = p["cor"]
    return visual_valido(novo)


FRENTES = {"esquerda": -1, "direita": 1}


# os adereços desses espaços são desenhados com os olhos no meio e andam junto com eles
SEGUEM_OLHOS = ("olhos", "rosto")


def pixels(id_aderecos, t=0, olhando=-1, olhar=(0, 0)):
    """Pixels (col, lin, cor) de um adereço nesse quadro (antena pisca, fone muda de cor, viseira varre).
    Adereço com "frente" (franja, aba do boné, tapa-olho…) espelha pra seguir o lado pra onde ele olha
    (`olhando`: -1 esquerda, 1 direita). Óculos e rosto (bigode, bochechas…) andam com os olhos:
    `olhar` = (x, y) de -1 a 1, o mesmo deslocamento dos olhinhos."""
    a = ADERECOS[id_aderecos]
    lista = list(a["pixels"])
    if a.get("pisca") and t % 10 < 5:
        lista.append(a["pisca"])
    if a.get("rgb"):
        r, g, b = colorsys.hsv_to_rgb((t % 40) / 40, 0.8, 1.0)
        cor = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        lista += [(c, l, cor) for c, l in a["rgb"]]
    if a.get("varredura"):
        lista.append((1 + (t // 2) % 9, a["varredura"], "#b8f6ff"))
    if a.get("frente") and FRENTES[a["frente"]] != olhando:
        lista = [(10 - c, l, cor) for c, l, cor in lista]  # espelha na grade de 11 colunas (0–10)
    if a["espaco"] in SEGUEM_OLHOS and olhar != (0, 0):
        dx, dy = olhar
        lista = [(c + dx, l + dy, cor) for c, l, cor in lista]
    return lista


def itens_vestidos(visual):
    """Nomes dos adereços que ele está usando, em minúsculas (ex.: ['boné', 'óculos escuros'])."""
    return [ADERECOS[visual[e]]["nome"].lower() for e in ESPACOS if visual.get(e) in ADERECOS]


def autorretrato(visual, vendado=False):
    """Como ele está agora, numa frase (vai pro Haiku e pro chat: é assim que ele "se enxerga")."""
    cor = CORES.get(visual.get("cor"), CORES["laranja"])
    partes = [f"corpinho pixelado cor {cor['nome'].lower()}" if visual.get("cor") != "laranja"
              else "corpinho pixelado laranja clássico"]
    itens = itens_vestidos(visual)
    if itens:
        partes.append("usando " + ", ".join(itens))
    if vendado:
        partes.append("com uma faixa nos olhos")
    return ", ".join(partes)


def catalogo():
    """Tudo que o painel precisa pra montar as escolhas e desenhar a prévia (JSON)."""
    return {
        "espacos": [{"id": e, "nome": NOMES_ESPACOS[e]} for e in ESPACOS],
        "cores": [{"id": k, **v} for k, v in CORES.items()],
        "aderecos": [{"id": k, "nome": v["nome"], "espaco": v["espaco"], "pixels": v["pixels"], "frente": v.get("frente"),
                      "pisca": v.get("pisca"), "rgb": v.get("rgb"), "varredura": v.get("varredura"),
                      "sapato": v.get("sapato")}
                     for k, v in ADERECOS.items()],
        "pacotes": [{"id": k, "nome": v["nome"], "aderecos": v["aderecos"], "cor": v.get("cor")}
                    for k, v in PACOTES.items()],
    }
