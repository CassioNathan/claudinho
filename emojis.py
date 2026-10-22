"""Pacote de reações do Claudinho: emojis em pixel art (9x9) que sobem flutuando do lado dele.

Cada emoji tem quadros (a animação troca entre eles), uma paleta e frases curtas que às vezes
aparecem junto. `escolher` sorteia um combinando com o que você está fazendo no PC.
Pra criar um novo: desenhe os quadros com uma letra por cor e ponha a letra na paleta.
"""
import random
import time

EMOJIS = {
    "cafe": {
        "quadros": [
            ["..s..s...", "...s..s..", "..s..s...", "wwwwwww..", "wcccccwww", "wcccccw.w", "wcccccwww", ".wwwww...", "........."],
            ["...s..s..", "..s..s...", "...s..s..", "wwwwwww..", "wcccccwww", "wcccccw.w", "wcccccwww", ".wwwww...", "........."],
        ],
        "cores": {"s": "#cfcac0", "w": "#f2efe8", "c": "#7a4a26"},
        "frases": ["hora do café?", "um cafezinho caía bem", "recarregando…"],
    },
    "bug": {
        "quadros": [
            ["..a...a..", "...a.a...", "..ggggg..", "l.gkgkg.l", ".lgggggl.", "l.ggggg.l", ".lgggggl.", "...ggg...", "........."],
            ["..a...a..", "...a.a...", "..ggggg..", ".lgkgkgl.", "l.ggggg.l", ".lgggggl.", "l.ggggg.l", "...ggg...", "........."],
        ],
        "cores": {"a": "#2b2a28", "g": "#5fb34a", "k": "#1f1e1d", "l": "#2b2a28"},
        "frases": ["achei um bug! …brincadeira", "bzzz", "olha o bug aí"],
    },
    "ideia": {
        "quadros": [
            ["...yyy...", "..yyyyy..", ".yyyyyyy.", ".yyyhyyy.", ".yyyyyyy.", "..yyyyy..", "...ggg...", "...ggg...", "....g...."],
            ["r..yyy..r", "..yyyyy..", "ryyyyyyyr", ".yyyhyyy.", "ryyyyyyyr", "..yyyyy..", "...ggg...", "...ggg...", "....g...."],
        ],
        "cores": {"y": "#ffd84a", "h": "#fffbe6", "g": "#8a8a8a", "r": "#fff1a8"},
        "frases": ["tive uma ideia!", "e se…", "pensei numa coisa"],
    },
    "coracao": {
        "quadros": [
            [".rr...rr.", "rrrr.rrrr", "rrrrrrrrr", "rrrrrrrrr", ".rrrrrrr.", "..rrrrr..", "...rrr...", "....r....", "........."],
            [".........", "..r...r..", ".rrr.rrr.", ".rrrrrrr.", "..rrrrr..", "...rrr...", "....r....", ".........", "........."],
        ],
        "cores": {"r": "#e8445a"},
        "frases": ["tô gostando de ficar aqui", "<3", "cê tá mandando bem"],
    },
    "zzz": {
        "quadros": [
            ["......zzz", ".......z.", "......zzz", "..zzzz...", "....z....", "...z.....", "..zzzz...", ".........", "........."],
            ["......zzz", "......z..", "......zzz", "..zzzz...", "...z.....", "..z......", "..zzzz...", ".........", "........."],
        ],
        "cores": {"z": "#a7b8ff"},
        "frases": ["zzz…", "que soninho", "já é tarde, hein"],
    },
    "check": {
        "quadros": [
            ["........g", ".......gg", "......gg.", "g....gg..", "gg..gg...", ".gggg....", "..gg.....", ".........", "........."],
        ],
        "cores": {"g": "#4cc27a"},
        "frases": ["boa!", "foi!", "mais uma pra conta"],
    },
    "fogo": {
        "quadros": [
            ["....o....", "...oo....", "...ooo.o.", "..oyooo..", ".ooyyooo.", ".oyyyyoo.", ".oyyyyyo.", "..oyyyo..", "...ooo..."],
            ["....o....", "....oo...", ".o.ooo...", "..oooyo..", ".oooyyoo.", ".ooyyyyo.", ".oyyyyyo.", "..oyyyo..", "...ooo..."],
        ],
        "cores": {"o": "#ff7a1a", "y": "#ffd84a"},
        "frases": ["tá pegando fogo!", "isso é produção?", "que chama!"],
    },
    "nota": {
        "quadros": [
            ["...nnnnnn", "...nnnnnn", "...n....n", "...n....n", "...n....n", ".nnn..nnn", "nnnn.nnnn", ".nn...nn.", "........."],
            ["..nnnnnn.", "..nnnnnn.", "..n....n.", "..n....n.", "..n....n.", "nnn..nnn.", "nnn.nnnn.", "nn...nn..", "........."],
        ],
        "cores": {"n": "#c79bff"},
        "frases": ["essa é boa!", "lá lá lá ♪", "aumenta o som"],
    },
    "interrogacao": {
        "quadros": [
            ["..qqqq...", ".qq..qq..", ".....qq..", "....qq...", "...qq....", "...qq....", ".........", "...qq....", "...qq...."],
        ],
        "cores": {"q": "#f2efe8"},
        "frases": ["hmm?", "o que é isso?", "será?"],
    },
    "raio": {
        "quadros": [
            ["....yyy..", "...yyy...", "..yyy....", ".yyyyyy..", "....yyy..", "...yyy...", "..yy.....", ".y.......", "........."],
            ["....hhh..", "...yyy...", "..yyy....", ".yyyyyy..", "....yyy..", "...yyy...", "..yy.....", ".h.......", "........."],
        ],
        "cores": {"y": "#ffd84a", "h": "#fffbe6"},
        "frases": ["rapidão!", "deploy nível relâmpago", "zap"],
    },
    "disquete": {
        "quadros": [
            ["bbbbbbbb.", "bbgggggb.", "bbggkggb.", "bbbbbbbbb", "bwwwwwwwb", "bwwwwwwwb", "bwwwwwwwb", "bbbbbbbbb", "........."],
        ],
        "cores": {"b": "#3a63c9", "w": "#f2efe8", "g": "#b8b8b8", "k": "#3a63c9"},
        "frases": ["salvou? Ctrl+S!", "não esquece de salvar", "commit também conta"],
    },
    "suor": {
        "quadros": [
            ["....d....", "...ddd...", "..ddddd..", "..dddhd..", "..ddddd..", "...ddd...", ".........", ".........", "........."],
        ],
        "cores": {"d": "#6fc3ff", "h": "#ffffff"},
        "frases": ["ufa…", "tá puxado hoje", "respira"],
    },
}


def escolher(categoria="geral", minutos_no_app=0, musica_tocando=False):
    """Sorteia um emoji combinando com o momento (categoria do programa em foco, tempo, hora, música)."""
    pesos = {nome: 1.0 for nome in EMOJIS}

    def mais(nome, quanto):
        pesos[nome] += quanto

    if musica_tocando:
        mais("nota", 6)
    if categoria in ("ide", "vscode", "delphi"):
        mais("bug", 3); mais("ideia", 2); mais("disquete", 2); mais("check", 1)
    elif categoria == "terminal":
        mais("raio", 3)
    elif categoria in ("postman", "localhost", "docker", "banco"):
        mais("check", 2); mais("fogo", 2)
    elif categoria in ("discord", "whatsapp"):
        mais("coracao", 2); mais("interrogacao", 1)
    if minutos_no_app >= 45:
        mais("cafe", 3); mais("suor", 2)
    hora = time.localtime().tm_hour
    if hora >= 23 or hora < 5:
        mais("zzz", 5)
    elif 7 <= hora < 10:
        mais("cafe", 2)
    nomes = list(pesos)
    return random.choices(nomes, weights=[pesos[n] for n in nomes])[0]
