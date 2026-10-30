"""Baixa os negativos prontos do openWakeWord (features de ~2000 h de áudio qualquer, já passadas pelo embedding).

O arquivo inteiro tem 17 GB; aqui vêm só PEDACOS pedaços espalhados (download por faixa de bytes: o .npy é um
cabeçalho + as linhas em sequência), ~1,5 GB, e o conjunto de validação (~11 h de áudio, 185 MB) que mede quantas
vezes por hora ele acordaria à toa. Fica em ~/.claudinho/ativacao/treino/ (fora do repositório).

    python treino_ativacao/baixar_negativos.py
"""
import ast
import os
import urllib.request
from pathlib import Path

import numpy as np

DADOS = Path(os.environ.get("CLAUDINHO_DADOS") or Path.home() / ".claudinho")
PASTA = DADOS / "ativacao" / "treino"
BASE = "https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/main/"
ACAV = "openwakeword_features_ACAV100M_2000_hrs_16bit.npy"
VALIDACAO = "validation_set_features.npy"
PEDACOS = 6
LINHAS_POR_PEDACO = 80_000      # 80 mil janelas de 1,28 s por pedaço (~240 MB cada em float16)


def faixa(url, inicio, fim):
    req = urllib.request.Request(url, headers={"Range": f"bytes={inicio}-{fim}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def cabecalho(url):
    bruto = faixa(url, 0, 1023)
    tam = int.from_bytes(bruto[8:10], "little")
    info = ast.literal_eval(bruto[10:10 + tam].decode("latin1"))
    return 10 + tam, info


def baixar_pedacos():
    destino = PASTA / "acav_pedacos.npy"
    if destino.exists():
        print("já baixado:", destino)
        return
    url = BASE + ACAV
    inicio, info = cabecalho(url)
    linhas, *forma = info["shape"]
    bytes_linha = int(np.prod(forma)) * np.dtype(info["descr"]).itemsize
    partes = []
    for i in range(PEDACOS):
        primeira = int((linhas - LINHAS_POR_PEDACO) * i / max(1, PEDACOS - 1))
        a = inicio + primeira * bytes_linha
        print(f"pedaço {i + 1}/{PEDACOS} (linha {primeira})…", flush=True)
        dados = faixa(url, a, a + LINHAS_POR_PEDACO * bytes_linha - 1)
        partes.append(np.frombuffer(dados, dtype=info["descr"]).reshape(-1, *forma))
    PASTA.mkdir(parents=True, exist_ok=True)
    np.save(PASTA / "acav_pedacos.tmp.npy", np.concatenate(partes))
    os.replace(PASTA / "acav_pedacos.tmp.npy", destino)
    print("ok:", destino, flush=True)


def baixar_validacao():
    destino = PASTA / VALIDACAO
    if destino.exists():
        print("já baixado:", destino)
        return
    PASTA.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp")
    print("validação (185 MB)…", flush=True)
    urllib.request.urlretrieve(BASE + VALIDACAO, tmp)
    os.replace(tmp, destino)


if __name__ == "__main__":
    baixar_validacao()
    baixar_pedacos()
