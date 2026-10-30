"""Amostras da palavra de ativação na SUA voz (clonada pelo Chatterbox a partir da referência da voz própria):
as chamadas ("Ei Claudinho"…) como positivos e as parecidas ("Fala, Claude"…) como negativos.

Roda no ambiente da clonagem (precisa de CUDA):

    ~/.claudinho/vozes/clonagem/.venv/Scripts/python.exe treino_ativacao/gerar_chatterbox.py

Usa a referência de ~/.claudinho/vozes/minhas/*/referencia.wav. Pode parar e rodar de novo: continua. Opcional: precisa
de ~4 GB livres na placa (com o papel de parede animado e o navegador abertos numa de 8 GB ele trava); sem ele, a sua
voz entra pelo Piper treinado com ela (gerar.py piper).
"""
import random
import sys
from pathlib import Path

import torch

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import gerar  # noqa: E402

POR_CHAMADA = 25
POR_PARECIDA = 2


def main():
    if not torch.cuda.is_available():
        sys.exit("precisa de placa de vídeo NVIDIA (CUDA)")
    referencias = sorted((gerar.VOZES / "minhas").glob("*/referencia.wav"))
    if not referencias:
        sys.exit("nenhuma voz própria com referencia.wav")
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    modelo = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
    rnd = random.Random(5)
    g = gerar.Gerador()

    def falar(frase, ref):
        wav = modelo.generate(frase, language_id="pt", audio_prompt_path=str(ref),
                              exaggeration=rnd.uniform(0.3, 0.8), cfg_weight=rnd.uniform(0.3, 0.7),
                              temperature=rnd.uniform(0.6, 1.0))
        return wav.squeeze(0).cpu().numpy(), modelo.sr
    for ref in referencias:
        nome = ref.parent.name
        print("voz:", nome, flush=True)
        for j, frase in enumerate(gerar.chamadas()):
            for v in range(POR_CHAMADA):
                g.salvar("positivos", "chatterbox", nome, f"{j}_{v}", lambda f=frase: falar(f, ref))
        for j, frase in enumerate(gerar.PARECIDAS):
            if "claudinho" in frase.lower():
                continue
            for v in range(POR_PARECIDA):
                g.salvar("negativos", "chatterbox", nome, f"p{j}_{v}", lambda f=frase: falar(f, ref))
    print("pronto:", g.feitos, "novos", flush=True)


if __name__ == "__main__":
    main()
