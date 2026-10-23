"""Instala o Claudinho pra rodar do código (quem só quer usar baixa o zip da release: ver README).

    python instalar.py              instala dependências e o aviso do Claude Code
    python instalar.py --iniciar    também abre o Claudinho junto com o Windows

O que ele faz:
1. pip install das dependências (requirements.txt);
2. registra o aviso no ~/.claude/settings.json (com backup antes), pro Claudinho avisar quando um chat termina;
3. com --iniciar, cria um atalho na pasta Inicializar do Windows.
Os dois últimos também dá pra ligar/desligar no painel (Sistema). Depois falta só logar o Claude Code:
rode `claude` no terminal e digite /login.
"""
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import sistema  # noqa: E402


def passo(texto):
    print(f"\n==> {texto}")


def main():
    passo("Instalando dependências")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(AQUI / "requirements.txt")], check=True)
    passo("Registrando o aviso no Claude Code")
    sistema.ligar_aviso(True)
    print(f"registrado em {sistema.CLAUDE / 'settings.json'} (backup em settings.json.bak-claudinho)")
    if "--iniciar" in sys.argv:
        passo("Abrindo o Claudinho junto com o Windows")
        sistema.abrir_com_windows(True)
        print(f"atalho criado em {sistema.ATALHO_INICIO}")
    passo("Pronto!")
    print("Falta só: logar o Claude Code no terminal (rode `claude` e digite /login) e abrir o claudinho.pyw.")
    if not shutil.which("claude"):
        print("ATENÇÃO: não achei o comando `claude`. Instale o Claude Code antes de usar o chat.")


if __name__ == "__main__":
    main()
