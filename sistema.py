"""Onde as coisas ficam e a "instalação" do Claudinho no Windows (atalho de inicialização e aviso do Claude Code).

Funciona igual rodando do código (python claudinho.pyw) e empacotado pelo PyInstaller (Claudinho.exe):
- BASE: onde estão os arquivos que vêm com ele (painel.html, extensão…);
- DADOS: o que é de cada pessoa (config, banco, perfil) — ~/.claudinho, ou CLAUDINHO_DADOS pra testar;
- o "ajudante" de linha de comando: claudinho-cli.exe empacotado, ou python cli.py no código.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

VERSAO = "1.2.0"
EMPACOTADO = bool(getattr(sys, "frozen", False))
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
PASTA_APP = Path(sys.executable).resolve().parent if EMPACOTADO else BASE
DADOS = Path(os.environ.get("CLAUDINHO_DADOS") or Path.home() / ".claudinho")
CLAUDE = Path.home() / ".claude"
ATALHO_INICIO = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup/Claudinho.lnk"

PERFIL_MODELO = """# Quem é o usuário

Este arquivo é o perfil que o Claudinho usa no chat e nas piadas. Escreva aqui quem você é,
onde trabalha, o que faz, ferramentas que usa e projetos pessoais.
"""


def comando_cli(*args):
    """Como chamar o ajudante de linha de comando (música, abrir site, aviso do Claude Code)."""
    if EMPACOTADO:
        return [str(PASTA_APP / "claudinho-cli.exe"), *args]
    return [str(Path(sys.executable).with_name("python.exe")), str(BASE / "cli.py"), *args]


CREATE_BREAKAWAY_FROM_JOB = 0x01000000


def lancar(alvo, argumentos=None):
    """Abre programa, site ou arquivo como se você tivesse clicado, FORA do "job" do Claudinho. O chat roda num job
    que fecha tudo junto com o Claudinho (pra não sobrar processo do chat); o que ele abre pra você herdava o job e
    fechava junto. Quem abre agora é um ajudante que sai do job antes (o programa fica filho dele, livre)."""
    try:
        subprocess.Popen(comando_cli("lancar", str(alvo), *([argumentos] if argumentos else [])),
                         creationflags=subprocess.CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB, close_fds=True)
    except OSError:  # job que não deixa sair (Claudinho antigo): abre direto, como antes
        os.startfile(str(alvo), arguments=argumentos) if argumentos else os.startfile(str(alvo))


def comando_texto(*args):
    return " ".join(f'"{Path(p).as_posix()}"' if i == 0 or (i == 1 and not EMPACOTADO) else p
                    for i, p in enumerate(comando_cli(*args)))


# ---------- segredos (chave da API) criptografados pelo Windows (DPAPI: só o seu usuário consegue abrir) ----------
def _dpapi(dados, cifrar):
    import ctypes
    import ctypes.wintypes as wt

    class Blob(ctypes.Structure):
        _fields_ = [("tamanho", wt.DWORD), ("dados", ctypes.POINTER(ctypes.c_char))]

    buffer = ctypes.create_string_buffer(dados, len(dados))
    entrada, saida = Blob(len(dados), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), Blob()
    funcao = ctypes.windll.crypt32.CryptProtectData if cifrar else ctypes.windll.crypt32.CryptUnprotectData
    if not funcao(ctypes.byref(entrada), None, None, None, None, 0, ctypes.byref(saida)):
        raise OSError("o Windows não conseguiu (des)criptografar")
    try:
        return ctypes.string_at(saida.dados, saida.tamanho)
    finally:
        ctypes.windll.kernel32.LocalFree(saida.dados)


def guardar_segredo(nome, valor):
    arquivo = DADOS / f"{nome}.bin"
    if not valor:
        arquivo.unlink(missing_ok=True)
        return
    DADOS.mkdir(parents=True, exist_ok=True)
    arquivo.write_bytes(_dpapi(valor.encode("utf-8"), True))


def ler_segredo(nome):
    try:
        return _dpapi((DADOS / f"{nome}.bin").read_bytes(), False).decode("utf-8")
    except (OSError, ValueError):
        return None


def claude_instalado():
    return shutil.which("claude") is not None


# ---------- abrir junto com o Windows ----------
def abre_com_windows():
    return ATALHO_INICIO.exists()


def abrir_com_windows(ligar):
    """Cria (ou apaga) o atalho do Claudinho na pasta Inicializar do Windows."""
    if not ligar:
        ATALHO_INICIO.unlink(missing_ok=True)
        return
    if EMPACOTADO:
        alvo, args, pasta = PASTA_APP / "Claudinho.exe", "", PASTA_APP
    else:
        alvo, args, pasta = Path(sys.executable).with_name("pythonw.exe"), f'"{BASE / "claudinho.pyw"}"', BASE
    ATALHO_INICIO.parent.mkdir(parents=True, exist_ok=True)
    script = (f'$s = (New-Object -ComObject WScript.Shell).CreateShortcut("{ATALHO_INICIO}"); '
              f'$s.TargetPath = "{alvo}"; $s.Arguments = \'{args}\'; $s.WorkingDirectory = "{pasta}"; $s.Save()')
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


# ---------- aviso quando um chat do Claude Code termina (hook "Stop") ----------
def _ler_settings():
    arquivo = CLAUDE / "settings.json"
    try:
        return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}
    except ValueError:
        return None  # settings com erro: melhor não mexer


def _e_nosso(comando):
    return "claudinho_notificar" in comando or "claudinho-cli" in comando or ("cli.py" in comando and " aviso" in comando)


def aviso_ligado():
    dados = _ler_settings() or {}
    return any(_e_nosso(h.get("command", "")) for g in dados.get("hooks", {}).get("Stop", []) for h in g.get("hooks", []))


def ligar_aviso(ligar):
    """Registra (ou tira) o aviso do Claudinho no ~/.claude/settings.json, com backup antes."""
    dados = _ler_settings()
    if dados is None:
        raise RuntimeError("o ~/.claude/settings.json está com erro de formato; não mexi nele")
    arquivo = CLAUDE / "settings.json"
    if arquivo.exists():
        shutil.copy(arquivo, arquivo.with_name("settings.json.bak-claudinho"))
    paradas = dados.setdefault("hooks", {}).setdefault("Stop", [])
    for grupo in paradas:  # tira o nosso (de versões antigas também); se ligar, põe de novo atualizado
        grupo["hooks"] = [h for h in grupo.get("hooks", []) if not _e_nosso(h.get("command", ""))]
    paradas[:] = [g for g in paradas if g.get("hooks")]
    if ligar:
        paradas.append({"hooks": [{"type": "command", "command": comando_texto("aviso"), "timeout": 10}]})
    if not paradas:
        dados["hooks"].pop("Stop")
    CLAUDE.mkdir(exist_ok=True)
    arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
