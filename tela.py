"""Print da tela pra IA quando o usuário PEDE ("olha a tela e me responde"): usado pela ferramenta `ver_tela`
(MCP do Claudinho e chat pela API). Só lê: tira o print e devolve, não clica nem digita nada.

Respeita a faixa nos olhos e a chave "ver_tela" do painel lendo o config.json na hora (o MCP roda em outro processo)."""
import ctypes
import ctypes.wintypes as wt
import io
import json
import time

from PIL import ImageGrab

import janelas
import sistema

ALVOS = ("janela", "monitor", "tudo")
LARGURA = 1280  # barato e ainda legível; pra texto miúdo, a janela em foco sai mais nítida


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT), ("dwFlags", wt.DWORD)]


def bloqueio():
    """Motivo pra NÃO olhar (faixa nos olhos, chave desligada), ou None se pode."""
    try:
        cfg = json.loads((sistema.DADOS / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    if cfg.get("vendado"):
        return "estou com a faixa nos olhos (vendado): não posso olhar a tela. Ele tira no Win+Shift+Y."
    if not cfg.get("ver_tela", True):
        return "olhar a tela está desligado no painel (Privacidade e sistema → \"Olhar a tela quando eu pedir\")."
    return None


def janela_da_frente():
    """A janela que ele está usando: a da frente, pulando as do próprio Claudinho (mascote, chat, balões)."""
    janela = janelas.janela_ativa()
    if not janela or janela["exe"] in janelas.IGNORAR or janela["rect"][2] - janela["rect"][0] <= 200:
        janela = next(iter(janelas.listar()), None)
    return janela


def monitor_de(x, y):
    mi = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
    h = ctypes.windll.user32.MonitorFromPoint(wt.POINT(int(x), int(y)), 2)
    ctypes.windll.user32.GetMonitorInfoW(h, ctypes.byref(mi))
    r = mi.rcMonitor
    return (r.left, r.top, r.right, r.bottom)


def capturar(alvo="janela", nome=""):
    """-> (imagem PIL, descrição). `alvo`: janela (a em foco), monitor (o dela inteiro) ou tudo (todos).
    `nome`: olhar uma janela específica (programa ou parte do título): ela vem pra frente antes do print."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # coordenadas reais, senão o recorte sai torto com escala
    except Exception:
        pass
    alvo = alvo if alvo in ALVOS else "janela"
    if nome.strip():
        import abrir
        import teclas
        janela = teclas.achar_janela(nome)
        if not janela:
            raise LookupError(f"não achei a janela '{nome}' aberta")
        import programas
        if programas.exe_bloqueado(janela["exe"]):
            raise PermissionError(f"{janela['exe']} está bloqueado no painel (Programas): não olho ele")
        if ctypes.windll.user32.GetForegroundWindow() != janela["hwnd"]:
            abrir.forcar_frente(janela["hwnd"])
            time.sleep(0.4)  # dar tempo de redesenhar na frente
        janela = janelas.descrever(janela["hwnd"])  # posição de agora (podia estar minimizada)
    else:
        janela = janela_da_frente()
    if alvo == "tudo":
        img, descricao = ImageGrab.grab(all_screens=True), "todos os monitores"
    else:
        if janela:
            esq, topo, dir_, base = janela["rect"]
            mon = monitor_de((esq + dir_) / 2, (topo + base) / 2)
        else:
            ponto = wt.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(ponto))
            mon = monitor_de(ponto.x, ponto.y)
        if alvo == "janela" and janela:
            esq, topo, dir_, base = janela["rect"]
            caixa = (max(esq, mon[0]), max(topo, mon[1]), min(dir_, mon[2]), min(base, mon[3]))
            descricao = f"janela em foco: {janela['titulo'] or janela['exe']} ({janela['exe']})"
        else:
            caixa, descricao = mon, "monitor inteiro"
        img = ImageGrab.grab(bbox=caixa, all_screens=True)
    if img.width > LARGURA:
        img = img.resize((LARGURA, round(img.height * LARGURA / img.width)))
    return img, descricao


def jpeg(img, qualidade=80):
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, "JPEG", quality=qualidade)
    return buffer.getvalue()
