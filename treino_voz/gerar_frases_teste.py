"""Treino-teste do Piper: gera ~24 frases com a voz PADRÃO do Chatterbox (sem clonar ninguém) só pra conferir o pipeline."""
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import torchaudio

warnings.filterwarnings("ignore")
SAIDA = Path(sys.argv[1])
(SAIDA / "wavs").mkdir(parents=True, exist_ok=True)
FRASES = [
    "Oi! Eu sou o Claudinho, tudo bem com você?",
    "Pronto, terminei o que você pediu.",
    "Hoje o dia está bonito, vamos programar juntos?",
    "Não encontrei esse arquivo na pasta do projeto.",
    "Quer que eu abra o programa para você?",
    "O servidor subiu e já está respondendo normalmente.",
    "Achei um erro na linha quarenta e dois do código.",
    "Vou olhar a tela e te conto o que estou vendo.",
    "Essa música é muito boa, gostei bastante.",
    "Espera um instante, estou pensando aqui.",
    "A conversa acabou, se precisar é só me chamar.",
    "Foram duzentos e cinquenta e três pedidos hoje.",
    "O botão está com uma cor um pouco diferente do outro.",
    "Sempre que quiser, eu também posso abrir o navegador.",
    "Desculpa, eu não entendi muito bem o que você disse.",
    "Já salvei tudo, pode ficar tranquilo.",
    "Mais cinco minutos e o trabalho termina.",
    "Que legal, deu tudo certo dessa vez!",
    "Qual projeto você quer que eu abra agora?",
    "Estou escutando, pode falar quando quiser.",
    "A reunião começa em dez minutos, não esquece.",
    "Passei o dia inteiro olhando para essa linha de código.",
    "Ontem choveu muito, e hoje o céu está aberto.",
    "Posso resumir o que está na tela, se você quiser.",
]
from chatterbox.mtl_tts import ChatterboxMultilingualTTS  # noqa: E402

modelo = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
linhas, t0 = [], time.time()
for i, frase in enumerate(FRASES):
    wav = modelo.generate(frase, language_id="pt")          # [1, n] float a 24 kHz
    wav = torchaudio.functional.resample(wav.cpu(), modelo.sr, 22050)
    pcm = (wav.squeeze(0).clamp(-1, 1).numpy() * 32767).astype(np.int16)
    nome = f"f{i:03d}"
    import wave
    with wave.open(str(SAIDA / "wavs" / f"{nome}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(pcm.tobytes())
    linhas.append(f"{nome}|{frase}")
    print(f"{i + 1}/{len(FRASES)} {len(pcm) / 22050:.1f}s de fala, {time.time() - t0:.0f}s decorridos", flush=True)
(SAIDA / "metadata.csv").write_text("\n".join(linhas) + "\n", encoding="utf-8")
print("pronto", flush=True)
