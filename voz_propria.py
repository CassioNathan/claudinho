"""Ajudante da voz própria ("Minha voz"): roda no ambiente do Chatterbox (~/.claudinho/vozes/clonagem), à parte do
Claudinho, porque precisa do torch e da placa de vídeo. O fala.py abre ele quando precisa e conversa por linhas JSON:

    entra: {"texto": "Oi!", "voz": "C:/.../minhas/cassio"}       sai: {"ok": true, "arquivo": "...npy", "taxa": 24000}

A voz é uma pasta com referencia.wav (o áudio que a pessoa mandou, já limpo). A "impressão" da voz é tirada uma vez e
fica guardada (conds.pt) pra não clonar de novo a cada vez que liga. Fica parado 3 min sem falar: sai sozinho e solta a
placa de vídeo (o fala.py abre de novo na próxima frase). Pesa ~7-8 GB de memória reservada, então sai NA HORA quando o
Claudinho fecha (vigia o processo dele, `--pai <pid>`): ajudante sobrando de um Claudinho que já fechou enchia a memória
do Windows. Tudo local: nada sai do PC.
"""
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

PARADO = 3 * 60
ultimo = time.time()


def vivo(pid):
    """O processo `pid` ainda está rodando? (Windows: abre e pergunta o código de saída; 259 = ainda rodando.)"""
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    codigo = ctypes.c_ulong()
    k.GetExitCodeProcess(h, ctypes.byref(codigo))
    k.CloseHandle(h)
    return codigo.value == 259


def vigiar(pai):
    while True:
        time.sleep(3)
        if time.time() - ultimo > PARADO or (pai and not vivo(pai)):
            os._exit(0)


def main():
    global ultimo
    import numpy as np
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS, Conditionals

    pai = int(sys.argv[sys.argv.index("--pai") + 1]) if "--pai" in sys.argv else 0
    threading.Thread(target=vigiar, args=(pai,), daemon=True).start()
    aparelho = "cuda" if torch.cuda.is_available() else "cpu"
    modelo = ChatterboxMultilingualTTS.from_pretrained(device=aparelho)
    atual = None
    saida = Path(tempfile.gettempdir()) / "claudinho-voz"
    saida.mkdir(exist_ok=True)
    print(json.dumps({"pronto": True, "aparelho": aparelho}), flush=True)
    for linha in sys.stdin:
        ultimo = time.time()
        try:
            pedido = json.loads(linha)
            pasta = Path(pedido["voz"])
            if pasta != atual:   # outra voz (ou a primeira): usa a impressão guardada, ou tira e guarda
                conds = pasta / "conds.pt"
                if conds.exists():
                    modelo.conds = Conditionals.load(conds, map_location=aparelho).to(aparelho)
                else:
                    modelo.prepare_conditionals(str(pasta / "referencia.wav"))
                    modelo.conds.save(conds)
                atual = pasta
            wav = modelo.generate(pedido["texto"], language_id="pt")
            arquivo = saida / f"{time.time_ns()}.npy"
            np.save(arquivo, wav.squeeze(0).cpu().numpy().astype("float32"))
            print(json.dumps({"ok": True, "arquivo": str(arquivo), "taxa": modelo.sr}), flush=True)
        except Exception as e:
            print(json.dumps({"ok": False, "erro": str(e)}), flush=True)
        ultimo = time.time()


if __name__ == "__main__":
    main()
    os._exit(0)   # a entrada fechou (o Claudinho saiu): não espera nada, solta a memória já
