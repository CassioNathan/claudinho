# Receita do PyInstaller: gera dist/Claudinho/ com dois executáveis que dividem a mesma pasta _internal:
#   Claudinho.exe       o mascote (sem console)
#   claudinho-cli.exe   o ajudante de linha de comando (música/abrir pro chat, o aviso do Claude Code e o MCP)
# Rode pelo empacotar.py (ele gera o ícone antes e faz o zip depois).
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

ocultos = collect_submodules("winrt") + ["pystray._win32", "tela", "teclas", "projetos", "rotinas", "programas",
                                         "claudinho_mcp"]  # importados só na hora (ver_tela da API, MCP)
dados = (collect_data_files("customtkinter") + collect_data_files("ytmusicapi")
         + [("painel.html", "."), ("conversa.html", "."), ("extensao", "extensao")])
binarios = []
# partes que o Claudinho não usa e nem importam sem pacotes extras (treino do Piper, ferramentas do onnxruntime, CLI do mcp)
SEM = ("mcp.cli", "piper.train", "onnxruntime.quantization", "onnxruntime.tools", "onnxruntime.transformers")
# voz (Whisper, Piper, Kokoro, Microsoft) e o servidor MCP: trazem modelos, dlls e dados que o PyInstaller não acha sozinho
for pacote in ["faster_whisper", "ctranslate2", "piper", "kokoro_onnx", "espeakng_loader", "onnxruntime",
               "sounddevice", "_sounddevice_data", "edge_tts", "miniaudio", "mcp", "phonemizer", "tokenizers"]:
    d, b, h = collect_all(pacote, filter_submodules=lambda nome: not nome.startswith(SEM))
    dados += d
    binarios += b
    ocultos += h
# torch, numba e scipy vêm de partes de treino do Piper e do onnxruntime: o Claudinho só usa os modelos prontos
fora = ["matplotlib", "pandas", "IPython", "pytest", "torch", "torchaudio", "numba", "llvmlite", "scipy", "sympy",
        "transformers", "tensorboard"]

mascote = Analysis(["claudinho.pyw"], pathex=["hook"], hiddenimports=ocultos, datas=dados, binaries=binarios,
                   excludes=fora)
ajudante = Analysis(["cli.py"], pathex=["hook"], hiddenimports=ocultos, excludes=fora)

exe_mascote = EXE(PYZ(mascote.pure), mascote.scripts, [], exclude_binaries=True, name="Claudinho",
                  console=False, icon="build/claudinho.ico")
exe_ajudante = EXE(PYZ(ajudante.pure), ajudante.scripts, [], exclude_binaries=True, name="claudinho-cli",
                   console=True, icon="build/claudinho.ico")
COLLECT(exe_mascote, mascote.binaries, mascote.datas, exe_ajudante, ajudante.binaries, ajudante.datas,
        name="Claudinho")
