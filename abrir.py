"""Ajudante limitado do Claudinho: só abre site, faz pesquisa ou abre programa da lista.

Como não consegue fazer mais nada, o chat pode rodar sem pedir confirmação:
    python abrir.py site https://github.com
    python abrir.py pesquisa "como fazer left join"  [google|youtube|bing|duckduckgo]
    python abrir.py programa intellij
A lista de programas fica em PROGRAMAS (e pode ser trocada em ~/.claudinho/config.json,
chave "programas_liberados").
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import sys
import time
import winreg
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import janelas

# nome -> pedaços do nome do atalho no menu Iniciar / área de trabalho
PROGRAMAS = {
    "navegador": None,  # navegador padrão
    "chrome": ["Google Chrome"],
    "edge": ["Microsoft Edge"],
    "opera": ["Opera"],
    "intellij": ["IntelliJ IDEA"],
    "vscode": ["Visual Studio Code"],
    "discord": ["Discord"],
    "whatsapp": ["WhatsApp"],
    "postman": ["Postman"],
    "docker": ["Docker Desktop"],
    "spotify": ["Spotify"],
}

# nome -> executável da janela (pra achar e trazer pra frente depois de abrir)
EXES = {
    "chrome": ["chrome.exe"], "edge": ["msedge.exe"], "opera": ["opera.exe"],
    "intellij": ["idea64.exe", "idea.exe"], "vscode": ["code.exe"], "discord": ["discord.exe"],
    "whatsapp": ["whatsapp.exe", "whatsapp.root.exe"], "postman": ["postman.exe"],
    "docker": ["docker desktop.exe"], "spotify": ["spotify.exe"],
}
NAVEGADORES = ["opera.exe", "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"]

BUSCADORES = {
    "google": "https://www.google.com/search?q={}",
    "youtube": "https://www.youtube.com/results?search_query={}",
    "bing": "https://www.bing.com/search?q={}",
    "duckduckgo": "https://duckduckgo.com/?q={}",
}

PASTAS_ATALHOS = [
    Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
    Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
    Path.home() / "Desktop",
    Path(os.environ.get("PUBLIC", "")) / "Desktop",
]


def liberados():
    try:
        cfg = json.loads((Path.home() / ".claudinho/config.json").read_text(encoding="utf-8"))
        nomes = cfg.get("programas_liberados")
    except Exception:
        nomes = None
    return {n: PROGRAMAS[n] for n in (nomes or PROGRAMAS) if n in PROGRAMAS}


def navegador_padrao():
    """Executável do navegador padrão, pelo ProgId do https (ex.: 'Opera GXStable' -> opera.exe)."""
    try:
        chave = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, chave) as k:
            prog = winreg.QueryValueEx(k, "ProgId")[0].lower()
    except OSError:
        return NAVEGADORES
    for pedaco, exe in (("opera", "opera.exe"), ("chrome", "chrome.exe"), ("msedge", "msedge.exe"),
                        ("firefox", "firefox.exe"), ("brave", "brave.exe")):
        if pedaco in prog:
            return [exe]
    return NAVEGADORES


def forcar_frente(hwnd):
    """O Windows não deixa processo em segundo plano jogar janela pra frente; o jeito aceito é
    "grudar" na fila de entrada de quem está na frente por um instante e então ativar."""
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    frente = user32.GetForegroundWindow()
    t_frente = user32.GetWindowThreadProcessId(frente, None)
    t_eu = kernel32.GetCurrentThreadId()
    grudou = t_frente and t_frente != t_eu and user32.AttachThreadInput(t_eu, t_frente, True)
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if grudou:
            user32.AttachThreadInput(t_eu, t_frente, False)
    return user32.GetForegroundWindow() == hwnd


def trazer_pra_frente(exes, antes, espera=6.0):
    """Espera a janela do programa aparecer (ou mudar de título, no caso de aba nova no navegador)
    e traz ela pra frente. `antes` = títulos por janela tirados antes de abrir."""
    fim, achada = time.time() + espera, None
    while time.time() < fim:
        candidatas = [j for j in janelas.listar() if j["exe"] in exes]
        mudou = [j for j in candidatas if antes.get(j["hwnd"]) != j["titulo"]]
        achada = (mudou or [None])[0]
        if achada:
            break
        time.sleep(0.25)
    achada = achada or next((j for j in janelas.listar() if j["exe"] in exes), None)
    if achada:
        time.sleep(0.3)  # deixa a janela terminar de nascer
        forcar_frente(achada["hwnd"])


def titulos_agora():
    try:
        return {j["hwnd"]: j["titulo"] for j in janelas.listar()}
    except Exception:
        return {}


def abrir_site(url):
    if "://" not in url and "." in url and " " not in url:  # "youtube.com" vira https://youtube.com
        url = "https://" + url
    partes = urlparse(url)
    if partes.scheme not in ("http", "https") or not partes.netloc:
        sys.exit(f"recusado: só abro endereço http(s), não '{url}'")
    antes = titulos_agora()
    os.startfile(url)
    print(f"abri {url}")
    trazer_pra_frente(navegador_padrao(), antes)


def achar_atalho(pedacos):
    for pasta in PASTAS_ATALHOS:
        if pasta.is_dir():
            for atalho in sorted(pasta.rglob("*.lnk")):
                if any(p.lower() in atalho.stem.lower() for p in pedacos) and "uninstall" not in atalho.stem.lower():
                    return atalho
    return None


def app_da_loja(pedacos):
    """Apps da Microsoft Store (ex.: WhatsApp) não têm atalho .lnk: acha o AppID."""
    filtro = "|".join(pedacos)
    saida = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"Get-StartApps | Where-Object {{ $_.Name -match '{filtro}' }} | Select-Object -First 1 -ExpandProperty AppID"],
        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout.strip()
    return saida or None


def abrir_programa(nome):
    programas = liberados()
    nome = nome.lower().strip()
    if nome not in programas:
        sys.exit(f"recusado: '{nome}' não está na lista. Liberados: {', '.join(programas)}")
    pedacos = programas[nome]
    if pedacos is None:
        abrir_site("https://www.google.com")
        return
    antes = titulos_agora()
    atalho = achar_atalho(pedacos)
    if atalho:
        os.startfile(str(atalho))
        print(f"abri {atalho.stem}")
    else:
        app_id = app_da_loja(pedacos)
        if not app_id:
            sys.exit(f"não achei o {nome} instalado")
        subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app_id}"])
        print(f"abri {nome}")
    # programa pesado (IntelliJ, Docker) demora pra mostrar a janela: espera mais
    trazer_pra_frente(EXES.get(nome, []), antes, espera=15.0)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    acao, resto = sys.argv[1], sys.argv[2:]
    if acao == "site":
        abrir_site(resto[0])
    elif acao == "pesquisa":
        buscador = resto[1].lower() if len(resto) > 1 and resto[1].lower() in BUSCADORES else "google"
        abrir_site(BUSCADORES[buscador].format(quote_plus(resto[0])))
    elif acao == "programa":
        abrir_programa(resto[0])
    else:
        sys.exit(f"recusado: ação '{acao}' não existe (site, pesquisa, programa)")


if __name__ == "__main__":
    main()
