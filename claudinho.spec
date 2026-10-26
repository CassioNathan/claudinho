# Receita do PyInstaller: gera dist/Claudinho/ com dois executáveis que dividem a mesma pasta _internal:
#   Claudinho.exe       o mascote (sem console)
#   claudinho-cli.exe   o ajudante de linha de comando (música/abrir pro chat, e o aviso do Claude Code)
# Rode pelo empacotar.py (ele gera o ícone antes e faz o zip depois).
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ocultos = collect_submodules("winrt") + ["pystray._win32", "tela"]  # tela: importado só na hora (ver_tela da API)
dados = (collect_data_files("customtkinter") + collect_data_files("ytmusicapi")
         + [("painel.html", "."), ("conversa.html", "."), ("extensao", "extensao")])
fora = ["matplotlib", "numpy", "pandas", "scipy", "IPython", "pytest"]

mascote = Analysis(["claudinho.pyw"], pathex=["hook"], hiddenimports=ocultos, datas=dados, excludes=fora)
ajudante = Analysis(["cli.py"], pathex=["hook"], hiddenimports=ocultos, excludes=fora)

exe_mascote = EXE(PYZ(mascote.pure), mascote.scripts, [], exclude_binaries=True, name="Claudinho",
                  console=False, icon="build/claudinho.ico")
exe_ajudante = EXE(PYZ(ajudante.pure), ajudante.scripts, [], exclude_binaries=True, name="claudinho-cli",
                   console=True, icon="build/claudinho.ico")
COLLECT(exe_mascote, mascote.binaries, mascote.datas, exe_ajudante, ajudante.binaries, ajudante.datas,
        name="Claudinho")
