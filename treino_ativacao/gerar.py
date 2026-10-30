"""Gera as amostras do treino da palavra de ativação ("Ei Claudinho"): vozes sintéticas falando as frases de chamada
(positivos) e frases parecidas que NÃO podem acordar ("Fala, Claude", "Ei Cláudio", "o Claudinho é legal").

Roda no Python do Claudinho (usa o Kokoro, o Piper e o Edge que ele já tem):

    python treino_ativacao/gerar.py            gera o que falta (pode parar e rodar de novo: continua)
    python treino_ativacao/gerar.py edge       só uma fonte (piper, kokoro, edge): dá pra rodar em paralelo

Saída em ~/.claudinho/ativacao/treino/{positivos,negativos}/<fonte>__<voz>__<n>.wav, 16 kHz mono. A voz vai no nome
do arquivo: o treino separa vozes inteiras pra conferir (uma voz que ele nunca ouviu tem que acordar também).
"""
import asyncio
import json
import os
import random
import sys
import wave
from pathlib import Path

import numpy as np

DADOS = Path(os.environ.get("CLAUDINHO_DADOS") or Path.home() / ".claudinho")
SAIDA = DADOS / "ativacao" / "treino"
VOZES = DADOS / "vozes"
TAXA = 16000
CHAMADAS_PADRAO = ["Ei Claudinho", "Fala Claudinho", "Oi Claudinho", "Olá Claudinho"]
# parecidas, que não podem acordar: outros nomes, o Claude (você fala "Fala, Claude" ditando pro Claude Code) e o
# Claudinho no meio da frase (falar DELE não é chamar)
PARECIDAS = [
    "Fala, Claude", "Ei, Claude", "Oi, Claude", "Olá, Claude", "Claude, roda os testes", "Fala, Claude, tudo certo?",
    "Ei, Cláudio", "Fala, Cláudio", "Oi, Cláudia", "Olá, Claudete", "Ei, carinho", "Fala, caminho", "Oi, cadinho",
    "Olá, gordinho", "Ei, Paulinho", "Fala, Juninho", "Oi, Fabinho", "Ei, vizinho", "Fala, sozinho",
    "O Claudinho é muito fofo", "Vou pedir pro Claudinho depois", "Cadê o Claudinho?", "Esse Claudinho aí",
    "Ei", "Fala aí", "Oi, tudo bem?", "Olá, pessoal", "Fala, galera", "Ei, você", "Claro, caminho livre",
    "Cláudio, me liga depois", "Fala com o Cláudio", "Claudinho", "o Claudinho",
]
MISTURAS = 24                # vozes do Kokoro misturadas duas a duas (falantes novos)
PARECIDAS_POR_VOZ = 6        # quantas frases parecidas cada voz do Kokoro fala
GERAIS = 40    # frases comuns do banco do Claudinho, faladas por vozes sorteadas (negativos de fala qualquer)


def chamadas():
    """As frases de chamada do painel (Voz → Frases de chamada), ou as padrão."""
    try:
        cfg = json.loads((DADOS / "config.json").read_text(encoding="utf-8"))
        lista = [a for a in cfg.get("voz_apelidos") or [] if isinstance(a, str) and "claudinho" in a.lower()]
        return lista or CHAMADAS_PADRAO
    except (OSError, ValueError):
        return CHAMADAS_PADRAO


def frases_gerais(n):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import frases as banco

    def achatar(o):
        if isinstance(o, str):
            yield o
        elif isinstance(o, dict):
            for v in o.values():
                yield from achatar(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                yield from achatar(v)
    todas = [f for f in dict.fromkeys(achatar([getattr(banco, x) for x in dir(banco) if not x.startswith("_")]))
             if isinstance(f, str) and "{" not in f and "claudinho" not in f.lower() and 3 <= len(f.split()) <= 16]
    random.Random(7).shuffle(todas)
    return todas[:n]


def para_16k(audio, taxa):
    audio = np.asarray(audio, dtype="float32").reshape(-1)
    if taxa != TAXA:
        n = int(len(audio) * TAXA / taxa)
        audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype("float32")
    pico = float(np.max(np.abs(audio))) if len(audio) else 0.0
    return audio / pico * 0.9 if pico > 0 else audio


def gravar(caminho, audio):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".tmp")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
    os.replace(tmp, caminho)


class Gerador:
    def __init__(self):
        self.feitos = 0

    def salvar(self, tipo, fonte, voz, n, sintetizar):
        caminho = SAIDA / tipo / f"{fonte}__{voz}__{n}.wav"
        if caminho.exists():
            return
        try:
            audio, taxa = sintetizar()
        except Exception as e:
            print(f"  falhou {caminho.name}: {e}", flush=True)
            return
        gravar(caminho, para_16k(audio, taxa))
        self.feitos += 1
        if self.feitos % 50 == 0:
            print(f"  {self.feitos} gerados", flush=True)


def kokoro(g, pos, neg, gerais):
    from kokoro_onnx import Kokoro
    k = Kokoro(str(VOZES / "kokoro" / "kokoro-v1.0.onnx"), str(VOZES / "kokoro" / "voices-v1.0.bin"))
    vozes = k.get_voices()
    rnd = random.Random(1)
    # misturas de duas vozes: falantes "novos" que nenhuma voz pronta tem
    misturas = [(rnd.choice(vozes), rnd.choice(vozes), round(rnd.uniform(0.3, 0.7), 2)) for _ in range(MISTURAS)]

    def falar(texto, voz, velocidade):
        if isinstance(voz, tuple):
            a, b, peso = voz
            estilo = k.get_voice_style(a) * peso + k.get_voice_style(b) * (1 - peso)
            return k.create(texto, voice=estilo, speed=velocidade, lang="pt-br")
        return k.create(texto, voice=voz, speed=velocidade, lang="pt-br")

    print(f"Kokoro: {len(vozes)} vozes + {len(misturas)} misturas", flush=True)
    for i, voz in enumerate(vozes + misturas):
        nome = voz if isinstance(voz, str) else f"mix{i}"
        for j, frase in enumerate(pos):
            for v, vel in enumerate((0.9, 1.1) if isinstance(voz, str) else (rnd.uniform(0.85, 1.2),)):
                g.salvar("positivos", "kokoro", nome, f"{j}_{v}", lambda f=frase, vel=vel: falar(f, voz, vel))
        for j in rnd.sample(range(len(neg)), PARECIDAS_POR_VOZ):
            g.salvar("negativos", "kokoro", nome, f"p{j}", lambda f=neg[j]: falar(f, voz, rnd.uniform(0.9, 1.15)))
    for j, frase in enumerate(gerais):
        voz = rnd.choice(vozes)
        g.salvar("negativos", "kokoro", f"geral-{voz}", f"g{j}", lambda f=frase, v=voz: falar(f, v, 1.0))


def piper(g, pos, neg):
    from piper import PiperVoice, SynthesisConfig
    modelos = sorted(VOZES.glob("pt_BR-*.onnx")) + sorted((VOZES / "minhas").glob("*/voz.onnx"))
    rnd = random.Random(2)
    print(f"Piper: {len(modelos)} vozes", flush=True)
    for modelo in modelos:
        voz = PiperVoice.load(str(modelo))
        nome = modelo.parent.name if modelo.name == "voz.onnx" else modelo.stem.split("-")[1]

        def falar(texto, ajuste):
            pedacos = [c.audio_float_array for c in voz.synthesize(texto, ajuste)]
            return np.concatenate(pedacos), voz.config.sample_rate
        sua = modelo.name == "voz.onnx"   # a voz própria (treinada com a sua): vale mais variações dela
        for j, frase in enumerate(pos):
            for v in range(25 if sua else 6):
                ajuste = SynthesisConfig(length_scale=rnd.uniform(0.8, 1.25), noise_scale=rnd.uniform(0.4, 0.9),
                                         noise_w_scale=rnd.uniform(0.5, 1.0))
                g.salvar("positivos", "piper", nome, f"{j}_{v}", lambda f=frase, a=ajuste: falar(f, a))
        for j, frase in enumerate(neg):
            for v in range(3 if sua else 1):
                ajuste = SynthesisConfig(length_scale=rnd.uniform(0.85, 1.15), noise_scale=rnd.uniform(0.5, 0.8))
                g.salvar("negativos", "piper", nome, f"p{j}" + (f"_{v}" if v else ""), lambda f=frase, a=ajuste: falar(f, a))


def edge(g, pos, neg):
    import edge_tts
    import miniaudio
    vozes = [v["ShortName"] for v in asyncio.run(edge_tts.list_voices())
             if v["Locale"].startswith("pt-") or "Multilingual" in v["ShortName"]]
    rnd = random.Random(3)
    print(f"Edge: {len(vozes)} vozes", flush=True)

    def falar(texto, voz, rate, pitch):
        async def baixar():
            mp3 = b""
            async for pedaco in edge_tts.Communicate(texto, voz, rate=f"{rate:+d}%", pitch=f"{pitch:+d}Hz").stream():
                if pedaco["type"] == "audio":
                    mp3 += pedaco["data"]
            return mp3
        dados = miniaudio.decode(asyncio.run(baixar()), output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1,
                                 sample_rate=24000)
        return np.frombuffer(dados.samples, dtype="float32"), 24000
    for voz in vozes:
        nome = voz.replace("Neural", "").replace("Multilingual", "M")
        for j, frase in enumerate(pos):
            for v in range(3):
                rate, pitch = rnd.randint(-15, 20), rnd.randint(-12, 12)
                g.salvar("positivos", "edge", nome, f"{j}_{v}", lambda f=frase, r=rate, p=pitch: falar(f, voz, r, p))
        for j in rnd.sample(range(len(neg)), 14):
            g.salvar("negativos", "edge", nome, f"p{j}", lambda f=neg[j]: falar(f, voz, 0, 0))


def main():
    pos, neg = chamadas(), PARECIDAS
    print("chamadas:", pos, flush=True)
    g = Gerador()
    gerais = frases_gerais(GERAIS)
    fontes = {"piper": lambda: piper(g, pos, neg), "kokoro": lambda: kokoro(g, pos, neg, gerais),
              "edge": lambda: edge(g, pos, neg)}
    for nome, etapa in fontes.items():
        if len(sys.argv) > 1 and nome not in sys.argv[1:]:
            continue
        try:
            etapa()
        except Exception as e:   # uma fonte faltando (sem internet pro Edge, sem Kokoro) não para as outras
            print("fonte falhou:", e, flush=True)
    total = {t: len(list((SAIDA / t).glob("*.wav"))) for t in ("positivos", "negativos")}
    print("pronto:", total, flush=True)


if __name__ == "__main__":
    main()
