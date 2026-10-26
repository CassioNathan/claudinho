"""Atalhos de teclado nos programas, quando o usuário PEDE ("vai pra próxima aba", "desce a página").

Só combinações de teclas, nunca texto livre. Três faixas:
  livre      navegação (setas, Tab, PageUp, Esc, Ctrl+Tab, Alt+←…): roda sem perguntar
  popup      o resto (Enter, Delete, Ctrl+S, letras…): o chat pede confirmação (ferramenta atalho_confirmado)
  bloqueada  Alt+F4, Alt+Tab, qualquer coisa com Win, Ctrl+Shift+Esc, Ctrl+Alt+Del: nunca
Os atalhos que o usuário ensinou pra cada programa (lista no painel) contam como livres na janela daquele programa.
Antes de apertar, a janela certa vem pra frente (senão a tecla cairia no chat do Claudinho)."""
import ctypes
import json
import re
import time
import unicodedata

import janelas
import sistema

user32 = ctypes.windll.user32

MODS = {"ctrl": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B}
APELIDOS = {"control": "ctrl", "ctl": "ctrl", "windows": "win", "super": "win", "escape": "esc", "return": "enter",
            "del": "delete", "ins": "insert", "pgup": "pageup", "pgdn": "pagedown", "pagina_acima": "pageup",
            "pagina_abaixo": "pagedown", "cima": "up", "baixo": "down", "esquerda": "left", "direita": "right",
            "←": "left", "→": "right", "↑": "up", "↓": "down", "espaco": "space", "barra": "space",
            "voltar": "backspace", "mais": "plus", "menos": "minus", "+": "plus", "-": "minus"}
TECLAS = {"enter": 0x0D, "tab": 0x09, "esc": 0x1B, "space": 0x20, "backspace": 0x08, "delete": 0x2E, "insert": 0x2D,
          "pageup": 0x21, "pagedown": 0x22, "end": 0x23, "home": 0x24,
          "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28, "plus": 0xBB, "minus": 0xBD}
TECLAS.update({f"f{i}": 0x6F + i for i in range(1, 13)})
TECLAS.update({c: ord(c.upper()) for c in "abcdefghijklmnopqrstuvwxyz0123456789"})
ESTENDIDAS = {"delete", "insert", "pageup", "pagedown", "end", "home", "left", "up", "right", "down"}

LIVRES = {"up", "down", "left", "right", "tab", "shift+tab", "pageup", "pagedown", "home", "end", "esc", "f5",
          "ctrl+tab", "ctrl+shift+tab", "alt+left", "alt+right", "ctrl+f", "ctrl+l", "ctrl+t",
          "ctrl+home", "ctrl+end", "ctrl+plus", "ctrl+minus", "ctrl+0", "ctrl+pageup", "ctrl+pagedown",
          *(f"ctrl+{i}" for i in range(1, 10))}
BLOQUEADAS = {"alt+f4", "alt+tab", "alt+shift+tab", "ctrl+shift+esc", "ctrl+alt+delete", "ctrl+alt+del", "alt+esc"}
ORDEM = ["ctrl", "alt", "shift", "win"]

# atalhos ensinados por programa (painel → Atalhos dos programas, fica no config.json): valem como "livre" só na
# janela daquele programa (Shift+F10 fora do IntelliJ é o menu de contexto). Esta é a lista que vem de fábrica.
PADRAO = [
    {"programa": "IntelliJ IDEA", "exes": ["idea64.exe", "idea.exe"], "acoes": [
        {"nome": "rodar/iniciar o projeto", "teclas": "shift+f10"},
        {"nome": "parar o projeto", "teclas": "ctrl+f2"},
    ]},
]


def _config():
    try:
        return json.loads((sistema.DADOS / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def programas_ensinados():
    """A lista do painel, lida na hora (o MCP roda em outro processo)."""
    lista = _config().get("atalhos_programas")
    return lista if isinstance(lista, list) else PADRAO


def validar_lista(valor):
    """Limpa a lista que veio do painel: tecla escrita do jeito certo, sem bloqueada, sem lixo."""
    limpa = []
    for prog in (valor if isinstance(valor, list) else [])[:30]:
        if not isinstance(prog, dict):
            continue
        exes = [str(e).strip().lower()[:60] for e in prog.get("exes") or [] if str(e).strip().lower().endswith(".exe")]
        nome = str(prog.get("programa") or "").strip()[:60] or (exes[0].replace(".exe", "") if exes else "")
        if not exes:
            continue
        acoes = []
        for a in (prog.get("acoes") or [])[:40]:
            try:
                combo = entender(str(a.get("teclas") or "")[:40])[0]
            except (ValueError, AttributeError):
                continue
            if faixa(combo) != "bloqueada" and str(a.get("nome") or "").strip():
                acoes.append({"nome": str(a["nome"]).strip()[:60], "teclas": combo})
        limpa.append({"programa": nome, "exes": exes[:5], "acoes": acoes})
    return limpa


def programa_de(janela):
    """O programa ensinado dessa janela (o item da lista), ou None."""
    for prog in programas_ensinados():
        if janela and janela["exe"] in prog.get("exes", []):
            return prog
    return None


def catalogo():
    """Os atalhos ensinados, em texto (a ferramenta atalhos_conhecidos devolve isso)."""
    linhas = [f"{p['programa']} ({', '.join(p['exes'])}): "
              + ", ".join(f"{a['nome']} = {a['teclas']}" for a in p.get("acoes", []))
              for p in programas_ensinados() if p.get("acoes")]
    return "\n".join(linhas) or "nenhum atalho ensinado ainda"


def _limpo(texto):
    return unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode() or texto.lower()


def entender(teclas):
    """'Ctrl + Shift + Tab' -> ('ctrl+shift+tab', [mods], tecla). Erro vira ValueError com o motivo."""
    partes = [p for p in re.split(r"\s*\+\s*|\s+", teclas.strip()) if p] if teclas.strip() not in ("+", "-") \
        else [teclas.strip()]
    if not partes:
        raise ValueError("nenhuma tecla")
    nomes = []
    for p in partes:
        nome = APELIDOS.get(p.lower(), APELIDOS.get(_limpo(p), _limpo(p)))
        if nome not in MODS and nome not in TECLAS:
            raise ValueError(f"não conheço a tecla '{p}'")
        nomes.append(nome)
    mods = sorted({n for n in nomes if n in MODS}, key=ORDEM.index)
    principais = [n for n in nomes if n not in MODS]
    if len(principais) != 1:
        raise ValueError("mande uma tecla principal por vez (ex.: ctrl+tab, alt+left, pagedown)")
    combo = "+".join(mods + principais)
    return combo, mods, principais[0]


def faixa(combo):
    """'livre', 'popup' ou 'bloqueada'."""
    if combo in BLOQUEADAS or "win" in combo.split("+"):
        return "bloqueada"
    return "livre" if combo in LIVRES else "popup"


def vendado():
    return bool(_config().get("vendado"))


def achar_janela(nome):
    """A janela pelo nome (título ou programa, aproximado); sem nome, a que ele está usando (pulando o Claudinho)."""
    if not nome.strip():
        import tela
        return tela.janela_da_frente()
    alvo = _limpo(nome).replace(".exe", "").strip()
    todas = janelas.listar()
    for j in todas:
        if alvo in _limpo(j["titulo"]) or alvo in j["exe"].replace(".exe", ""):
            return j
    # pelo nome que ele deu na lista de atalhos ("intellij" → idea64.exe)
    for prog in programas_ensinados():
        if alvo in _limpo(prog.get("programa", "")):
            for j in todas:
                if j["exe"] in prog.get("exes", []):
                    return j
    import programas
    for _, item in programas.achar(nome):
        abertas = programas._janelas_do(item)
        if abertas:
            return abertas[0]
    return None


def esperar(janela, segundos=120):
    """Espera o programa abrir de verdade (janela + CPU sossegada) e devolve em quanto tempo, em texto."""
    segundos = max(5, min(int(segundos or 120), 300))
    j, levou, pronta = janelas.esperar_pronta(lambda: achar_janela(janela), limite=segundos)
    if not j:
        return f"em {levou:.0f}s a janela '{janela}' não apareceu: confira com ver_tela antes de seguir"
    if pronta:
        return f"{j['titulo'] or j['exe']} está aberta e pronta (levou {levou:.0f}s)"
    return (f"{j['titulo'] or j['exe']} abriu mas continua trabalhando depois de {levou:.0f}s (carregando/indexando): "
            "dá pra seguir, mas confira com ver_tela")


def _apertar(vk, solta=False, estendida=False):
    user32.keybd_event(vk, 0, (0x2 if solta else 0) | (0x1 if estendida else 0), 0)


def apertar(teclas, janela="", vezes=1, confirmado=False):
    """Aperta o atalho na janela pedida. Devolve o que fez (ou por que não fez), numa frase."""
    if vendado():
        return "não posso: estou com a faixa nos olhos (vendado). Ele tira no Win+Shift+Y."
    try:
        combo, mods, tecla = entender(teclas[:40])
    except ValueError as e:
        return f"não entendi o atalho: {e}"
    f = faixa(combo)
    if f == "bloqueada":
        return f"{combo} é bloqueado (fecha programa, troca de janela ou mexe no Windows): não aperto."
    j = achar_janela(janela)
    if not j:
        return f"não achei a janela '{janela}' aberta" if janela.strip() else "não achei nenhuma janela pra apertar"
    import programas
    if programas.exe_bloqueado(j["exe"]):
        return f"{j['exe']} está bloqueado no painel (Programas): não aperto nada nele"
    prog = programa_de(j)
    if prog and combo in {a["teclas"] for a in prog.get("acoes", [])}:
        f = "livre"  # atalho ensinado daquele programa
    if f == "popup" and not confirmado:
        return f"{combo} precisa da confirmação dele: use a ferramenta atalho_confirmado com as mesmas teclas."
    vezes = max(1, min(int(vezes or 1), 10 if f == "livre" else 3))
    import abrir
    if user32.GetForegroundWindow() != j["hwnd"]:
        abrir.forcar_frente(j["hwnd"])
        time.sleep(0.25)
    if user32.GetForegroundWindow() != j["hwnd"]:
        return f"não consegui trazer {j['titulo'] or j['exe']} pra frente: não apertei nada"
    for _ in range(vezes):
        for m in mods:
            _apertar(MODS[m])
        _apertar(TECLAS[tecla], estendida=tecla in ESTENDIDAS)
        _apertar(TECLAS[tecla], solta=True, estendida=tecla in ESTENDIDAS)
        for m in reversed(mods):
            _apertar(MODS[m], solta=True)
        time.sleep(0.08)
    nome = j["titulo"] or j["exe"]
    return f"apertei {combo}" + (f" {vezes}x" if vezes > 1 else "") + f" em {nome}"
