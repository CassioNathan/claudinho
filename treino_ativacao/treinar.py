"""Treina o detector da palavra de ativação ("Ei Claudinho") e exporta ~/.claudinho/ativacao/claudinho.onnx.

Roda no ambiente da clonagem (tem torch com CUDA):

    ~/.claudinho/vozes/clonagem/.venv/Scripts/python.exe treino_ativacao/treinar.py

Antes: gerar.py (as vozes falando) e baixar_negativos.py (as ~2000 h de áudio qualquer do openWakeWord).

    1. cada positivo vira várias versões (velocidade, volume, ruído, eco, conversa no fundo), num clipe de 2 s com a
       chamada terminando perto do fim → os últimos 16 embeddings são o exemplo
    2. negativos: as frases parecidas, frases comuns (inclusive na sua voz clonada) e os pedaços prontos do
       openWakeWord, em janelas de 16
    3. classificador pequeno (2 camadas) na GPU
    4. confere com vozes que ele nunca viu e com ~11 h de áudio de validação (quantas vezes por hora acordaria à
       toa), escolhe o limiar e exporta
"""
import json
import os
import random
import sys
import wave
import zlib
from pathlib import Path

import numpy as np
import torch
from torch import nn

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))
import ativacao  # noqa: E402
import gerar  # noqa: E402

TREINO = ativacao.PASTA / "treino"
CLONAGEM = ativacao.DADOS / "vozes" / "clonagem" / "trabalho"
TAXA = 16000
CLIPE = 2 * TAXA                 # 2 s → exatamente 16 embeddings
VERSOES_POSITIVO = 8
VERSOES_NEGATIVO = 2
PASSOS = 25000
LOTE = 512
# o limiar escolhido dispara à toa no máximo isso por hora (no áudio de validação). O detector é só o porteiro: cada
# disparo faz o Whisper conferir a frase (o que antes ele fazia com TODA fala da sala), então vale acertar mais chamadas
FP_POR_HORA_MAX = 8
SEMENTE = 42
PESO_NEGATIVO_FINAL = 40         # o peso dos negativos vai de 1 até isso ao longo do treino


def ler(caminho):
    with wave.open(str(caminho), "rb") as w:
        taxa, dados = w.getframerate(), w.readframes(w.getnframes())
    audio = np.frombuffer(dados, dtype="<i2").astype("float32") / 32768
    if taxa != TAXA:
        audio = np.interp(np.linspace(0, len(audio) - 1, int(len(audio) * TAXA / taxa)), np.arange(len(audio)), audio)
    return audio.astype("float32")


def aparar(audio, limite=0.02):
    """Tira o silêncio das pontas (a TTS deixa um pouco): a chamada fica no lugar certo do clipe."""
    alto = np.where(np.abs(audio) > limite * max(1e-6, float(np.max(np.abs(audio)))))[0]
    return audio[max(0, alto[0] - 800):alto[-1] + 800] if len(alto) else audio


def voz_do_arquivo(caminho):
    fonte, voz, _ = caminho.stem.split("__")
    return f"{fonte}:{voz}"


def separada(voz):
    """~1 em 7 vozes fica de fora do treino, só pra conferir."""
    return zlib.crc32(voz.encode()) % 7 == 0


# ---------- aumentar os dados ----------
def ruido(n, rnd):
    tipo = rnd.choice(("branco", "rosa", "marrom"))
    r = np.random.default_rng(rnd.randint(0, 1 << 30)).standard_normal(n).astype("float32")
    if tipo == "rosa":
        r = np.cumsum(r) * 0.02 + r * 0.5
        r -= np.convolve(r, np.ones(400) / 400, mode="same")
    elif tipo == "marrom":
        r = np.cumsum(r)
        r -= np.convolve(r, np.ones(800) / 800, mode="same")
    return r / (np.std(r) + 1e-6)


def eco(audio, rnd):
    """Sala: resposta ao impulso sintética (ruído com decaimento exponencial)."""
    rt60 = rnd.uniform(0.15, 0.7)
    n = int(rt60 * TAXA)
    t = np.arange(n) / TAXA
    rir = np.random.default_rng(rnd.randint(0, 1 << 30)).standard_normal(n) * np.exp(-6.9 * t / rt60)
    rir[0] = 1.0
    saida = np.convolve(audio, rir)[:len(audio)]
    return saida / (np.max(np.abs(saida)) + 1e-6) * np.max(np.abs(audio))


def velocidade(audio, fator):
    n = int(len(audio) / fator)
    return np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype("float32")


def misturar(audio, fundo, snr_db):
    if fundo is None or not len(fundo):
        return audio
    if len(fundo) < len(audio):
        fundo = np.tile(fundo, len(audio) // len(fundo) + 1)
    fundo = fundo[:len(audio)]
    p_a, p_f = np.mean(audio ** 2) + 1e-9, np.mean(fundo ** 2) + 1e-9
    return audio + fundo * np.sqrt(p_a / (p_f * 10 ** (snr_db / 10)))


def versao(audio, rnd, fala_fundo, no_fim=True):
    """Uma versão "do mundo real" da fala, num clipe de 2 s (ou mais, se a fala for maior)."""
    audio = velocidade(audio, rnd.uniform(0.88, 1.12))
    if rnd.random() < 0.5:
        audio = eco(audio, rnd)
    tamanho = max(CLIPE, len(audio) + TAXA // 4)
    clipe = np.zeros(tamanho, dtype="float32")
    if no_fim:   # a chamada termina entre 0 e 0,25 s antes do fim: é aí que o detector tem que disparar
        fim = tamanho - rnd.randint(0, TAXA // 4)
        clipe[max(0, fim - len(audio)):fim] = audio[-min(len(audio), fim):]
    else:
        inicio = rnd.randint(0, tamanho - len(audio))
        clipe[inicio:inicio + len(audio)] = audio
    clipe = misturar(clipe, ruido(len(clipe), rnd), rnd.uniform(8, 35))
    if fala_fundo and rnd.random() < 0.4:   # gente falando no fundo, mais baixo
        clipe = misturar(clipe, rnd.choice(fala_fundo), rnd.uniform(10, 22))
    clipe *= rnd.uniform(0.1, 1.0) / (np.max(np.abs(clipe)) + 1e-6)
    return (np.clip(clipe, -1, 1) * 32767).astype("int16")


# ---------- atributos ----------
def janelas(emb):
    """Todas as janelas de 16 embeddings de um clipe: (n, 16, 96)."""
    if len(emb) < ativacao.JANELA:
        return np.zeros((0, ativacao.JANELA, 96), dtype="float32")
    idx = np.arange(len(emb) - ativacao.JANELA + 1)[:, None] + np.arange(ativacao.JANELA)
    return emb[idx]


def montar(ext, rnd):
    positivos = sorted((TREINO / "positivos").glob("*.wav"))
    proibidas = {i for i, f in enumerate(gerar.PARECIDAS) if "claudinho" in f.lower()}  # quem diz "Claudinho" o
    negativos = [c for c in sorted((TREINO / "negativos").glob("*.wav"))              # Whisper filtra depois
                 if not (c.stem.split("__")[2].startswith("p") and int(c.stem.split("__")[2][1:]) in proibidas)]
    sua_voz = sorted((CLONAGEM).glob("*/wavs/*.wav"))
    print(f"positivos {len(positivos)}, negativos {len(negativos)}, sua voz (fala comum) {len(sua_voz)}", flush=True)
    fala_fundo = [ler(c) for c in rnd.sample(sua_voz + negativos, min(150, len(sua_voz) + len(negativos)))]
    dados = {k: [] for k in ("pos", "pos_conf", "neg", "neg_conf")}
    for i, c in enumerate(positivos):
        conf = separada(voz_do_arquivo(c))
        audio = aparar(ler(c))
        for _ in range(2 if conf else VERSOES_POSITIVO):
            emb = ext.embeddings(versao(audio, rnd, fala_fundo))
            dados["pos_conf" if conf else "pos"].append(emb[-ativacao.JANELA:])
        if i % 200 == 0:
            print(f"  positivos {i}/{len(positivos)}", flush=True)
    for i, c in enumerate(negativos + sua_voz):
        conf = c in negativos and separada(voz_do_arquivo(c))
        audio = aparar(ler(c))
        for _ in range(1 if conf else VERSOES_NEGATIVO):
            dados["neg_conf" if conf else "neg"].append(janelas(ext.embeddings(versao(audio, rnd, None, no_fim=False))))
        if i % 300 == 0:
            print(f"  negativos {i}/{len(negativos) + len(sua_voz)}", flush=True)
    for _ in range(300):   # silêncio e ruído puro
        n = (ruido(CLIPE, rnd) * rnd.uniform(0.001, 0.3) * 32767).clip(-32767, 32767).astype("int16")
        dados["neg"].append(janelas(ext.embeddings(n)))
    return {k: (np.stack(v) if k.startswith("pos") else np.concatenate(v)).astype("float32") for k, v in dados.items()}


# ---------- modelo ----------
class Classificador(nn.Module):
    def __init__(self):
        super().__init__()
        self.rede = nn.Sequential(nn.Flatten(), nn.Dropout(0.3), nn.Linear(ativacao.JANELA * 96, 128), nn.LayerNorm(128),
                                  nn.ReLU(), nn.Dropout(0.3), nn.Linear(128, 128), nn.LayerNorm(128), nn.ReLU(),
                                  nn.Linear(128, 1))

    def forward(self, x):
        return torch.sigmoid(self.rede(x))


def notas(modelo, x, lote=8192):
    modelo.eval()
    saida = []
    with torch.no_grad():
        for i in range(0, len(x), lote):
            saida.append(modelo(torch.as_tensor(np.asarray(x[i:i + lote], dtype="float32")).cuda()).cpu().numpy().ravel())
    modelo.train()
    return np.concatenate(saida) if saida else np.zeros(0)


def treinar(d, acav):
    torch.manual_seed(SEMENTE)
    modelo = Classificador().cuda()
    otim = torch.optim.AdamW(modelo.parameters(), lr=1e-3, weight_decay=1e-3)
    agenda = torch.optim.lr_scheduler.OneCycleLR(otim, max_lr=1e-3, total_steps=PASSOS)
    pos, neg = torch.as_tensor(d["pos"]).cuda(), torch.as_tensor(d["neg"]).cuda()
    acav_t = torch.as_tensor(acav)   # fica na RAM: pega um lote por vez
    rng = np.random.default_rng(SEMENTE)
    for passo in range(PASSOS):
        # um quarto de chamadas, um quarto de frases (parecidas e comuns) e metade de áudio qualquer
        ip = torch.randint(len(pos), (LOTE // 4,), device="cuda")
        ineg = torch.randint(len(neg), (LOTE // 4,), device="cuda")
        ia = torch.as_tensor(rng.integers(0, len(acav_t), LOTE // 2))
        x = torch.cat([pos[ip], neg[ineg], acav_t[ia].float().cuda()])
        y = torch.cat([torch.ones(len(ip)), torch.zeros(len(ineg) + len(ia))]).cuda()
        # o peso dos negativos sobe com o tempo: no fim, acordar à toa custa bem mais que perder uma chamada
        peso = torch.where(y > 0, 1.0, 1.0 + PESO_NEGATIVO_FINAL * passo / PASSOS)
        perda = (nn.functional.binary_cross_entropy(modelo(x).squeeze(1), y, reduction="none") * peso).mean()
        otim.zero_grad()
        perda.backward()
        otim.step()
        agenda.step()
        if passo % 1000 == 0:
            print(f"  passo {passo}: perda {perda.item():.4f}", flush=True)
    return modelo


def fp_por_hora(n_notas, limiar, horas):
    """Disparos à toa por hora: notas seguidas acima do limiar contam como um disparo só."""
    acima = n_notas >= limiar
    disparos = int(np.sum(acima[1:] & ~acima[:-1]) + (acima[0] if len(acima) else 0))
    return disparos / horas


def conferir(modelo, d):
    val = np.load(TREINO / gerar_validacao(), mmap_mode="r")
    horas = len(val) * 0.08 / 3600
    nv = []
    for i in range(0, len(val) - ativacao.JANELA, 100_000):
        bloco = np.asarray(val[i:i + 100_000 + ativacao.JANELA - 1], dtype="float32")
        nv.append(notas(modelo, janelas(bloco)))
    nv = np.concatenate(nv)
    npos, nneg = notas(modelo, d["pos_conf"]), notas(modelo, d["neg_conf"])
    tabela = []
    for limiar in np.arange(0.05, 0.99, 0.01):
        tabela.append((round(float(limiar), 2), float(np.mean(npos >= limiar)), fp_por_hora(nv, limiar, horas),
                       float(np.mean(nneg >= limiar))))
    aceitos = [t for t in tabela if t[2] <= FP_POR_HORA_MAX]
    escolhido = max(aceitos, key=lambda t: (t[1], -t[0])) if aceitos else tabela[-1]
    print(f"validação: {horas:.1f} h de áudio qualquer; vozes nunca vistas: {len(npos)} chamadas, {len(nneg)} janelas "
          "parecidas", flush=True)
    for t in tabela[::10] + [escolhido]:
        print(f"  limiar {t[0]:.2f}: acerta {t[1]:.0%} das chamadas, {t[2]:.2f} disparos/h à toa, "
              f"{t[3]:.2%} das parecidas", flush=True)
    return escolhido


def gerar_validacao():
    import baixar_negativos
    return baixar_negativos.VALIDACAO


def exportar(modelo, escolhido, d):
    modelo = modelo.cpu().eval()
    tmp = ativacao.MODELO.with_suffix(".tmp.onnx")
    torch.onnx.export(modelo, torch.zeros(1, ativacao.JANELA, 96), str(tmp), input_names=["entrada"],
                      output_names=["nota"], dynamic_axes={"entrada": {0: "lote"}}, dynamo=False, opset_version=17)
    os.replace(tmp, ativacao.MODELO)
    limiar, acerto, fp, parecidas = escolhido
    info = {"limiar": limiar, "acerto": round(acerto, 3), "disparos_por_hora": round(fp, 3),
            "parecidas": round(parecidas, 4), "positivos": int(len(d["pos"])), "negativos": int(len(d["neg"])),
            "chamadas": gerar.chamadas()}
    ativacao.INFO.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print("exportado:", ativacao.MODELO, info, flush=True)


def main():
    if not torch.cuda.is_available():
        sys.exit("treinar precisa de placa de vídeo NVIDIA (CUDA)")
    ativacao.baixar_bases()
    rnd = random.Random(SEMENTE)
    cache = TREINO / "atributos.npz"
    if cache.exists() and "--refazer" not in sys.argv:
        d = dict(np.load(cache))
        print("atributos do cache:", {k: v.shape for k, v in d.items()}, flush=True)
    else:
        d = montar(ativacao.Extrator(), rnd)
        np.savez(cache, **d)
    acav = np.load(TREINO / "acav_pedacos.npy", mmap_mode="r")
    acav = np.asarray(acav)   # ~1,5 GB em float16
    print(f"treinando: {len(d['pos'])} positivos, {len(d['neg'])} negativos + {len(acav)} do openWakeWord", flush=True)
    modelo = treinar(d, acav)
    escolhido = conferir(modelo, d)
    exportar(modelo, escolhido, d)


if __name__ == "__main__":
    main()
