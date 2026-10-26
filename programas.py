"""Abre qualquer programa instalado no PC pelo nome (aproximado): "steam", "abre o vscode", "bloco de notas".

Acha no menu Iniciar (atalhos .lnk e apps da Microsoft Store), e então:
  - se o programa já tem janela aberta (inclusive minimizada), traz ela pra frente;
  - se não, abre (um programa que vive na bandeja, como a Steam, reabre a janela dele ao ser aberto de novo).
Só abre: não passa argumento, não roda comando, não fecha nada. É a única coisa que o MCP do Claudinho faz.

    python programas.py <nome>        abre/traz pra frente
    python programas.py --listar      os programas que ele conhece
"""
import ctypes
import ctypes.wintypes as wt
import difflib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

# com os padrões do Windows caso a variável falte (um processo aberto com ambiente enxuto não acharia nada)
PASTAS_ATALHOS = [
    Path(os.environ.get("APPDATA") or Path.home() / "AppData/Roaming") / "Microsoft/Windows/Start Menu/Programs",
    Path(os.environ.get("PROGRAMDATA") or "C:/ProgramData") / "Microsoft/Windows/Start Menu/Programs",
    Path.home() / "Desktop",
    Path(os.environ.get("PUBLIC") or "C:/Users/Public") / "Desktop",
]
RUIM = re.compile(r"uninstall|desinstal|remover|readme|leia-?me|manual|licen|ajuda|help|documenta|release notes|"
                  r"website|site d[aeo]|support|suporte|changelog", re.I)
PALAVRAS_DE_PEDIDO = {"abre", "abrir", "abra", "abri", "o", "a", "os", "as", "pra", "pro", "para", "pelo", "pela", "meu",
                      "minha", "programa", "aplicativo", "app", "por", "favor", "no", "na", "de", "do", "da"}
SINONIMOS = {"bloco de notas": "notepad", "calculadora": "calculator", "paint": "paint", "vs code": "visual studio code",
             "vscode": "visual studio code", "code": "visual studio code", "zap": "whatsapp", "zapzap": "whatsapp",
             "word": "word", "excel": "excel", "powerpoint": "powerpoint", "navegador": "chrome"}

# programas cuja janela pertence a outro .exe (a Steam desenha a interface no steamwebhelper)
OUTROS_EXES = {"steam.exe": ["steamwebhelper.exe"]}

_CACHE = {"quando": 0.0, "itens": []}


def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", texto).strip()


def _alvos_dos_atalhos(atalhos):
    """Programa (.exe) que cada atalho abre, tudo numa chamada só do PowerShell."""
    if not atalhos:
        return {}
    import tempfile
    lista = Path(tempfile.gettempdir()) / "claudinho_atalhos.json"
    lista.write_text(json.dumps([str(a) for a in atalhos]), encoding="utf-8")
    roteiro = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8; $s = New-Object -ComObject WScript.Shell; "
               f"$entrada = Get-Content -Raw -Encoding UTF8 '{lista}' | ConvertFrom-Json; "
               "$saida = @{}; foreach ($l in $entrada) { try { $saida[$l] = $s.CreateShortcut($l).TargetPath } catch {} }; "
               "$saida | ConvertTo-Json -Compress")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", roteiro],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        return json.loads(r.stdout or "{}")
    except Exception:
        return {}


def _apps_iniciar():
    """Tudo o que aparece no menu Iniciar (inclui os da Store): [{'Name', 'AppID'}]."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
                            "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        dados = json.loads(r.stdout or "[]")
        return [dados] if isinstance(dados, dict) else dados
    except Exception:
        return []


def indexar(forcar=False):
    """Lista de {'nome', 'atalho', 'app_id', 'exe'}; guardada por 10 minutos."""
    if not forcar and _CACHE["itens"] and time.time() - _CACHE["quando"] < 600:
        return _CACHE["itens"]
    itens, vistos = [], set()
    atalhos = []
    for pasta in PASTAS_ATALHOS:
        if pasta.is_dir():
            atalhos += [a for a in pasta.rglob("*.lnk") if not RUIM.search(a.stem)]
    alvos = _alvos_dos_atalhos(atalhos)
    for a in atalhos:
        chave = normalizar(a.stem)
        if chave in vistos:
            continue
        vistos.add(chave)
        exe = Path(alvos.get(str(a)) or "").name.lower()
        itens.append({"nome": a.stem, "atalho": str(a), "app_id": None, "exe": exe if exe.endswith(".exe") else ""})
    for app in _apps_iniciar():
        nome, app_id = (app.get("Name") or "").strip(), app.get("AppID") or ""
        if not nome or RUIM.search(nome) or normalizar(nome) in vistos:
            continue
        vistos.add(normalizar(nome))
        itens.append({"nome": nome, "atalho": None, "app_id": app_id, "exe": ""})
    _CACHE.update(quando=time.time(), itens=itens)
    return itens


def pontuar(pedido, nome):
    """0 a 1: o quanto o nome do programa parece com o que foi pedido."""
    a, b = normalizar(pedido), normalizar(nome)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if b.startswith(a) or a.startswith(b):
        return 0.93
    pa, pb = a.split(), b.split()
    if a in b.split() or all(p in pb for p in pa):
        return 0.9
    if a in b:
        return 0.85
    juntos = a.replace(" ", "")
    if juntos in b.replace(" ", ""):
        return 0.82
    melhor = 0.0
    for palavra in [b] + pb:  # erro de fala/escrita: "steem" ~ "steam", "intelij" ~ "intellij"
        if abs(len(a) - len(palavra)) <= 1 and a[0] == palavra[0] and len(a) >= 4:
            razao = difflib.SequenceMatcher(None, a, palavra).ratio()
            if razao >= 0.8:
                melhor = max(melhor, razao * 0.95)
    return melhor


def limpar_pedido(pedido):
    palavras = [p for p in normalizar(pedido).split() if p not in PALAVRAS_DE_PEDIDO]
    texto = " ".join(palavras) or normalizar(pedido)
    return SINONIMOS.get(texto, texto)


def achar(pedido, minimo=0.72, n=3):
    """Os programas que mais parecem com o pedido, do melhor pro pior: [(pontos, item)]."""
    pedido = limpar_pedido(pedido)
    ranque = sorted(((pontuar(pedido, i["nome"]), i) for i in indexar()), key=lambda t: (-t[0], len(t[1]["nome"])))
    return [t for t in ranque[:n] if t[0] >= minimo]


def _exes(item):
    return ([item["exe"]] + OUTROS_EXES.get(item["exe"], [])) if item["exe"] else []


def _janelas_do(item):
    """Janelas já abertas desse programa (pelo .exe do atalho; sem ele, pelo título)."""
    import janelas
    todas = janelas.listar()
    exes = _exes(item)
    nome = normalizar(item["nome"])
    return [j for j in todas if j["exe"] in exes or (nome and nome == normalizar(j["titulo"]))]


def _janelas_minimizadas(exes):
    """Janelas minimizadas (que o `listar` pula) de um programa, por exe."""
    user32 = ctypes.windll.user32
    import janelas
    achadas = []
    ENUM = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd) and user32.IsIconic(hwnd) and user32.GetWindowTextLengthW(hwnd) \
                and janelas.exe_de(hwnd) in exes:
            achadas.append(hwnd)
        return True
    user32.EnumWindows(ENUM(cb), 0)
    return achadas


def bloqueados():
    """Os programas que ele desligou no painel (Programas): o Claudinho não abre nem mexe neles. Lido na hora."""
    try:
        import sistema
        cfg = json.loads((sistema.DADOS / "config.json").read_text(encoding="utf-8"))
        return {str(n) for n in cfg.get("programas_bloqueados") or []}
    except (OSError, ValueError, ImportError):
        return set()


def esta_bloqueado(item):
    return item["nome"] in bloqueados()


def exe_bloqueado(exe):
    """A janela desse .exe é de um programa bloqueado?"""
    nomes = bloqueados()
    return bool(nomes and exe and any(i["exe"] == exe and i["nome"] in nomes for i in indexar()))


def recusa(pedido):
    """Se o programa pedido está bloqueado no painel, a frase de recusa; senão None."""
    achados = achar(pedido) if bloqueados() else []
    if achados and esta_bloqueado(achados[0][1]):
        return f"{achados[0][1]['nome']} está bloqueado no painel (Programas): não abro nem mexo nele"
    return None


def listar(busca="", n=20):
    """Programas instalados (nome, liberado) que parecem com a busca; sem busca, os primeiros em ordem alfabética."""
    nomes = bloqueados()
    itens = indexar()
    if busca.strip():
        itens = [i for _, i in achar(busca, minimo=0.6, n=n)]
    else:
        itens = sorted(itens, key=lambda i: i["nome"].lower())[:n]
    return [{"nome": i["nome"], "exe": i["exe"], "liberado": i["nome"] not in nomes} for i in itens]


def abrir(pedido):
    """Abre (ou traz pra frente) o programa que mais se parece com o pedido. Devolve o que fez, em uma frase."""
    import abrir as _abrir
    import janelas
    achados = achar(pedido)
    if not achados:
        return f"não achei nenhum programa parecido com '{pedido}' instalado"
    item = achados[0][1]
    if esta_bloqueado(item):
        return f"{item['nome']} está bloqueado no painel (Programas): não abro nem mexo nele"
    # já está aberto? (visível ou minimizado) → só traz pra frente
    jans = _janelas_do(item)
    hwnds = [j["hwnd"] for j in jans] or (_janelas_minimizadas(_exes(item)) if item["exe"] else [])
    if hwnds:
        _abrir.forcar_frente(hwnds[0])
        return f"{item['nome']} já estava aberto: trouxe pra frente"
    antes = _abrir.titulos_agora()
    if item["atalho"]:
        os.startfile(item["atalho"])
    else:
        subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{item['app_id']}"])
    exes = _exes(item)
    if exes:
        _abrir.trazer_pra_frente(exes, antes, espera=15.0)
    else:  # app da Store: espera uma janela nova aparecer e traz pra frente
        fim = time.time() + 12
        while time.time() < fim:
            novas = [j for j in janelas.listar() if j["hwnd"] not in antes]
            if novas:
                time.sleep(0.4)
                _abrir.forcar_frente(novas[0]["hwnd"])
                break
            time.sleep(0.3)
    return f"abri {item['nome']}"


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == "--listar":
        for i in sorted(indexar(True), key=lambda i: i["nome"].lower()):
            print(i["nome"])
        return
    print(abrir(" ".join(sys.argv[1:])))


if __name__ == "__main__":
    main()
