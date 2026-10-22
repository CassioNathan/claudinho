"""Instala o Claudinho neste PC.

    python instalar.py              instala dependências e o hook de aviso
    python instalar.py --iniciar    também abre o Claudinho junto com o Windows

O que ele faz:
1. pip install das dependências (requirements.txt);
2. copia o hook de aviso para ~/.claude/hooks e registra no ~/.claude/settings.json
   (com backup do settings antes), para o Claudinho avisar quando um chat termina;
3. cria ~/.claudinho/CLAUDE.md (o seu perfil) se ainda não existir;
4. com --iniciar, cria um atalho na pasta Inicializar do Windows.
Depois disso falta só logar o Claude Code no terminal: rode `claude` e digite /login.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CLAUDE = Path.home() / ".claude"
DADOS = Path.home() / ".claudinho"

PERFIL_MODELO = """# Quem é o usuário

Este arquivo é o perfil que o Claudinho usa no chat e nas piadas. Escreva aqui quem você é,
onde trabalha, o que faz, ferramentas que usa e projetos pessoais.
"""


def passo(texto):
    print(f"\n==> {texto}")


def instalar_dependencias():
    passo("Instalando dependências")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(AQUI / "requirements.txt")], check=True)


def instalar_hook():
    passo("Instalando o hook de aviso no Claude Code")
    (CLAUDE / "hooks").mkdir(parents=True, exist_ok=True)
    destino = CLAUDE / "hooks" / "claudinho_notificar.py"
    shutil.copy(AQUI / "hook" / "claudinho_notificar.py", destino)

    python = Path(sys.executable).with_name("python.exe")  # nunca o pythonw: o hook lê o stdin
    comando = f'"{python.as_posix()}" "{destino.as_posix()}"'
    config = CLAUDE / "settings.json"
    dados = json.loads(config.read_text(encoding="utf-8")) if config.exists() else {}
    if config.exists():
        shutil.copy(config, config.with_name("settings.json.bak-claudinho"))

    paradas = dados.setdefault("hooks", {}).setdefault("Stop", [])
    for grupo in paradas:  # já instalado antes: só atualiza o caminho
        for h in grupo.get("hooks", []):
            if "claudinho_notificar" in h.get("command", ""):
                h["command"] = comando
                break
        else:
            continue
        break
    else:
        paradas.append({"hooks": [{"type": "command", "command": comando, "timeout": 10}]})
    config.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"hook registrado em {config} (backup em settings.json.bak-claudinho)")


def criar_perfil():
    DADOS.mkdir(exist_ok=True)
    perfil = DADOS / "CLAUDE.md"
    if not perfil.exists():
        passo("Criando seu perfil em branco")
        perfil.write_text(PERFIL_MODELO, encoding="utf-8")
        print(f"edite {perfil} pra ele saber quem você é")


def iniciar_com_windows():
    passo("Abrindo o Claudinho junto com o Windows")
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    pasta = Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"
    atalho = pasta / "Claudinho.lnk"
    script = (f'$s = (New-Object -ComObject WScript.Shell).CreateShortcut("{atalho}"); '
              f'$s.TargetPath = "{pythonw}"; $s.Arguments = \'"{AQUI / "claudinho.pyw"}"\'; '
              f'$s.WorkingDirectory = "{AQUI}"; $s.Save()')
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)
    print(f"atalho criado em {atalho}")


def main():
    instalar_dependencias()
    instalar_hook()
    criar_perfil()
    if "--iniciar" in sys.argv:
        iniciar_com_windows()
    passo("Pronto!")
    print("Falta só: logar o Claude Code no terminal (rode `claude` e digite /login) e abrir o claudinho.pyw.")
    if not shutil.which("claude"):
        print("ATENÇÃO: não achei o comando `claude`. Instale o Claude Code antes de usar o chat.")


if __name__ == "__main__":
    main()
